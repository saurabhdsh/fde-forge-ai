"""Permission codes and role → permission mappings."""

from __future__ import annotations

# Permission codes used for authorization checks
PERMISSIONS: dict[str, dict[str, str]] = {
    "organization.manage": {
        "name": "Manage Organization",
        "category": "organization",
        "description": "Create and update organization settings",
    },
    "organization.view": {
        "name": "View Organization",
        "category": "organization",
        "description": "View organization details",
    },
    "user.create": {
        "name": "Create Users",
        "category": "users",
        "description": "Invite or create users",
    },
    "user.view": {
        "name": "View Users",
        "category": "users",
        "description": "View users in organization",
    },
    "user.manage": {
        "name": "Manage Users",
        "category": "users",
        "description": "Update users and assignments",
    },
    "role.manage": {
        "name": "Manage Roles",
        "category": "users",
        "description": "Assign roles and permissions",
    },
    "learner.view": {
        "name": "View Learners",
        "category": "learners",
        "description": "View learner profiles",
    },
    "learner.manage": {
        "name": "Manage Learners",
        "category": "learners",
        "description": "Manage learner profiles and onboarding",
    },
    "learner.self": {
        "name": "Manage Own Learner Profile",
        "category": "learners",
        "description": "Manage own learner profile and resume",
    },
    "curriculum.create": {
        "name": "Create Curriculum",
        "category": "curriculum",
        "description": "Create curriculum content",
    },
    "curriculum.review": {
        "name": "Review Curriculum",
        "category": "curriculum",
        "description": "Review curriculum content",
    },
    "curriculum.publish": {
        "name": "Publish Curriculum",
        "category": "curriculum",
        "description": "Publish curriculum content",
    },
    "assessment.generate": {
        "name": "Generate Assessments",
        "category": "assessments",
        "description": "Generate assessments with AI",
    },
    "assessment.approve": {
        "name": "Approve Assessments",
        "category": "assessments",
        "description": "Approve assessments",
    },
    "learner.evaluate": {
        "name": "Evaluate Learners",
        "category": "evaluation",
        "description": "Evaluate learner submissions",
    },
    "certification.approve": {
        "name": "Approve Certification",
        "category": "certification",
        "description": "Approve certification decisions",
    },
    "analytics.executive": {
        "name": "Executive Analytics",
        "category": "analytics",
        "description": "View executive analytics",
    },
    "audit.read": {
        "name": "Read Audit Logs",
        "category": "audit",
        "description": "Read audit logs",
    },
    "ai_configuration.manage": {
        "name": "Manage AI Configuration",
        "category": "ai",
        "description": "Manage AI providers and limits",
    },
    "mentor.manage": {
        "name": "Mentor Learners",
        "category": "mentoring",
        "description": "Mentor assigned learners",
    },
}

# System roles (organization_id = NULL for global templates; cloned per org on seed)
ROLE_DEFINITIONS: dict[str, dict[str, object]] = {
    "platform_super_admin": {
        "name": "Platform Super Admin",
        "permissions": list(PERMISSIONS.keys()),
    },
    "organization_admin": {
        "name": "Organization Admin",
        "permissions": [
            "organization.manage",
            "organization.view",
            "user.create",
            "user.view",
            "user.manage",
            "role.manage",
            "learner.view",
            "learner.manage",
            "audit.read",
            "ai_configuration.manage",
            "analytics.executive",
            "curriculum.create",
            "curriculum.review",
            "curriculum.publish",
            "assessment.generate",
            "assessment.approve",
            "certification.approve",
        ],
    },
    "academy_admin": {
        "name": "Academy Admin",
        "permissions": [
            "organization.view",
            "user.view",
            "learner.view",
            "learner.manage",
            "curriculum.create",
            "curriculum.review",
            "curriculum.publish",
            "assessment.generate",
            "assessment.approve",
            "analytics.executive",
        ],
    },
    "curriculum_manager": {
        "name": "Curriculum Manager",
        "permissions": [
            "curriculum.create",
            "curriculum.review",
            "curriculum.publish",
            "assessment.generate",
            "learner.view",
        ],
    },
    "domain_expert": {
        "name": "Domain Expert",
        "permissions": ["curriculum.review", "learner.view", "learner.evaluate"],
    },
    "technical_reviewer": {
        "name": "Technical Reviewer",
        "permissions": ["curriculum.review", "assessment.approve", "learner.evaluate"],
    },
    "compliance_reviewer": {
        "name": "Compliance Reviewer",
        "permissions": ["curriculum.review", "assessment.approve", "audit.read"],
    },
    "mentor": {
        "name": "Mentor",
        "permissions": [
            "learner.view",
            "learner.evaluate",
            "mentor.manage",
            "certification.approve",
        ],
    },
    "evaluator": {
        "name": "Evaluator",
        "permissions": ["learner.view", "learner.evaluate", "assessment.approve"],
    },
    "delivery_manager": {
        "name": "Delivery Manager",
        "permissions": ["learner.view", "analytics.executive", "certification.approve"],
    },
    "resource_manager": {
        "name": "Resource Manager",
        "permissions": ["learner.view", "analytics.executive", "user.view"],
    },
    "learner": {
        "name": "Learner",
        "permissions": ["learner.self", "organization.view"],
    },
    "auditor": {
        "name": "Auditor",
        "permissions": ["audit.read", "organization.view", "learner.view"],
    },
    "executive_viewer": {
        "name": "Executive Viewer",
        "permissions": ["analytics.executive", "organization.view", "learner.view"],
    },
}
