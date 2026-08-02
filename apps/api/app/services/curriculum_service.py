"""Admin course enrichment documents (PDF/DOCX) for AI course generation."""

from __future__ import annotations

from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models.curriculum import CourseEnrichmentDocument
from app.repositories.curriculum import CurriculumRepository
from app.schemas.curriculum import CourseEnrichmentDocumentOut
from app.services.audit_service import AuditService
from app.services.document_extraction import DocumentExtractionService
from app.services.storage_service import StorageService

logger = get_logger(__name__)

ALLOWED_DOMAINS = ("all", "healthcare", "life_sciences", "technical")
PER_DOC_CHARS = 12000
TOTAL_ENRICH_CHARS = 40000


class CurriculumService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CurriculumRepository(session)
        self.storage = StorageService()
        self.extractor = DocumentExtractionService()
        self.audit = AuditService(session)
        self.settings = get_settings()

    def _to_out(self, doc: CourseEnrichmentDocument) -> CourseEnrichmentDocumentOut:
        return CourseEnrichmentDocumentOut(
            id=doc.id,
            organization_id=doc.organization_id,
            uploaded_by_user_id=doc.uploaded_by_user_id,
            domain=doc.domain,
            title=doc.title,
            notes=doc.notes,
            original_filename=doc.original_filename,
            content_type=doc.content_type,
            file_extension=doc.file_extension,
            file_size_bytes=doc.file_size_bytes,
            extraction_status=doc.extraction_status,
            extraction_error=doc.extraction_error,
            extracted_chars=len(doc.extracted_text or ""),
            is_active=doc.is_active,
            created_at=doc.created_at,
        )

    async def list_documents(
        self,
        organization_id: UUID,
        *,
        domain: str | None = None,
    ) -> list[CourseEnrichmentDocumentOut]:
        docs = await self.repo.list_for_org(
            organization_id, domain=domain, active_only=True
        )
        return [self._to_out(d) for d in docs]

    async def upload_document(
        self,
        *,
        organization_id: UUID,
        actor_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
        domain: str = "all",
        title: str | None = None,
        notes: str | None = None,
        correlation_id: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> CourseEnrichmentDocumentOut:
        domain = (domain or "all").strip().lower().replace("-", "_").replace(" ", "_")
        if domain in {"life_science", "lifesciences"}:
            domain = "life_sciences"
        if domain in {"health", "health_care"}:
            domain = "healthcare"
        if domain not in ALLOWED_DOMAINS:
            raise ValidationAppError(
                "Invalid domain. Use all, healthcare, life_sciences, or technical."
            )

        ext = Path(filename).suffix.lower().lstrip(".")
        # Course enrichment is PDF/DOCX focused; still allow txt/md if configured
        allowed = [t for t in self.settings.allowed_file_type_list if t in {"pdf", "docx", "txt", "md"}]
        if ext not in allowed:
            raise ValidationAppError(
                "File type not allowed for course enrichment",
                details={"allowed": allowed},
            )
        max_bytes = self.settings.max_upload_size_mb * 1024 * 1024
        if len(data) > max_bytes:
            raise ValidationAppError(
                f"File exceeds maximum size of {self.settings.max_upload_size_mb} MB"
            )
        if len(data) == 0:
            raise ValidationAppError("Uploaded file is empty")

        bucket, key, checksum = self.storage.upload_bytes(
            data=data,
            organization_id=str(organization_id),
            folder="course_enrichment",
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )

        doc = CourseEnrichmentDocument(
            organization_id=organization_id,
            uploaded_by_user_id=actor_id,
            domain=domain,
            title=(title or "").strip() or None,
            notes=(notes or "").strip() or None,
            original_filename=filename,
            content_type=content_type or "application/octet-stream",
            file_extension=ext,
            file_size_bytes=len(data),
            storage_bucket=bucket,
            storage_key=key,
            checksum_sha256=checksum,
            extraction_status="pending",
            is_active=True,
        )
        await self.repo.create(doc)

        try:
            text = self.extractor.extract(data=data, file_extension=ext)
            doc.extracted_text = text
            doc.extraction_status = "extracted"
            doc.extraction_error = None
        except ValidationAppError as exc:
            doc.extraction_status = "failed"
            doc.extraction_error = exc.message
            await self.session.flush()
            raise

        await self.session.flush()

        await self.audit.log(
            action="curriculum.document.uploaded",
            entity_type="course_enrichment_document",
            entity_id=doc.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "filename": filename,
                "domain": domain,
                "size": len(data),
                "extracted_chars": len(doc.extracted_text or ""),
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return self._to_out(doc)

    async def delete_document(
        self,
        *,
        doc_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None = None,
    ) -> None:
        doc = await self.repo.get_by_id(doc_id, organization_id)
        if not doc or not doc.is_active:
            raise NotFoundError("Enrichment document not found")
        doc.is_active = False
        await self.session.flush()
        try:
            self.storage.delete_object(bucket=doc.storage_bucket, key=doc.storage_key)
        except Exception as exc:  # noqa: BLE001
            logger.warning("enrichment_storage_delete_failed", error=str(exc))

        await self.audit.log(
            action="curriculum.document.deleted",
            entity_type="course_enrichment_document",
            entity_id=doc.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"filename": doc.original_filename, "domain": doc.domain},
            correlation_id=correlation_id,
        )

    async def build_enrichment_context(
        self, organization_id: UUID, domain: str
    ) -> tuple[str | None, list[str]]:
        """Concatenate extracted source text for course generation."""
        docs = await self.repo.list_for_course_domain(organization_id, domain)
        if not docs:
            return None, []

        chunks: list[str] = []
        titles: list[str] = []
        used = 0
        for doc in docs:
            text = (doc.extracted_text or "").strip()
            if not text:
                continue
            label = doc.title or doc.original_filename
            titles.append(label)
            piece = text[:PER_DOC_CHARS]
            header = f"### Source: {label} (domain={doc.domain})\n"
            remaining = TOTAL_ENRICH_CHARS - used
            if remaining <= 200:
                break
            body = piece[: remaining - len(header)]
            chunks.append(header + body)
            used += len(header) + len(body)

        if not chunks:
            return None, []
        return "\n\n".join(chunks), titles
