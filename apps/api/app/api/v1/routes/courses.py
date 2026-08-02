"""Domain course routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.schemas.course import CompleteSlideRequest, EnsureCourseRequest, SelectTopicsRequest
from app.services.course_service import CourseService

router = APIRouter()


@router.get("/catalog")
async def course_catalog(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CourseService(db)
    data = await service.catalog(ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/assessment-unlocked")
async def assessment_unlocked(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CourseService(db)
    unlocked = await service.is_assessment_unlocked(ctx.user.id, ctx.organization_id)
    incomplete = await service.incomplete_domains(ctx.user.id, ctx.organization_id)
    return success(
        {"unlocked": unlocked, "incomplete_domains": incomplete},
        correlation_id=ctx.correlation_id,
    )


@router.put("/domains/{domain}/topics")
async def select_domain_topics(
    domain: str,
    payload: SelectTopicsRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CourseService(db)
    data = await service.save_topic_selection(
        domain=domain,
        topic_ids=payload.topic_ids,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
    )
    return success(data, correlation_id=ctx.correlation_id)


@router.post("/domains/{domain}/ensure")
async def ensure_domain_course(
    domain: str,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
    force: bool = Query(default=False),
    payload: EnsureCourseRequest | None = Body(default=None),
) -> dict:
    body = payload or EnsureCourseRequest()
    service = CourseService(db)
    data = await service.ensure_course(
        domain=domain,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
        force_regenerate=force or body.force,
        topic_ids=body.topic_ids,
    )
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/{course_id}")
async def get_course(
    course_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CourseService(db)
    data = await service.get_course(course_id, ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.post("/{course_id}/slides/complete")
async def complete_slide(
    course_id: UUID,
    payload: CompleteSlideRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CourseService(db)
    data = await service.complete_slide(
        course_id=course_id,
        slide_id=payload.slide_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(data, correlation_id=ctx.correlation_id)
