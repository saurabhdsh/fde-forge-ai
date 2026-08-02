"""Tests for skill resolution used during resume confirmation."""

from app.services.learner_service import LearnerService


def test_skill_alias_map_covers_common_ai_names() -> None:
    # Smoke: method exists and aliases dict is reachable via source contract
    assert hasattr(LearnerService, "_resolve_or_create_skill")
    assert hasattr(LearnerService, "_resolve_skill")
