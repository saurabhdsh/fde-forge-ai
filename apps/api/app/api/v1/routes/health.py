"""Health and readiness endpoints."""

from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.api.responses import success
from app.core.config import get_settings

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    settings = get_settings()
    return success(
        {
            "status": "ok",
            "app": settings.app_name,
            "env": settings.app_env,
            "openai_configured": settings.openai_configured,
            "bedrock_enabled": settings.bedrock_enabled,
            "bedrock_configured": settings.bedrock_configured,
            "ai_configured": settings.ai_configured,
            "default_llm_provider": settings.ai_default_provider,
        }
    )


@router.get("/ready")
async def ready(db: DbSession) -> dict:
    await db.execute(text("SELECT 1"))
    return success({"status": "ready"})
