"""Domain super-course generation, progress, and assessment gating."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway, sanitize_for_prompt
from app.ai.prompts.domain_course import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.domain.course_topics import (
    default_topic_ids,
    resolve_topics,
    topics_for_domain,
)
from app.models.course import Course, CourseModule, CourseProgress, CourseSlide
from app.repositories.course import CourseRepository
from app.repositories.learner import LearnerRepository
from app.schemas.course import (
    CourseCatalogItem,
    CourseCatalogOut,
    CourseModuleOut,
    CourseOut,
    CourseProgressOut,
    CourseSlideOut,
    CourseTopicOut,
    GeneratedCoursePayload,
)
from app.services.audit_service import AuditService
from app.services.curriculum_service import CurriculumService

logger = get_logger(__name__)

SUPPORTED_DOMAINS = ("healthcare", "life_sciences", "technical")
DOMAIN_HINTS = {
    "healthcare": {
        "title_hint": "Healthcare FDE Super-Course",
        "description": "Care continuum, interop, privacy, and customer deployment for healthcare FDEs.",
    },
    "life_sciences": {
        "title_hint": "Life Sciences FDE Super-Course",
        "description": "R&D-to-regulatory path, GxP, clinical data, and AI validation for LS FDEs.",
    },
    "technical": {
        "title_hint": "Technical FDE Super-Course",
        "description": "Architecture, GenAI delivery, cloud, and production hardening for technical FDEs.",
    },
}


def normalize_domain_preferences(prefs: list | None) -> list[str]:
    """Map free-text / UI domain labels onto supported course domains."""
    prefs = prefs or []
    out: list[str] = []
    for d in prefs:
        key = str(d).strip().lower().replace(" ", "_").replace("-", "_")
        if key in {
            "life_science",
            "lifesciences",
            "life_sciences",
            "pharma",
            "pharmaceutical",
            "biotech",
        }:
            key = "life_sciences"
        elif key in {
            "health",
            "health_care",
            "healthcare",
            "payer",
            "provider",
            "clinical",
        }:
            key = "healthcare"
        elif key in {
            "tech",
            "technical",
            "technology",
            "engineering",
            "software",
            "genai",
            "ai",
            "enterprise",
        }:
            key = "technical"
        if key in SUPPORTED_DOMAINS and key not in out:
            out.append(key)
    return out


class CourseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CourseRepository(session)
        self.learners = LearnerRepository(session)
        self.audit = AuditService(session)
        self.ai = AIGateway()
        self.settings = get_settings()
        self.curriculum = CurriculumService(session)

    def normalize_domains(self, prefs: list | None) -> list[str]:
        return normalize_domain_preferences(prefs)

    async def required_domains(self, user_id: UUID, organization_id: UUID) -> list[str]:
        profile = await self.learners.get_by_user(user_id, organization_id)
        if not profile:
            raise NotFoundError("Learner profile not found")
        domains = self.normalize_domains(list(profile.domain_preferences or []))
        if not domains:
            raise ValidationAppError(
                "Select at least one domain (healthcare, life_sciences, or technical) "
                "in My profile before starting courses."
            )
        return domains

    async def incomplete_domains(self, user_id: UUID, organization_id: UUID) -> list[str]:
        try:
            domains = await self.required_domains(user_id, organization_id)
        except (NotFoundError, ValidationAppError):
            return []
        courses = await self.repo.list_for_user(user_id, organization_id)
        by_domain = {c.domain: c for c in courses}
        return [
            d
            for d in domains
            if not by_domain.get(d) or by_domain[d].status != "completed"
        ]

    async def is_assessment_unlocked(self, user_id: UUID, organization_id: UUID) -> bool:
        try:
            domains = await self.required_domains(user_id, organization_id)
        except (NotFoundError, ValidationAppError):
            return False
        if not domains:
            return False
        incomplete = await self.incomplete_domains(user_id, organization_id)
        return len(incomplete) == 0

    def _selected_ids_for_domain(self, profile, domain: str) -> list[str]:
        prefs = dict(profile.course_topic_preferences or {})
        raw = prefs.get(domain) or []
        resolved = resolve_topics(domain, [str(x) for x in raw])
        if resolved:
            return [t["id"] for t in resolved]
        return default_topic_ids(domain)

    async def catalog(
        self, user_id: UUID, organization_id: UUID
    ) -> CourseCatalogOut:
        profile = await self.learners.get_by_user(user_id, organization_id)
        if not profile:
            raise NotFoundError("Learner profile not found")
        domains = self.normalize_domains(list(profile.domain_preferences or []))
        courses = await self.repo.list_for_user(user_id, organization_id)
        by_domain = {c.domain: c for c in courses}
        items: list[CourseCatalogItem] = []
        for d in domains:
            hint = DOMAIN_HINTS[d]
            course = by_domain.get(d)
            topic_defs = topics_for_domain(d)
            selected = self._selected_ids_for_domain(profile, d)
            items.append(
                CourseCatalogItem(
                    domain=d,
                    required=True,
                    course=self._to_out(course) if course else None,
                    title_hint=hint["title_hint"],
                    description=hint["description"],
                    topics=[CourseTopicOut(**t) for t in topic_defs],
                    selected_topic_ids=selected,
                )
            )
        unlocked = bool(domains) and not await self.incomplete_domains(
            user_id, organization_id
        )
        return CourseCatalogOut(
            domains=domains,
            items=items,
            assessment_unlocked=unlocked,
        )

    async def save_topic_selection(
        self,
        *,
        domain: str,
        topic_ids: list[str],
        user_id: UUID,
        organization_id: UUID,
    ) -> CourseCatalogItem:
        domain = domain.strip().lower()
        if domain not in SUPPORTED_DOMAINS:
            raise ValidationAppError(f"Unsupported domain: {domain}")
        required = await self.required_domains(user_id, organization_id)
        if domain not in required:
            raise ValidationAppError(
                f"Domain '{domain}' is not in your profile preferences. Update My profile first."
            )
        resolved = resolve_topics(domain, topic_ids)
        if not resolved:
            raise ValidationAppError("Select at least one valid topic for this domain")
        if len(resolved) > 24:
            raise ValidationAppError("Select at most 24 topics per domain course")

        profile = await self.learners.get_by_user(user_id, organization_id)
        assert profile is not None
        prefs = dict(profile.course_topic_preferences or {})
        prefs[domain] = [t["id"] for t in resolved]
        profile.course_topic_preferences = prefs
        await self.session.flush()

        course = await self.repo.get_by_domain(user_id, organization_id, domain)
        hint = DOMAIN_HINTS[domain]
        return CourseCatalogItem(
            domain=domain,
            required=True,
            course=self._to_out(course) if course else None,
            title_hint=hint["title_hint"],
            description=hint["description"],
            topics=[CourseTopicOut(**t) for t in topics_for_domain(domain)],
            selected_topic_ids=prefs[domain],
        )

    async def ensure_course(
        self,
        *,
        domain: str,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
        force_regenerate: bool = False,
        topic_ids: list[str] | None = None,
    ) -> CourseOut:
        domain = domain.strip().lower()
        if domain not in SUPPORTED_DOMAINS:
            raise ValidationAppError(f"Unsupported domain: {domain}")
        required = await self.required_domains(user_id, organization_id)
        if domain not in required:
            raise ValidationAppError(
                f"Domain '{domain}' is not in your profile preferences. Update My profile first."
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        assert profile is not None

        if topic_ids is not None:
            await self.save_topic_selection(
                domain=domain,
                topic_ids=topic_ids,
                user_id=user_id,
                organization_id=organization_id,
            )
            await self.session.refresh(profile)

        selected_ids = self._selected_ids_for_domain(profile, domain)
        selected_topics = resolve_topics(domain, selected_ids)
        if not selected_topics:
            raise ValidationAppError("Select at least one topic before generating this course")

        existing = await self.repo.get_by_domain(user_id, organization_id, domain)
        if existing and existing.status in {"ready", "in_progress", "completed"} and not force_regenerate:
            return self._to_out(existing)
        if existing and existing.status == "generating":
            raise ValidationAppError("Course generation already in progress. Wait and refresh.")

        if not self.settings.ai_configured:
            raise ConfigurationError(
                "No AI provider ready. Set OPENAI_API_KEY or enable Bedrock (BEDROCK_ENABLED=true + AWS creds)."
            )

        if existing and (force_regenerate or existing.status == "failed"):
            await self.session.delete(existing)
            await self.session.flush()

        course = Course(
            user_id=user_id,
            organization_id=organization_id,
            domain=domain,
            title=DOMAIN_HINTS[domain]["title_hint"],
            summary=None,
            status="generating",
            prompt_version=PROMPT_VERSION,
            learning_goals=[],
            selected_topics=selected_ids,
        )
        await self.repo.create(course)
        self.session.add(
            CourseProgress(
                user_id=user_id,
                course_id=course.id,
                completed_slide_ids=[],
                percent_complete=0.0,
            )
        )
        await self.session.flush()

        enrich_titles: list[str] = []
        enrich_safe: str | None = None
        module_count = 0
        try:
            enrich_raw, enrich_titles = await self.curriculum.build_enrichment_context(
                organization_id, domain
            )
            enrich_safe = (
                sanitize_for_prompt(enrich_raw, max_chars=40000) if enrich_raw else None
            )
            result = await self.ai.generate_structured(
                prompt=build_user_prompt(
                    domain=domain,
                    target_role=profile.target_fde_role,
                    other_domains=[d for d in required if d != domain],
                    enrichment_text=enrich_safe,
                    enrichment_sources=enrich_titles,
                    selected_topics=selected_topics,
                ),
                schema=GeneratedCoursePayload,
                system=SYSTEM_PROMPT,
                temperature=0.25,
                max_output_tokens=8192,
            )
            payload = GeneratedCoursePayload.model_validate(result.data)
            course.title = payload.title.strip() or course.title
            course.summary = payload.summary.strip()
            course.learning_goals = list(payload.learning_goals or [])
            course.provider = result.provider
            course.model = result.model
            course.status = "ready"
            course.error_message = None

            module_count = 0
            for mi, mod in enumerate(payload.modules[:7]):
                slides = mod.slides[:10]
                if not slides:
                    continue
                cm = CourseModule(
                    course_id=course.id,
                    title=mod.title.strip(),
                    objectives=list(mod.objectives or []),
                    sort_order=mi,
                    status="ready",
                )
                self.session.add(cm)
                await self.session.flush()
                for si, slide in enumerate(slides):
                    visual_type = slide.visual_type or "none"
                    if visual_type not in {"map", "diagram", "process", "timeline", "cards", "none"}:
                        visual_type = "none"
                    self.session.add(
                        CourseSlide(
                            module_id=cm.id,
                            title=slide.title.strip(),
                            body_markdown=slide.body_markdown.strip(),
                            visual_type=visual_type,
                            visual_payload=dict(slide.visual_payload or {}),
                            key_takeaway=(slide.key_takeaway or "").strip() or None,
                            self_check=slide.self_check.model_dump() if slide.self_check else None,
                            sort_order=si,
                        )
                    )
                module_count += 1

            if module_count == 0:
                raise ValidationAppError("AI returned a course with no usable modules")

            await self.session.flush()
        except ConfigurationError:
            course.status = "failed"
            course.error_message = "OPENAI_API_KEY is not configured"
            await self.session.flush()
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("course_generation_failed", error=str(exc), domain=domain)
            course.status = "failed"
            course.error_message = str(exc)
            await self.session.flush()
            raise

        await self.audit.log(
            action="course.generated",
            entity_type="course",
            entity_id=course.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "domain": domain,
                "modules": module_count,
                "prompt_version": PROMPT_VERSION,
                "enrichment_sources": enrich_titles,
                "enrichment_used": bool(enrich_safe),
                "selected_topics": selected_ids,
            },
            correlation_id=correlation_id,
        )
        refreshed = await self.repo.get_by_id(course.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def get_course(
        self, course_id: UUID, user_id: UUID, organization_id: UUID
    ) -> CourseOut:
        course = await self.repo.get_by_id(course_id, organization_id)
        if not course or course.user_id != user_id:
            raise NotFoundError("Course not found")
        return self._to_out(course)

    async def complete_slide(
        self,
        *,
        course_id: UUID,
        slide_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> CourseOut:
        course = await self.repo.get_by_id(course_id, organization_id)
        if not course or course.user_id != user_id:
            raise NotFoundError("Course not found")
        if course.status not in {"ready", "in_progress", "completed"}:
            raise ValidationAppError("Course is not ready to study")

        slide = await self.repo.get_slide(slide_id)
        if not slide or slide.module.course_id != course.id:
            raise NotFoundError("Slide not found")

        progress = course.progress
        if not progress:
            progress = CourseProgress(
                user_id=user_id,
                course_id=course.id,
                completed_slide_ids=[],
                percent_complete=0.0,
            )
            self.session.add(progress)
            await self.session.flush()

        completed = {str(x) for x in (progress.completed_slide_ids or [])}
        completed.add(str(slide_id))
        progress.completed_slide_ids = sorted(completed)
        progress.current_module_id = slide.module_id
        progress.current_slide_id = slide_id

        all_slide_ids = [
            str(s.id) for m in course.modules for s in m.slides
        ]
        total = len(all_slide_ids) or 1
        progress.percent_complete = round(100.0 * len(completed) / total, 1)

        if course.status == "ready":
            course.status = "in_progress"

        if len(completed) >= total:
            course.status = "completed"
            course.completed_at = datetime.now(UTC)
            progress.completed_at = course.completed_at
            progress.percent_complete = 100.0
            await self.audit.log(
                action="course.completed",
                entity_type="course",
                entity_id=course.id,
                organization_id=organization_id,
                actor_id=actor_id,
                after={"domain": course.domain},
                correlation_id=correlation_id,
            )

            profile = await self.learners.get_by_user(user_id, organization_id)
            if profile and await self.is_assessment_unlocked(user_id, organization_id):
                if profile.onboarding_status in {
                    "skills_confirmed",
                    "assessment_completed",
                    "plan_ready",
                    "courses_in_progress",
                }:
                    profile.onboarding_status = "courses_completed"

        await self.session.flush()
        refreshed = await self.repo.get_by_id(course.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    def _to_out(self, course: Course) -> CourseOut:
        completed_ids = set()
        progress_out = None
        if course.progress:
            completed_ids = {str(x) for x in (course.progress.completed_slide_ids or [])}
            progress_out = CourseProgressOut(
                percent_complete=course.progress.percent_complete or 0,
                completed_slide_ids=sorted(completed_ids),
                current_module_id=course.progress.current_module_id,
                current_slide_id=course.progress.current_slide_id,
                completed_at=course.progress.completed_at,
            )

        modules: list[CourseModuleOut] = []
        total_slides = 0
        for m in course.modules:
            slides: list[CourseSlideOut] = []
            for s in m.slides:
                total_slides += 1
                slides.append(
                    CourseSlideOut(
                        id=s.id,
                        module_id=s.module_id,
                        title=s.title,
                        body_markdown=s.body_markdown,
                        visual_type=s.visual_type,
                        visual_payload=dict(s.visual_payload or {}),
                        key_takeaway=s.key_takeaway,
                        self_check=s.self_check,
                        sort_order=s.sort_order,
                        completed=str(s.id) in completed_ids,
                    )
                )
            modules.append(
                CourseModuleOut(
                    id=m.id,
                    title=m.title,
                    objectives=list(m.objectives or []),
                    sort_order=m.sort_order,
                    status=m.status,
                    slides=slides,
                )
            )

        return CourseOut(
            id=course.id,
            domain=course.domain,
            title=course.title,
            summary=course.summary,
            status=course.status,
            learning_goals=list(course.learning_goals or []),
            selected_topics=list(course.selected_topics or []),
            provider=course.provider,
            model=course.model,
            prompt_version=course.prompt_version,
            error_message=course.error_message,
            created_at=course.created_at,
            completed_at=course.completed_at,
            modules=modules,
            progress=progress_out,
            total_slides=total_slides,
            completed_slides=len(completed_ids),
        )
