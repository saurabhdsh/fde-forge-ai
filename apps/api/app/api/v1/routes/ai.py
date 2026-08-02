"""AI provider discovery for Mac Bedrock / OpenAI switching."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.ai.gateway import AIGateway
from app.api.deps import RequestContext, get_current_context
from app.api.responses import success

router = APIRouter()


@router.get("/providers")
async def list_ai_providers(
    ctx: Annotated[RequestContext, Depends(get_current_context)],
) -> dict:
    """Return enabled LLM providers and which are ready (API key / IAM)."""
    data = AIGateway().list_providers()
    return success(data, correlation_id=ctx.correlation_id)
