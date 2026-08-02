"""Assessment routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.core.exceptions import NotFoundError
from app.schemas.assessment import AssessmentDraftRequest, AssessmentSubmitRequest
from app.services.assessment_service import AssessmentService

router = APIRouter()


@router.post("/baseline")
async def create_baseline(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = AssessmentService(db)
    data = await service.create_baseline(
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/me/latest")
async def latest_assessment(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = AssessmentService(db)
    data = await service.get_latest(ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/{assessment_id}/export")
async def export_assessment(
    assessment_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
    format: str = Query(default="markdown", alias="format"),
) -> Response:
    service = AssessmentService(db)
    assessment = await service.repo.get_by_id(assessment_id, ctx.organization_id)
    if not assessment or assessment.user_id != ctx.user.id:
        raise NotFoundError("Assessment not found")
    content, filename, media = service.export(assessment=assessment, fmt=format)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{assessment_id}/draft")
async def save_assessment_draft(
    assessment_id: UUID,
    payload: AssessmentDraftRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = AssessmentService(db)
    data = await service.save_draft(
        assessment_id=assessment_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        payload=payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/{assessment_id}")
async def get_assessment(
    assessment_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = AssessmentService(db)
    data = await service.get(assessment_id, ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.post("/{assessment_id}/submit")
async def submit_assessment(
    assessment_id: UUID,
    payload: AssessmentSubmitRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = AssessmentService(db)
    data = await service.submit(
        assessment_id=assessment_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        payload=payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(data, correlation_id=ctx.correlation_id)
