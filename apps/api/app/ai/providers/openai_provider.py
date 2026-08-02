"""OpenAI provider — fully operational initial implementation."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.base import (
    AIGenerationResult,
    AIProvider,
    EmbeddingResult,
    StructuredGenerationResult,
)
from app.core.config import Settings
from app.core.exceptions import AppError, ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Approximate public pricing for cost tracking (USD / 1M tokens)
COST_TABLE = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "text-embedding-3-small": {"input": 0.02, "output": 0.0},
}


def estimate_cost(model: str, input_tokens: int | None, output_tokens: int | None) -> float | None:
    rates = COST_TABLE.get(model)
    if not rates or input_tokens is None:
        return None
    inp = (input_tokens / 1_000_000) * rates["input"]
    out = ((output_tokens or 0) / 1_000_000) * rates["output"]
    return round(inp + out, 6)


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_configured:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Set OPENAI_API_KEY to enable AI features."
            )
        self.settings = settings
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.ai_request_timeout_seconds,
        )
        self.model = settings.openai_model
        self.embedding_model = settings.openai_embedding_model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AIGenerationResult:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_output_tokens,
        )
        choice = response.choices[0].message.content or ""
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        return AIGenerationResult(
            content=choice,
            provider=self.name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost(self.model, input_tokens, output_tokens),
            raw=response.model_dump(),
        )

    async def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
    ) -> StructuredGenerationResult:
        schema_json = schema.model_json_schema()
        system_prompt = (
            (system or "")
            + "\n\nYou must respond with valid JSON matching this JSON Schema. "
            "Do not invent facts not supported by the source text. "
            "If uncertain, lower confidence and omit unsupported claims.\n"
            f"JSON Schema:\n{json.dumps(schema_json)}"
        ).strip()

        last_error: Exception | None = None
        for attempt in range(1, self.settings.ai_max_retries + 1):
            try:
                result = await self._structured_once(
                    prompt=prompt,
                    schema=schema,
                    system=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    attempt=attempt,
                )
                return result
            except (ValidationError, json.JSONDecodeError, AppError) as exc:
                last_error = exc
                logger.warning(
                    "structured_generation_retry",
                    attempt=attempt,
                    error=str(exc),
                )
                prompt = (
                    prompt
                    + "\n\nPrevious response failed schema validation. "
                    f"Error: {exc}. Return corrected JSON only."
                )

        raise AppError(
            "AI structured output failed schema validation after retries",
            code="ai_validation_failed",
            status_code=502,
            details={"error": str(last_error)},
        )

    async def _structured_once(
        self,
        *,
        prompt: str,
        schema: type[BaseModel],
        system: str,
        temperature: float,
        max_output_tokens: int,
        attempt: int,
    ) -> StructuredGenerationResult:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_output_tokens,
            "response_format": {"type": "json_object"},
        }
        response = await self.client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or "{}"
        parsed = json.loads(content)
        validated = schema.model_validate(parsed)
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None
        return StructuredGenerationResult(
            data=validated.model_dump(),
            provider=self.name,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimate_cost(self.model, input_tokens, output_tokens),
            raw={"attempt": attempt, "response": response.model_dump()},
        )

    async def generate_embedding(self, *, text: str) -> EmbeddingResult:
        response = await self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        vector = response.data[0].embedding
        tokens = response.usage.total_tokens if response.usage else None
        return EmbeddingResult(
            embedding=vector,
            provider=self.name,
            model=self.embedding_model,
            input_tokens=tokens,
            estimated_cost_usd=estimate_cost(self.embedding_model, tokens, 0),
        )

    async def stream_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        stream = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=max_output_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta
