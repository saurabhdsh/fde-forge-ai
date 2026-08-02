"""Response helpers."""

from typing import Any, TypeVar

from app.schemas.common import APIResponse, ErrorItem, Meta

T = TypeVar("T")


def success(
    data: T,
    *,
    correlation_id: str | None = None,
    page: int | None = None,
    page_size: int | None = None,
    total: int | None = None,
    extra_meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    meta = Meta(
        correlation_id=correlation_id,
        page=page,
        page_size=page_size,
        total=total,
    )
    payload = APIResponse[Any](data=data, meta=meta, errors=[]).model_dump()
    if extra_meta:
        payload["meta"].update(extra_meta)
    return payload


def failure(
    *,
    code: str,
    message: str,
    status_hint: int = 400,
    details: dict[str, Any] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    _ = status_hint
    return APIResponse[Any](
        data=None,
        meta=Meta(correlation_id=correlation_id),
        errors=[ErrorItem(code=code, message=message, details=details or {})],
    ).model_dump()
