"""Non-OpenAI provider adapters — configuration validation only (no fake responses).

Bedrock is implemented in bedrock_provider.py.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

from app.ai.base import (
    AIGenerationResult,
    AIProvider,
    EmbeddingResult,
    StructuredGenerationResult,
)
from app.core.config import Settings
from app.core.exceptions import ConfigurationError


class _UnconfiguredProvider(AIProvider):
    """Base for adapters that are not yet operational."""

    required_fields: list[str] = []

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        missing = [f for f in self.required_fields if not getattr(settings, f, None)]
        if missing:
            raise ConfigurationError(
                f"{self.name} provider is not configured",
                details={"missing": missing},
            )
        raise ConfigurationError(
            f"{self.name} provider adapter is registered but not enabled. "
            "Use AI_DEFAULT_PROVIDER=openai or bedrock."
        )

    async def generate_text(self, **kwargs) -> AIGenerationResult:  # type: ignore[no-untyped-def]
        raise ConfigurationError(f"{self.name} is not enabled")

    async def generate_structured(  # type: ignore[no-untyped-def]
        self, **kwargs
    ) -> StructuredGenerationResult:
        raise ConfigurationError(f"{self.name} is not enabled")

    async def generate_embedding(self, **kwargs) -> EmbeddingResult:  # type: ignore[no-untyped-def]
        raise ConfigurationError(f"{self.name} is not enabled")

    async def stream_text(self, **kwargs) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
        raise ConfigurationError(f"{self.name} is not enabled")
        yield ""  # pragma: no cover


class AzureOpenAIProvider(_UnconfiguredProvider):
    name = "azure_openai"
    required_fields = [
        "azure_openai_api_key",
        "azure_openai_endpoint",
        "azure_openai_deployment",
    ]


class AnthropicProvider(_UnconfiguredProvider):
    name = "anthropic"
    required_fields = ["anthropic_api_key"]


class GeminiProvider(_UnconfiguredProvider):
    name = "gemini"
    required_fields = ["google_api_key"]
