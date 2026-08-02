"""Course enrichment document schemas."""

from datetime import datetime
from uuid import UUID

from app.schemas.common import APIModel


class CourseEnrichmentDocumentOut(APIModel):
    id: UUID
    organization_id: UUID
    uploaded_by_user_id: UUID | None = None
    domain: str
    title: str | None = None
    notes: str | None = None
    original_filename: str
    content_type: str
    file_extension: str
    file_size_bytes: int
    extraction_status: str
    extraction_error: str | None = None
    extracted_chars: int = 0
    is_active: bool = True
    created_at: datetime
