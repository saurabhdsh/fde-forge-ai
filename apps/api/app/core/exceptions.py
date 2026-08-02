"""Application exceptions and structured error helpers."""

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(message, code="not_found", status_code=404, **kwargs)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(message, code="unauthorized", status_code=401, **kwargs)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        super().__init__(message, code="forbidden", status_code=403, **kwargs)


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(message, code="conflict", status_code=409, **kwargs)


class ValidationAppError(AppError):
    def __init__(self, message: str = "Validation error", **kwargs: Any) -> None:
        super().__init__(message, code="validation_error", status_code=422, **kwargs)


class ConfigurationError(AppError):
    def __init__(self, message: str = "Service not configured", **kwargs: Any) -> None:
        super().__init__(message, code="configuration_error", status_code=503, **kwargs)


class RateLimitError(AppError):
    def __init__(self, message: str = "Rate limit exceeded", **kwargs: Any) -> None:
        super().__init__(message, code="rate_limit", status_code=429, **kwargs)
