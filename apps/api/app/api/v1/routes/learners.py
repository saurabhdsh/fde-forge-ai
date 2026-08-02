"""Learner onboarding and resume routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from app.api.deps import CurrentContext, DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.core.exceptions import ForbiddenError
from app.schemas.learner import ConfirmSkillsRequest, LearnerProfileUpdate
from app.services.learner_service import LearnerService

router = APIRouter()


def _ensure_self_or_manage(ctx: RequestContext, user_id: UUID) -> None:
    if ctx.user.id == user_id and "learner.self" in ctx.permissions:
        return
    if "learner.manage" in ctx.permissions or "learner.view" in ctx.permissions:
        return
    if ctx.user.is_super_admin:
        return
    raise ForbiddenError("Not allowed to access this learner profile")


@router.get("/me/profile")
async def get_my_profile(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    profile = await service.get_profile(ctx.user.id, ctx.organization_id)
    return success(profile, correlation_id=ctx.correlation_id)


@router.patch("/me/profile")
async def update_my_profile(
    payload: LearnerProfileUpdate,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    profile = await service.update_profile(
        ctx.user.id,
        ctx.organization_id,
        payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(profile, correlation_id=ctx.correlation_id)


@router.post("/me/resume")
async def upload_resume(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
    file: UploadFile = File(...),
) -> dict:
    data = await file.read()
    service = LearnerService(db)
    resume, extraction = await service.upload_resume(
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        filename=file.filename or "resume.pdf",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(
        {"resume": resume, "extraction": extraction},
        correlation_id=ctx.correlation_id,
    )


@router.post("/me/resume/{resume_id}/extract")
async def retry_extract(
    resume_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    extraction = await service.retry_extraction(
        resume_id=resume_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(extraction, correlation_id=ctx.correlation_id)


@router.get("/me/extraction")
async def get_extraction(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    extraction = await service.get_latest_extraction(ctx.user.id, ctx.organization_id)
    return success(extraction, correlation_id=ctx.correlation_id)


@router.post("/me/extraction/{extraction_id}/confirm")
async def confirm_skills(
    extraction_id: UUID,
    payload: ConfirmSkillsRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    skills = await service.confirm_skills(
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        extraction_id=extraction_id,
        payload=payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(skills, correlation_id=ctx.correlation_id, total=len(skills))


@router.get("/me/skills")
async def my_skills(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = LearnerService(db)
    skills = await service.list_learner_skills(ctx.user.id, ctx.organization_id)
    return success(skills, correlation_id=ctx.correlation_id, total=len(skills))


@router.get("/{user_id}/profile")
async def get_learner_profile(
    user_id: UUID,
    db: DbSession,
    ctx: CurrentContext,
) -> dict:
    _ensure_self_or_manage(ctx, user_id)
    if "learner.view" not in ctx.permissions and ctx.user.id != user_id:
        raise ForbiddenError("Missing learner.view permission")
    service = LearnerService(db)
    profile = await service.get_profile(user_id, ctx.organization_id)
    return success(profile, correlation_id=ctx.correlation_id)


@router.get("/{user_id}/skills")
async def get_learner_skills(
    user_id: UUID,
    db: DbSession,
    ctx: CurrentContext,
) -> dict:
    _ensure_self_or_manage(ctx, user_id)
    service = LearnerService(db)
    skills = await service.list_learner_skills(user_id, ctx.organization_id)
    return success(skills, correlation_id=ctx.correlation_id, total=len(skills))
