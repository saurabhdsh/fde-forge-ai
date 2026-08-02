"""Admin curriculum / course enrichment document routes."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.api.deps import DbSession, RequestContext, require_permissions
from app.api.responses import success
from app.services.curriculum_service import CurriculumService

router = APIRouter()


@router.get("/enrichment-documents")
async def list_enrichment_documents(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("curriculum.create"))],
    domain: str | None = Query(default=None),
) -> dict:
    service = CurriculumService(db)
    data = await service.list_documents(ctx.organization_id, domain=domain)
    return success(data, correlation_id=ctx.correlation_id)


@router.post("/enrichment-documents")
async def upload_enrichment_document(
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("curriculum.create"))],
    file: UploadFile = File(...),
    domain: str = Form(default="all"),
    title: str | None = Form(default=None),
    notes: str | None = Form(default=None),
) -> dict:
    data = await file.read()
    service = CurriculumService(db)
    doc = await service.upload_document(
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        filename=file.filename or "document.pdf",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        domain=domain,
        title=title,
        notes=notes,
        correlation_id=ctx.correlation_id,
        ip_address=ctx.ip_address,
        user_agent=ctx.user_agent,
    )
    return success(doc, correlation_id=ctx.correlation_id)


@router.delete("/enrichment-documents/{document_id}")
async def delete_enrichment_document(
    document_id: UUID,
    db: DbSession,
    ctx: Annotated[RequestContext, Depends(require_permissions("curriculum.create"))],
) -> dict:
    service = CurriculumService(db)
    await service.delete_document(
        doc_id=document_id,
        organization_id=ctx.organization_id,
        actor_id=ctx.user.id,
        correlation_id=ctx.correlation_id,
    )
    return success({"deleted": True}, correlation_id=ctx.correlation_id)
