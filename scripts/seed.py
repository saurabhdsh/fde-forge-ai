"""Idempotent demonstration seed for FDE Forge AI Phase 1."""

from __future__ import annotations

import sys
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Make API package importable when run as `python -m scripts.seed`
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.core.security import encrypt_password, hash_password  # noqa: E402
from app.domain.permissions import PERMISSIONS, ROLE_DEFINITIONS  # noqa: E402
from app.models.identity import (  # noqa: E402
    Organization,
    OrganizationSetting,
    Permission,
    Role,
    RolePermission,
    User,
    UserProfile,
    UserRole,
)
from app.models.learner import LearnerProfile  # noqa: E402
from app.models.skills import CompetencyPillar, Skill, SkillLevel  # noqa: E402

PILLARS = [
    ("ai_genai", "AI and Generative AI Engineering", 1),
    ("enterprise_swe", "Enterprise Software Engineering", 2),
    ("data_knowledge", "Data and Knowledge Engineering", 3),
    ("healthcare", "Healthcare Domain", 4),
    ("life_sciences", "Life Sciences Domain", 5),
    ("consulting", "Consulting and Customer Discovery", 6),
    ("rapid_build", "Rapid Build and Deployment", 7),
    ("communication", "Communication and Leadership", 8),
    ("security_rai", "Security, Compliance, and Responsible AI", 9),
]

SKILL_LEVELS = [
    ("not_assessed", "Not Assessed", 0),
    ("awareness", "Awareness", 1),
    ("foundational", "Foundational", 2),
    ("working", "Working", 3),
    ("proficient", "Proficient", 4),
    ("advanced", "Advanced", 5),
    ("expert", "Expert", 6),
]

SKILLS = [
    # AI / GenAI
    ("python_programming", "Python Programming", "ai_genai", "technical", "technical", "foundational"),
    ("rest_apis", "REST APIs", "ai_genai", "technical", "technical", "foundational"),
    ("machine_learning", "Machine Learning", "ai_genai", "technical", "technical", "working"),
    ("generative_ai", "Generative AI", "ai_genai", "technical", "technical", "working"),
    ("rag_engineering", "RAG Engineering", "ai_genai", "technical", "technical", "working"),
    ("agentic_ai", "Agentic AI", "ai_genai", "technical", "technical", "advanced"),
    ("prompt_engineering", "Prompt Engineering", "ai_genai", "technical", "technical", "foundational"),
    ("llm_evaluation", "LLM Evaluation", "ai_genai", "technical", "technical", "working"),
    # Enterprise SWE
    ("system_architecture", "System Architecture", "enterprise_swe", "technical", "technical", "working"),
    ("typescript", "TypeScript", "enterprise_swe", "technical", "technical", "foundational"),
    ("react", "React", "enterprise_swe", "technical", "technical", "foundational"),
    ("fastapi", "FastAPI", "enterprise_swe", "technical", "technical", "working"),
    ("postgresql", "PostgreSQL", "enterprise_swe", "technical", "technical", "foundational"),
    ("devops", "DevOps", "enterprise_swe", "technical", "technical", "working"),
    ("cloud_aws", "Cloud (AWS)", "enterprise_swe", "technical", "technical", "working"),
    # Data
    ("data_engineering", "Data Engineering", "data_knowledge", "technical", "technical", "working"),
    ("vector_databases", "Vector Databases", "data_knowledge", "technical", "technical", "working"),
    ("knowledge_graphs", "Knowledge Graphs", "data_knowledge", "technical", "technical", "advanced"),
    # Healthcare
    ("healthcare_ecosystem", "Healthcare Ecosystem", "healthcare", "domain", "healthcare", "foundational"),
    ("claims_processing", "Claims Processing", "healthcare", "domain", "healthcare", "working"),
    ("prior_authorization", "Prior Authorization", "healthcare", "domain", "healthcare", "working"),
    ("fhir", "FHIR", "healthcare", "domain", "healthcare", "working"),
    ("hipaa", "HIPAA", "healthcare", "domain", "healthcare", "foundational"),
    ("hedis_star", "HEDIS and STAR Ratings", "healthcare", "domain", "healthcare", "working"),
    ("value_based_care", "Value-Based Care", "healthcare", "domain", "healthcare", "working"),
    ("interoperability", "Healthcare Interoperability", "healthcare", "domain", "healthcare", "advanced"),
    # Life Sciences
    ("drug_discovery", "Drug Discovery", "life_sciences", "domain", "life_sciences", "foundational"),
    ("clinical_development", "Clinical Development", "life_sciences", "domain", "life_sciences", "working"),
    ("pharmacovigilance", "Pharmacovigilance", "life_sciences", "domain", "life_sciences", "working"),
    ("gcp_gxp", "GCP / GxP", "life_sciences", "domain", "life_sciences", "foundational"),
    ("regulatory_affairs", "Regulatory Affairs", "life_sciences", "domain", "life_sciences", "working"),
    ("cdisc", "CDISC", "life_sciences", "domain", "life_sciences", "working"),
    ("trial_master_file", "Trial Master File", "life_sciences", "domain", "life_sciences", "working"),
    # Consulting / Comm / Security
    ("customer_discovery", "Customer Discovery", "consulting", "consulting", "general", "working"),
    ("requirement_workshops", "Requirement Workshops", "consulting", "consulting", "general", "working"),
    ("stakeholder_management", "Stakeholder Management", "consulting", "consulting", "general", "working"),
    ("rapid_prototyping", "Rapid Prototyping", "rapid_build", "delivery", "technical", "working"),
    ("production_deployment", "Production Deployment", "rapid_build", "delivery", "technical", "advanced"),
    ("executive_communication", "Executive Communication", "communication", "communication", "general", "working"),
    ("technical_storytelling", "Technical Storytelling", "communication", "communication", "general", "working"),
    ("responsible_ai", "Responsible AI", "security_rai", "security", "general", "working"),
    ("security_fundamentals", "Security Fundamentals", "security_rai", "security", "general", "foundational"),
    ("compliance_governance", "Compliance Governance", "security_rai", "security", "general", "working"),
]


