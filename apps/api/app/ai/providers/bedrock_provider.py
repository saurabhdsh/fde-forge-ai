"""Amazon Bedrock Converse + Titan embeddings provider."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import BaseModel, ValidationError

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


def has_aws_credentials() -> bool:
    """True when env/profile/instance role can resolve credentials."""
    try:
        session = boto3.Session()
        creds = session.get_credentials()
        if creds is None:
            return False
        frozen = creds.get_frozen_credentials()
        return bool(frozen.access_key and frozen.secret_key)
    except Exception:  # noqa: BLE001
        return False


def resolve_bedrock_model_id(model_id: str, region: str) -> str:
    """Prefix anthropic.* with us. when in us-* regions (inference profile)."""
    mid = (model_id or "").strip()
    if not mid:
        return mid
    if mid.startswith("us.") or mid.startswith("eu.") or mid.startswith("apac."):
        return mid
    if mid.startswith("anthropic.") and (region or "").startswith("us-"):
        return f"us.{mid}"
    return mid


class BedrockProvider(AIProvider):
    name = "bedrock"

    def __init__(self, settings: Settings) -> None:
        if not settings.bedrock_enabled:
            raise ConfigurationError(
                "Bedrock is disabled. Set BEDROCK_ENABLED=true to use AWS Bedrock."
            )
        if not (settings.bedrock_model_id or "").strip():
            raise ConfigurationError("BEDROCK_MODEL_ID is not configured")
        if not has_aws_credentials() and not (
            settings.aws_access_key_id and settings.aws_secret_access_key
        ):
            raise ConfigurationError(
                "AWS credentials not found. On Mac run `aws configure` or mount ~/.aws into Docker. "
                "On EC2/ECS use an IAM role with bedrock:InvokeModel."
            )
        self.settings = settings
        self.region = settings.aws_region or "us-east-1"
        self.model = resolve_bedrock_model_id(settings.bedrock_model_id, self.region)
        self.embedding_model = (
            settings.bedrock_embedding_model_id or "amazon.titan-embed-text-v2:0"
        ).strip()
        client_kwargs: dict[str, Any] = {
            "region_name": self.region,
            "config": Config(
                connect_timeout=10,
                read_timeout=240,
                retries={"max_attempts": 2, "mode": "standard"},
            ),
        }
        if settings.aws_access_key_id and settings.aws_secret_access_key:
            client_kwargs["aws_access_key_id"] = settings.aws_access_key_id.strip()
            client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key.strip()
        self._client = boto3.client("bedrock-runtime", **client_kwargs)

    def _converse_sync(
        self,
        *,
        messages: list[dict[str, Any]],
        system: list[dict[str, str]] | None,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "modelId": self.model,
            "messages": messages,
            "inferenceConfig": {
                "maxTokens": max_tokens,
                "temperature": max(0.0, min(temperature, 1.0)),
            },
        }
        if system:
            kwargs["system"] = system
        return self._client.converse(**kwargs)

    @staticmethod
    def _extract_text(response: dict[str, Any]) -> str:
        parts: list[str] = []
        for block in response.get("output", {}).get("message", {}).get("content") or []:
            if isinstance(block, dict) and block.get("text"):
                parts.append(str(block["text"]))
        return "\n".join(parts).strip()

    @staticmethod
    def _usage(response: dict[str, Any]) -> tuple[int | None, int | None]:
        usage = response.get("usage") or {}
        inp = usage.get("inputTokens")
        out = usage.get("outputTokens")
        return (int(inp) if inp is not None else None, int(out) if out is not None else None)

    async def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AIGenerationResult:
        messages = [{"role": "user", "content": [{"text": prompt}]}]
        system_blocks = [{"text": system}] if system else None
        try:
            response = await asyncio.to_thread(
                self._converse_sync,
                messages=messages,
                system=system_blocks,
                temperature=temperature,
                max_tokens=max_output_tokens,
            )
        except (ClientError, BotoCoreError) as exc:
            raise AppError(
                f"Bedrock Converse failed: {exc}",
                code="bedrock_error",
                status_code=502,
                details={"model": self.model},
            ) from exc
        content = self._extract_text(response)
        inp, out = self._usage(response)
        return AIGenerationResult(
            content=content,
            provider=self.name,
            model=self.model,
            input_tokens=inp,
            output_tokens=out,
            raw={"converse": True},
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
            "If uncertain, lower confidence and omit unsupported claims. "
            "Return JSON only — no markdown fences.\n"
            f"JSON Schema:\n{json.dumps(schema_json)}"
        ).strip()

        last_error: Exception | None = None
        user_prompt = prompt
        for attempt in range(1, self.settings.ai_max_retries + 1):
            try:
                result = await self.generate_text(
                    prompt=user_prompt,
                    system=system_prompt,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
                content = result.content.strip()
                if content.startswith("```"):
                    content = content.strip("`")
                    if content.startswith("json"):
                        content = content[4:].strip()
                parsed = json.loads(content)
                validated = schema.model_validate(parsed)
                return StructuredGenerationResult(
                    data=validated.model_dump(),
                    provider=self.name,
                    model=self.model,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    raw={"attempt": attempt},
                )
            except AppError as exc:
                # Transport / IAM failures should bubble for gateway fallback
                if exc.code == "bedrock_error":
                    raise
                last_error = exc
                logger.warning(
                    "bedrock_structured_retry",
                    attempt=attempt,
                    error=str(exc),
                )
                user_prompt = (
                    prompt
                    + "\n\nPrevious response failed schema validation. "
                    f"Error: {exc}. Return corrected JSON only."
                )
            except (ValidationError, json.JSONDecodeError) as exc:
                last_error = exc
                logger.warning(
                    "bedrock_structured_retry",
                    attempt=attempt,
                    error=str(exc),
                )
                user_prompt = (
                    prompt
                    + "\n\nPrevious response failed schema validation. "
                    f"Error: {exc}. Return corrected JSON only."
                )

        raise AppError(
            "Bedrock structured output failed schema validation after retries",
            code="ai_validation_failed",
            status_code=502,
            details={"error": str(last_error)},
        )

    def _embed_sync(self, text: str) -> list[float]:
        body = json.dumps({"inputText": text[:25000], "dimensions": 1024, "normalize": True})
        response = self._client.invoke_model(
            modelId=self.embedding_model,
            body=body,
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding")
        if not isinstance(embedding, list):
            raise AppError("Bedrock embedding response missing vector", code="bedrock_error", status_code=502)
        return [float(x) for x in embedding]

    async def generate_embedding(self, *, text: str) -> EmbeddingResult:
        try:
            vector = await asyncio.to_thread(self._embed_sync, text)
        except (ClientError, BotoCoreError) as exc:
            raise AppError(
                f"Bedrock embedding failed: {exc}",
                code="bedrock_error",
                status_code=502,
                details={"model": self.embedding_model},
            ) from exc
        return EmbeddingResult(
            embedding=vector,
            provider=self.name,
            model=self.embedding_model,
        )

    async def stream_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        # Converse streaming omitted for V1; emit full completion as one chunk.
        result = await self.generate_text(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        if result.content:
            yield result.content
