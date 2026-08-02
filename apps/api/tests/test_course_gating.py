"""Unit tests for domain course gating helpers."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.core.exceptions import ValidationAppError
from app.services.course_service import CourseService


def _service_with_profile(domains: list[str] | None, courses: list | None = None) -> CourseService:
    service = CourseService(MagicMock())
    profile = SimpleNamespace(domain_preferences=domains or [])
    service.learners = MagicMock()
    service.learners.get_by_user = AsyncMock(return_value=profile)
    service.repo = MagicMock()
    service.repo.list_for_user = AsyncMock(return_value=courses or [])
    return service


@pytest.mark.asyncio
async def test_normalize_domains() -> None:
    service = CourseService(MagicMock())
    assert service.normalize_domains(["Healthcare", "life-sciences", "technical", "other"]) == [
        "healthcare",
        "life_sciences",
        "technical",
    ]


@pytest.mark.asyncio
async def test_assessment_locked_when_courses_incomplete() -> None:
    uid, oid = uuid4(), uuid4()
    courses = [SimpleNamespace(domain="healthcare", status="in_progress")]
    service = _service_with_profile(["healthcare", "life_sciences"], courses)
    assert await service.is_assessment_unlocked(uid, oid) is False
    incomplete = await service.incomplete_domains(uid, oid)
    assert incomplete == ["healthcare", "life_sciences"]


@pytest.mark.asyncio
async def test_assessment_unlocked_when_all_completed() -> None:
    uid, oid = uuid4(), uuid4()
    courses = [
        SimpleNamespace(domain="healthcare", status="completed"),
        SimpleNamespace(domain="life_sciences", status="completed"),
    ]
    service = _service_with_profile(["healthcare", "life_sciences"], courses)
    assert await service.is_assessment_unlocked(uid, oid) is True
    assert await service.incomplete_domains(uid, oid) == []


@pytest.mark.asyncio
async def test_assessment_locked_without_domains() -> None:
    uid, oid = uuid4(), uuid4()
    service = _service_with_profile([])
    assert await service.is_assessment_unlocked(uid, oid) is False


@pytest.mark.asyncio
async def test_catalog_empty_without_domains() -> None:
    uid, oid = uuid4(), uuid4()
    service = _service_with_profile([])
    catalog = await service.catalog(uid, oid)
    assert catalog.domains == []
    assert catalog.items == []
    assert catalog.assessment_unlocked is False


@pytest.mark.asyncio
async def test_required_domains_raises_when_empty() -> None:
    uid, oid = uuid4(), uuid4()
    service = _service_with_profile([])
    with pytest.raises(ValidationAppError):
        await service.required_domains(uid, oid)
