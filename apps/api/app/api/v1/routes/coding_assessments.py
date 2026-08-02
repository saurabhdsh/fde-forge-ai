"""Coding playground assessment routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.core.exceptions import NotFoundError
from app.schemas.coding_assessment import (
    CodingDraftRequest,
    CodingSubmitRequest,
    SyntaxCheckOut,
    SyntaxCheckRequest,
    SyntaxDiagnosticOut,
)
from app.services.coding_assessment_service import CodingAssessmentService
from app.services.python_syntax import check_python_syntax

router = APIRouter()


@router.post("/syntax-check")
async def syntax_check(
    payload: SyntaxCheckRequest,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    lang = (payload.language or "python").lower().strip()
    if lang not in {"python", "py"}:
        return success(
            SyntaxCheckOut(
                ok=False,
                diagnostics=[
                    SyntaxDiagnosticOut(
                        line=1,
                        column=1,
                        message=f"Live syntax checking supports Python only (got {lang})",
                        severity="warning",
                        source="playground",
                    )
                ],
            ),
            correlation_id=ctx.correlation_id,
        )
    diags = check_python_syntax(payload.code or "")
    out = SyntaxCheckOut(
        ok=not any(d.severity == "error" for d in diags),
        diagnostics=[
            SyntaxDiagnosticOut(
                line=d.line,
                column=d.column,
                message=d.message,
                severity=d.severity,
                source=d.source,
            )
            for d in diags
        ],
    )
    return success(out, correlation_id=ctx.correlation_id)


@router.post("/start")
async def start_coding_assessment(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CodingAssessmentService(db)
    data = await service.create(
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/me/latest")
async def latest_coding_assessment(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CodingAssessmentService(db)
    data = await service.get_latest(ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.get("/{assessment_id}/export")
async def export_coding_assessment(
    assessment_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
    format: str = Query(default="markdown", alias="format"),
) -> Response:
    service = CodingAssessmentService(db)
    assessment = await service.repo.get_by_id(assessment_id, ctx.organization_id)
    if not assessment or assessment.user_id != ctx.user.id:
        raise NotFoundError("Coding assessment not found")
    content, filename, media = service.export(assessment=assessment, fmt=format)
    return Response(
        content=content,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{assessment_id}/draft")
async def save_coding_draft(
    assessment_id: UUID,
    payload: CodingDraftRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CodingAssessmentService(db)
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
async def get_coding_assessment(
    assessment_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CodingAssessmentService(db)
    data = await service.get(assessment_id, ctx.user.id, ctx.organization_id)
    return success(data, correlation_id=ctx.correlation_id)


@router.post("/{assessment_id}/submit")
async def submit_coding_assessment(
    assessment_id: UUID,
    payload: CodingSubmitRequest,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("learner.self"))],
) -> dict:
    service = CodingAssessmentService(db)
    data = await service.submit(
        assessment_id=assessment_id,
        user_id=ctx.user.id,
        organization_id=ctx.organization_id,
        payload=payload,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success(data, correlation_id=ctx.correlation_id)
