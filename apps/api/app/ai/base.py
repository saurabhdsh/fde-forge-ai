"""AI provider interface — provider-independent gateway contracts."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class AIGenerationResult(BaseModel):
    content: str
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw: dict[str, Any] | None = None


class StructuredGenerationResult(BaseModel):
    data: dict[str, Any]
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost_usd: float | None = None
    raw: dict[str, Any] | None = None


class EmbeddingResult(BaseModel):
    embedding: list[float]
    provider: str
    model: str
    input_tokens: int | None = None
    estimated_cost_usd: float | None = None


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def generate_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AIGenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def generate_structured(
        self,
        *,
        prompt: str,
        schema: type[BaseModel],
        system: str | None = None,
        temperature: float = 0.1,
        max_output_tokens: int = 4096,
    ) -> StructuredGenerationResult:
        raise NotImplementedError

    @abstractmethod
    async def generate_embedding(self, *, text: str) -> EmbeddingResult:
        raise NotImplementedError

    @abstractmethod
    async def stream_text(
        self,
        *,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        raise NotImplementedError
        yield ""  # pragma: no cover
