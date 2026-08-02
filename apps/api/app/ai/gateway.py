"""AI gateway with routing, retries, OpenAI↔Bedrock fallback, and usage tracking hooks."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import TypeVar

from pydantic import BaseModel

from app.ai.base import (
    AIGenerationResult,
    AIProvider,
    EmbeddingResult,
    StructuredGenerationResult,
)
from app.ai.providers.bedrock_provider import BedrockProvider, has_aws_credentials
from app.ai.providers.openai_provider import OpenAIProvider
from app.ai.providers.stubs import (
    AnthropicProvider,
    AzureOpenAIProvider,
    GeminiProvider,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import ConfigurationError
from app.core.logging import get_logger

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)

CREDENTIAL_ERROR_HINTS = (
    "unable to locate credentials",
    "no credentials",
    "expiredtoken",
    "invalidsignatureexception",
    "unrecognizedclientexception",
    "accessdeniedexception",
    "signaturedoesnotmatch",
)

INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all prior",
    "system prompt",
    "reveal your system",
    "jailbreak",
    "you are now",
]


def sanitize_for_prompt(text: str, *, max_chars: int = 50000) -> str:
    cleaned = text[:max_chars]
    lower = cleaned.lower()
    for pattern in INJECTION_PATTERNS:
        if pattern in lower:
            cleaned = cleaned.replace(pattern, "[filtered]")
            cleaned = cleaned.replace(pattern.title(), "[filtered]")
            cleaned = cleaned.replace(pattern.upper(), "[filtered]")
    return cleaned


def hallucination_risk_score(payload: dict) -> float:
    skills = payload.get("skills") or []
    if not skills:
        return 0.7
    confidences = [float(s.get("confidence", 0.5)) for s in skills if isinstance(s, dict)]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.5
    missing_evidence = sum(
        1 for s in skills if isinstance(s, dict) and not s.get("evidence")
    )
    risk = (1.0 - avg_conf) * 0.6 + (missing_evidence / max(len(skills), 1)) * 0.4
    return round(min(max(risk, 0.0), 1.0), 3)


class AIGateway:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def resolve_provider_name(self, name: str | None = None) -> str:
        requested = (name or self.settings.ai_default_provider or "openai").lower().strip()
        enabled = set(self.settings.enabled_llm_provider_list) or {"openai", "bedrock"}

        def ready(provider: str) -> bool:
            if provider not in enabled and provider != requested:
                return False
            if provider == "bedrock":
                return self.settings.bedrock_enabled and (
                    self.settings.bedrock_configured or has_aws_credentials()
                )
            if provider == "openai":
                return self.settings.openai_configured
            return False

        if requested == "bedrock":
            if ready("bedrock"):
                return "bedrock"
            if ready("openai"):
                logger.warning("bedrock_unavailable_fallback_openai")
                return "openai"
            raise ConfigurationError(
                "Bedrock is the default provider but AWS credentials are missing and OpenAI is not configured."
            )
        if requested == "openai":
            if ready("openai"):
                return "openai"
            if ready("bedrock"):
                logger.warning("openai_unavailable_fallback_bedrock")
                return "bedrock"
            raise ConfigurationError("OPENAI_API_KEY is not configured.")
        return requested

    def get_provider(self, name: str | None = None) -> AIProvider:
        provider_name = self.resolve_provider_name(name)
        if provider_name == "openai":
            return OpenAIProvider(self.settings)
        if provider_name == "azure_openai":
            return AzureOpenAIProvider(self.settings)
        if provider_name == "anthropic":
            return AnthropicProvider(self.settings)
        if provider_name == "bedrock":
            return BedrockProvider(self.settings)
        if provider_name == "gemini":
            return GeminiProvider(self.settings)
        raise ConfigurationError(
            f"Unknown AI provider '{provider_name}'",
            details={"supported": ["openai", "bedrock", "azure_openai", "anthropic", "gemini"]},
        )

    def _is_credential_error(self, exc: Exception) -> bool:
        msg = str(exc).lower()
        return any(h in msg for h in CREDENTIAL_ERROR_HINTS)

    async def generate_text(
        self, *, provider: str | None = None, **kwargs
    ) -> AIGenerationResult:  # type: ignore[no-untyped-def]
        try:
            return await self.get_provider(provider).generate_text(**kwargs)
        except Exception as exc:  # noqa: BLE001
            if provider != "openai" and self._is_credential_error(exc) and self.settings.openai_configured:
                logger.warning("bedrock_credential_fallback_openai", error=str(exc))
                return await OpenAIProvider(self.settings).generate_text(**kwargs)
            raise

    async def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[T],
        system: str | None = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
        provider: str | None = None,
    ) -> StructuredGenerationResult:
        try:
            resolved = self.get_provider(provider)
            return await resolved.generate_structured(
                prompt=prompt,
                schema=schema,
                system=system,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
            )
        except ConfigurationError:
            raise
        except Exception as exc:  # noqa: BLE001
            if self._is_credential_error(exc) and self.settings.openai_configured:
                logger.warning("ai_credential_fallback_openai", error=str(exc))
                return await OpenAIProvider(self.settings).generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system=system,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            fallback = self.settings.ai_fallback_model
            if fallback and self.settings.openai_configured:
                logger.warning("ai_fallback_attempt", error=str(exc), fallback=fallback)
                settings = self.settings.model_copy(update={"openai_model": fallback})
                return await OpenAIProvider(settings).generate_structured(
                    prompt=prompt,
                    schema=schema,
                    system=system,
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                )
            raise

    async def generate_embedding(
        self, *, text: str, provider: str | None = None
    ) -> EmbeddingResult:
        # Prefer OpenAI embeddings when available (stable dims); else Bedrock Titan.
        try:
            if provider:
                return await self.get_provider(provider).generate_embedding(text=text)
            if self.settings.openai_configured:
                return await OpenAIProvider(self.settings).generate_embedding(text=text)
            return await self.get_provider("bedrock").generate_embedding(text=text)
        except Exception as exc:  # noqa: BLE001
            if self.settings.openai_configured and self._is_credential_error(exc):
                return await OpenAIProvider(self.settings).generate_embedding(text=text)
            raise

    async def stream_text(
        self, *, provider: str | None = None, **kwargs
    ) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
        async for chunk in self.get_provider(provider).stream_text(**kwargs):
            yield chunk

    def list_providers(self) -> dict:
        openai_ready = self.settings.openai_configured
        bedrock_ready = self.settings.bedrock_enabled and (
            self.settings.bedrock_configured or has_aws_credentials()
        )
        enabled = set(self.settings.enabled_llm_provider_list) or {"openai", "bedrock"}
        providers = []
        if "openai" in enabled:
            providers.append(
                {
                    "id": "openai",
                    "name": "OpenAI",
                    "enabled": openai_ready,
                    "auth_type": "api_key",
                    "default_model": self.settings.openai_model,
                }
            )
        if "bedrock" in enabled:
            providers.append(
                {
                    "id": "bedrock",
                    "name": "AWS Bedrock",
                    "enabled": bedrock_ready,
                    "auth_type": "iam",
                    "default_model": self.settings.bedrock_model_id,
                }
            )
        try:
            default = self.resolve_provider_name()
        except ConfigurationError:
            default = self.settings.ai_default_provider
        return {"providers": providers, "default_provider": default}
