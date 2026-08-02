"""Shared API response schemas."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ErrorItem(APIModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Meta(APIModel):
    correlation_id: str | None = None
    page: int | None = None
    page_size: int | None = None
    total: int | None = None


class APIResponse(APIModel, Generic[T]):
    data: T | None = None
    meta: Meta = Field(default_factory=Meta)
    errors: list[ErrorItem] = Field(default_factory=list)


class MessageData(APIModel):
    message: str
