"""Celery tasks for Phase 1 (resume extraction can also run sync; async path ready)."""

from __future__ import annotations

from uuid import UUID

from app.core.logging import get_logger
from app.worker.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="jobs.ping")
def ping() -> dict[str, str]:
    return {"status": "ok"}


@celery_app.task(name="jobs.resume_extract", bind=True)
def resume_extract_task(self, resume_id: str, organization_id: str, user_id: str) -> dict:
    """Placeholder async entry — Phase 1 extraction runs inline in API for acceptance path.

    Future phases will move heavy extraction fully into this worker.
    """
    logger.info(
        "resume_extract_task",
        task_id=self.request.id,
        resume_id=resume_id,
        organization_id=organization_id,
        user_id=user_id,
    )
    return {
        "status": "queued_inline_phase1",
        "resume_id": resume_id,
        "organization_id": str(UUID(organization_id)),
        "user_id": str(UUID(user_id)),
    }