def get_or_create(session: Session, model, defaults: dict | None = None, **kwargs):
    instance = session.execute(select(model).filter_by(**kwargs)).scalar_one_or_none()
    if instance:
        return instance, False
    params = {**kwargs, **(defaults or {})}
    instance = model(**params)
    session.add(instance)
    session.flush()
    return instance, True


def seed() -> None:
    settings = get_settings()
    engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine)
    with SessionLocal() as session:
        # Permissions
        perm_map: dict[str, Permission] = {}
        for code, meta in PERMISSIONS.items():
            perm, _ = get_or_create(
                session,
                Permission,
                code=code,
                defaults={
                    "id": uuid4(),
                    "name": meta["name"],
                    "description": meta["description"],
                    "category": meta["category"],
                },
            )
            perm_map[code] = perm

        # System roles (global)
        role_map: dict[str, Role] = {}
        for code, meta in ROLE_DEFINITIONS.items():
            role, _ = get_or_create(
                session,
                Role,
                code=code,
                organization_id=None,
                defaults={
                    "id": uuid4(),
                    "name": str(meta["name"]),
                    "description": f"System role: {meta['name']}",
                    "is_system": True,
                },
            )
            role_map[code] = role
            for pcode in meta["permissions"]:  # type: ignore[index]
                if pcode not in perm_map:
                    continue
                exists = session.execute(
                    select(RolePermission).where(
                        RolePermission.role_id == role.id,
                        RolePermission.permission_id == perm_map[pcode].id,
                    )
                ).scalar_one_or_none()
                if not exists:
                    session.add(
                        RolePermission(
                            id=uuid4(),
                            role_id=role.id,
                            permission_id=perm_map[pcode].id,
                        )
                    )

        # Demo organization
        org, created_org = get_or_create(
            session,
            Organization,
            slug="acme-health",
            defaults={
                "id": uuid4(),
                "name": "Acme Health Academy",
                "status": "active",
                "branding": {
                    "product_name": settings.app_name,
                    "tagline": settings.app_tagline,
                    "primary_color": "#0F3D5E",
                },
                "is_demo": True,
            },
        )
        get_or_create(
            session,
            OrganizationSetting,
            organization_id=org.id,
            defaults={
                "id": uuid4(),
                "readiness_weights": {
                    "technical": 0.25,
                    "domain": 0.20,
                    "project": 0.20,
                    "consulting": 0.10,
                    "communication": 0.10,
                    "architecture": 0.10,
                    "security_compliance": 0.05,
                },
                "content_policies": {
                    "ai_requires_human_review": True,
                    "healthcare_disclaimer_required": True,
                    "life_sciences_sme_required": True,
                },
                "security_settings": {},
                "ai_limits": {"daily_budget_usd": 50},
                "certification_settings": {},
                "feature_flags": {"phase1_onboarding": True},
            },
        )

        # Skill levels & pillars
        for code, name, rank in SKILL_LEVELS:
            get_or_create(
                session,
                SkillLevel,
                code=code,
                defaults={"id": uuid4(), "name": name, "rank": rank, "description": name},
            )

        pillar_ids: dict[str, object] = {}
        for code, name, order in PILLARS:
            pillar, _ = get_or_create(
                session,
                CompetencyPillar,
                code=code,
                defaults={
                    "id": uuid4(),
                    "name": name,
                    "description": name,
                    "sort_order": order,
                    "is_active": True,
                },
            )
            pillar_ids[code] = pillar.id

        for code, name, pillar_code, category, domain, difficulty in SKILLS:
            get_or_create(
                session,
                Skill,
                code=code,
                version=1,
                defaults={
                    "id": uuid4(),
                    "name": name,
                    "description": name,
                    "pillar_id": pillar_ids[pillar_code],
                    "category": category,
                    "domain": domain,
                    "difficulty": difficulty,
                    "evidence_requirements": {"min_evidence": 1},
                    "assessment_mappings": {},
                    "learning_content_mappings": {},
                    "is_active": True,
                    "organization_id": None,
                },
            )

        def ensure_user(
            email: str,
            first: str,
            last: str,
            password: str,
            role_codes: list[str],
            *,
            username: str | None = None,
            super_admin: bool = False,
            learner: bool = False,
            sync_password: bool = False,
        ) -> User:
            login_name = (username or first).strip()

            def claim_username(target: User, name: str) -> None:
                clashes = session.execute(
                    select(User).where(
                        User.organization_id == org.id,
                        User.username.ilike(name),
                        User.id != target.id,
                    )
                ).scalars().all()
                for other in clashes:
                    other.username = f"{name}_{str(other.id).replace('-', '')[:4]}"
                target.username = name

            user, created = get_or_create(
                session,
                User,
                organization_id=org.id,
                email=email.lower(),
                defaults={
                    "id": uuid4(),
                    "username": login_name,
                    "password_hash": hash_password(password),
                    "password_encrypted": encrypt_password(password),
                    "first_name": first,
                    "last_name": last,
                    "status": "active",
                    "email_verified": True,
                    "is_super_admin": super_admin,
                },
            )
            if created:
                session.add(
                    UserProfile(
                        id=uuid4(),
                        user_id=user.id,
                        organization_id=org.id,
                        preferences={},
                    )
                )
                # Ensure unique if default collided with an existing username.
                claim_username(user, login_name)
            elif sync_password:
                claim_username(user, login_name)
                user.first_name = first
                user.last_name = last
                user.password_hash = hash_password(password)
                user.password_encrypted = encrypt_password(password)
                user.is_super_admin = super_admin
                user.status = "active"
                user.email_verified = True
            else:
                if not user.username:
                    claim_username(user, login_name)
                if not user.password_encrypted:
                    user.password_encrypted = encrypt_password(password)
                    user.password_hash = hash_password(password)
            for rcode in role_codes:
                role = role_map[rcode]
                exists = session.execute(
                    select(UserRole).where(
                        UserRole.user_id == user.id, UserRole.role_id == role.id
                    )
                ).scalar_one_or_none()
                if not exists:
                    session.add(
                        UserRole(
                            id=uuid4(),
                            user_id=user.id,
                            role_id=role.id,
                            organization_id=org.id,
                        )
                    )
            if learner:
                get_or_create(
                    session,
                    LearnerProfile,
                    user_id=user.id,
                    defaults={
                        "id": uuid4(),
                        "organization_id": org.id,
                        "onboarding_status": "invited",
                    },
                )
            return user

        # Saurabh is both a Candidate (profile/resume journey) and an Org Admin (User Management).
        # Login with username "Saurabh" (no email shown in the UI after login).
        ensure_user(
            settings.seed_admin_email,
            "Saurabh",
            "Dubey",
            settings.seed_admin_password,
            ["platform_super_admin", "organization_admin", "learner"],
            username="Saurabh",
            super_admin=True,
            sync_password=True,
            learner=True,
        )
        ensure_user(
            "academy.admin@fdeforge.example.com",
            "Academy",
            "Admin",
            settings.seed_admin_password,
            ["academy_admin"],
        )
        ensure_user(
            "mentor@fdeforge.example.com",
            "Maya",
            "Mentor",
            settings.seed_admin_password,
            ["mentor"],
        )
        ensure_user(
            "evaluator@fdeforge.example.com",
            "Evan",
            "Evaluator",
            settings.seed_admin_password,
            ["evaluator"],
        )
        for i, name in enumerate(
            [("Alex", "Learner"), ("Jordan", "Patel"), ("Sam", "Nguyen")], start=1
        ):
            ensure_user(
                f"learner{i}@fdeforge.example.com",
                name[0],
                name[1],
                settings.seed_learner_password,
                ["learner"],
                learner=True,
            )

        session.commit()
        print("Seed completed successfully.")
        print(f"Organization: {org.name} ({org.slug})")
        print(f"Admin username: Saurabh / {settings.seed_admin_password} (org: {org.slug})")
        print(f"Learners: Alex / Jordan / Sam / {settings.seed_learner_password}")


if __name__ == "__main__":
    seed()
