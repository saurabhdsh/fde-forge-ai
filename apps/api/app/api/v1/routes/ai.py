"""AI provider discovery and Bedrock access check."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.gateway import AIGateway
from app.ai.providers.bedrock_provider import (
    BedrockProvider,
    has_aws_credentials,
    resolve_bedrock_model_id,
)
from app.api.deps import RequestContext, get_current_context
from app.api.responses import success
from app.core.config import get_settings
from app.core.exceptions import AppError, ConfigurationError

router = APIRouter()


@router.get("/providers")
async def list_ai_providers(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> dict:
    """Return enabled LLM providers and which are ready (API key / IAM)."""
    data = AIGateway().list_providers()
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/bedrock/check")
async def check_bedrock_access(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> dict:
    """Tiny Converse call to verify Mac/EC2 AWS credentials can reach Bedrock."""
    settings = get_settings()
    region = (settings.aws_region or "us-east-1").strip()
    model = resolve_bedrock_model_id(
        settings.bedrock_model_id or "us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        region,
    )
    base = {
        "bedrock_enabled": settings.bedrock_enabled,
        "region": region,
        "model_id": model,
        "credentials_present": has_aws_credentials()
        or bool(settings.aws_access_key_id and settings.aws_secret_access_key),
    }
    if not settings.bedrock_enabled:
        raise ConfigurationError(
            "Bedrock is disabled. Set BEDROCK_ENABLED=true",
            details=base,
        )
    if not base["credentials_present"]:
        raise ConfigurationError(
            "AWS credentials not found. Run `aws configure` (region us-east-1).",
            details=base,
        )

    try:
        provider = BedrockProvider(settings)
        result = await provider.generate_text(
            prompt="Reply with exactly: BEDROCK_OK",
            system=None,
            temperature=0.0,
            max_output_tokens=32,
        )
    except ConfigurationError:
        raise
    except AppError as exc:
        raise AppError(
            f"Bedrock check failed: {exc.message}",
            code="bedrock_check_failed",
            status_code=502,
            details={**base, "error": exc.message},
        ) from exc
    except Exception as exc:  # noqa: BLE001
        raise AppError(
            f"Bedrock check failed: {exc}",
            code="bedrock_check_failed",
            status_code=502,
            details={**base, "error": str(exc)},
        ) from exc

    return success(
        {
            **base,
            "ok": True,
            "reply": (result.content or "")[:200],
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        },
        correlation_id=ctx.correlation_id,
    )
