"""Permission taxonomy tests."""

from app.domain.permissions import PERMISSIONS, ROLE_DEFINITIONS


def test_required_permissions_exist() -> None:
    required = [
        "curriculum.create",
        "curriculum.review",
        "curriculum.publish",
        "assessment.generate",
        "assessment.approve",
        "learner.view",
        "learner.evaluate",
        "certification.approve",
        "analytics.executive",
        "audit.read",
        "organization.manage",
        "ai_configuration.manage",
    ]
    for code in required:
        assert code in PERMISSIONS


def test_all_roles_defined() -> None:
    expected = {
        "platform_super_admin",
        "organization_admin",
        "academy_admin",
        "curriculum_manager",
        "domain_expert",
        "technical_reviewer",
        "compliance_reviewer",
        "mentor",
        "evaluator",
        "delivery_manager",
        "resource_manager",
        "learner",
        "auditor",
        "executive_viewer",
    }
    assert expected.issubset(set(ROLE_DEFINITIONS.keys()))
