"""Learner profile, resume upload, AI extraction, and skill confirmation."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway, hallucination_risk_score, sanitize_for_prompt
from app.ai.prompts.resume_extraction import PROMPT_VERSION, SYSTEM_PROMPT, build_user_prompt
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    ForbiddenError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.models.learner import AIExtractionRecord, LearnerProfile, ResumeDocument
from app.models.skills import LearnerSkill, Skill
from app.repositories.learner import LearnerRepository
from app.repositories.skills import SkillsRepository
from app.schemas.learner import (
    AIExtractionOut,
    ConfirmSkillsRequest,
    LearnerProfileOut,
    LearnerProfileUpdate,
    ResumeDocumentOut,
    ResumeExtractionPayload,
)
from app.schemas.skills import LearnerSkillOut
from app.services.audit_service import AuditService
from app.services.document_extraction import DocumentExtractionService
from app.services.storage_service import StorageService

logger = get_logger(__name__)


class LearnerService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LearnerRepository(session)
        self.skills = SkillsRepository(session)
        self.audit = AuditService(session)
        self.storage = StorageService()
        self.extractor = DocumentExtractionService()
        self.ai = AIGateway()
        self.settings = get_settings()

    async def get_or_create_profile(
        self, user_id: UUID, organization_id: UUID
    ) -> LearnerProfile:
        profile = await self.repo.get_by_user(user_id, organization_id)
        if profile:
            return profile
        profile = LearnerProfile(
            user_id=user_id,
            organization_id=organization_id,
            onboarding_status="profile_incomplete",
        )
        return await self.repo.create(profile)

    async def get_profile(self, user_id: UUID, organization_id: UUID) -> LearnerProfileOut:
        profile = await self.get_or_create_profile(user_id, organization_id)
        return LearnerProfileOut.model_validate(profile)

    async def update_profile(
        self,
        user_id: UUID,
        organization_id: UUID,
        payload: LearnerProfileUpdate,
        *,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LearnerProfileOut:
        profile = await self.get_or_create_profile(user_id, organization_id)
        before = {"onboarding_status": profile.onboarding_status}

        for field in (
            "target_fde_role",
            "career_interests",
            "domain_preferences",
            "technical_experience",
            "project_experience",
            "domain_experience",
            "existing_certifications",
            "years_of_experience",
            "available_weekly_hours",
            "summary",
        ):
            value = getattr(payload, field)
            if value is not None:
                setattr(profile, field, value)

        if payload.consent_privacy is not None:
            profile.consent_privacy = payload.consent_privacy
        if payload.consent_ai_processing is not None:
            profile.consent_ai_processing = payload.consent_ai_processing
        if profile.consent_privacy and profile.consent_ai_processing:
            profile.consent_timestamp = datetime.now(UTC)

        if (
            profile.consent_privacy
            and profile.consent_ai_processing
            and profile.target_fde_role
        ):
            profile.onboarding_status = "profile_complete"
            profile.profile_completed_at = datetime.now(UTC)

        await self.session.flush()
        await self.audit.log(
            action="learner.profile_update",
            entity_type="learner_profile",
            entity_id=profile.id,
            organization_id=organization_id,
            actor_id=actor_id,
            before=before,
            after={"onboarding_status": profile.onboarding_status},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return LearnerProfileOut.model_validate(profile)

    async def upload_resume(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[ResumeDocumentOut, AIExtractionOut | None]:
        profile = await self.get_or_create_profile(user_id, organization_id)
        if not profile.consent_ai_processing:
            raise ForbiddenError(
                "AI processing consent is required before uploading a resume for extraction"
            )

        ext = Path(filename).suffix.lower().lstrip(".")
        if ext not in self.settings.allowed_file_type_list:
            raise ValidationAppError(
                "File type not allowed",
                details={"allowed": self.settings.allowed_file_type_list},
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
            folder="resumes",
            filename=filename,
            content_type=content_type or "application/octet-stream",
        )

        await self.repo.mark_resumes_not_latest(profile.id)
        resume = ResumeDocument(
            learner_profile_id=profile.id,
            user_id=user_id,
            organization_id=organization_id,
            original_filename=filename,
            content_type=content_type or "application/octet-stream",
            file_extension=ext,
            file_size_bytes=len(data),
            storage_bucket=bucket,
            storage_key=key,
            checksum_sha256=checksum,
            extraction_status="pending",
            is_latest=True,
        )
        await self.repo.create_resume(resume)

        await self.audit.log(
            action="file.upload",
            entity_type="resume_document",
            entity_id=resume.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "filename": filename,
                "size": len(data),
                "storage_key": key,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Extract text immediately
        try:
            text = self.extractor.extract(data=data, file_extension=ext)
            resume.extracted_text = text
            resume.extraction_status = "extracted"
        except ValidationAppError as exc:
            resume.extraction_status = "failed"
            resume.extraction_error = exc.message
            await self.session.flush()
            raise

        await self.session.flush()
        profile.onboarding_status = "resume_uploaded"

        extraction_out: AIExtractionOut | None = None
        try:
            extraction_out = await self._run_ai_extraction(
                resume=resume,
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
            profile.onboarding_status = "skills_extracted"
        except ConfigurationError as exc:
            # Persist file + extracted text; surface configuration gap without fabricating AI output
            logger.warning("ai_not_configured", error=exc.message)
            resume.extraction_error = exc.message
            record = AIExtractionRecord(
                resume_document_id=resume.id,
                user_id=user_id,
                organization_id=organization_id,
                provider=self.settings.ai_default_provider,
                model=self.settings.ai_default_model,
                prompt_version=PROMPT_VERSION,
                status="configuration_error",
                error_message=exc.message,
                correlation_id=correlation_id,
            )
            await self.repo.create_extraction(record)
            extraction_out = self._extraction_out(record)
        except Exception as exc:  # noqa: BLE001
            logger.error("ai_extraction_failed", error=str(exc))
            record = AIExtractionRecord(
                resume_document_id=resume.id,
                user_id=user_id,
                organization_id=organization_id,
                provider=self.settings.ai_default_provider,
                model=self.settings.ai_default_model,
                prompt_version=PROMPT_VERSION,
                status="failed",
                error_message=str(exc),
                correlation_id=correlation_id,
            )
            await self.repo.create_extraction(record)
            extraction_out = self._extraction_out(record)

        await self.session.flush()
        return self._resume_out(resume), extraction_out

    async def retry_extraction(
        self,
        *,
        resume_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> AIExtractionOut:
        resume = await self.repo.get_resume(resume_id, organization_id)
        if not resume or resume.user_id != user_id:
            raise NotFoundError("Resume not found")
        if not resume.extracted_text:
            data = self.storage.download_bytes(
                bucket=resume.storage_bucket, key=resume.storage_key
            )
            resume.extracted_text = self.extractor.extract(
                data=data, file_extension=resume.file_extension
            )
            resume.extraction_status = "extracted"
            await self.session.flush()
        return await self._run_ai_extraction(
            resume=resume, actor_id=actor_id, correlation_id=correlation_id
        )

    async def _run_ai_extraction(
        self,
        *,
        resume: ResumeDocument,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> AIExtractionOut:
        if not self.settings.ai_configured:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Resume text was stored; "
                "configure OpenAI and retry extraction."
            )
        if not resume.extracted_text:
            raise ValidationAppError("No extracted text available for AI processing")

        safe_text = sanitize_for_prompt(resume.extracted_text)
        result = await self.ai.generate_structured(
            prompt=build_user_prompt(safe_text),
            schema=ResumeExtractionPayload,
            system=SYSTEM_PROMPT,
            temperature=0.1,
            max_output_tokens=4096,
        )
        risk = hallucination_risk_score(result.data)
        record = AIExtractionRecord(
            resume_document_id=resume.id,
            user_id=resume.user_id,
            organization_id=resume.organization_id,
            provider=result.provider,
            model=result.model,
            prompt_version=PROMPT_VERSION,
            status="awaiting_confirmation",
            raw_response=result.raw,
            validated_payload=result.data,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            estimated_cost_usd=result.estimated_cost_usd,
            hallucination_risk_score=risk,
            correlation_id=correlation_id,
        )
        await self.repo.create_extraction(record)
        await self.audit.log(
            action="ai.resume_extraction",
            entity_type="ai_extraction_record",
            entity_id=record.id,
            organization_id=resume.organization_id,
            actor_id=actor_id,
            after={
                "provider": result.provider,
                "model": result.model,
                "prompt_version": PROMPT_VERSION,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "estimated_cost_usd": result.estimated_cost_usd,
                "hallucination_risk_score": risk,
            },
            correlation_id=correlation_id,
        )
        return self._extraction_out(record)

    async def get_latest_extraction(
        self, user_id: UUID, organization_id: UUID
    ) -> AIExtractionOut | None:
        profile = await self.repo.get_by_user(user_id, organization_id)
        if not profile:
            return None
        latest_resume = next((r for r in profile.resumes if r.is_latest), None)
        if not latest_resume or not latest_resume.ai_extractions:
            return None
        latest = sorted(
            latest_resume.ai_extractions, key=lambda x: x.created_at, reverse=True
        )[0]
        return self._extraction_out(latest)

    async def confirm_skills(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        extraction_id: UUID,
        payload: ConfirmSkillsRequest,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> list[LearnerSkillOut]:
        record = await self.repo.get_extraction(extraction_id, organization_id)
        if not record or record.user_id != user_id:
            raise NotFoundError("Extraction record not found")

        confirmed = payload.payload
        record.edited_payload = confirmed.model_dump()
        record.confirmed_payload = confirmed.model_dump()
        record.status = "confirmed"
        record.confirmed_at = datetime.now(UTC)

        profile = await self.repo.get_by_user(user_id, organization_id)
        if not profile:
            raise NotFoundError("Learner profile not found")

        profile.summary = confirmed.summary or profile.summary
        if confirmed.years_of_experience is not None:
            profile.years_of_experience = int(confirmed.years_of_experience)
        profile.existing_certifications = [
            c.model_dump() for c in confirmed.certifications
        ]
        profile.project_experience = [p.model_dump() for p in confirmed.project_experience]
        profile.technical_experience = {
            "items": [t.model_dump() for t in confirmed.technical_experience]
        }
        profile.domain_experience = {"domains": confirmed.domain_experience}
        if confirmed.suggested_target_roles and not profile.target_fde_role:
            profile.target_fde_role = confirmed.suggested_target_roles[0]
        if confirmed.suggested_domains:
            profile.domain_preferences = confirmed.suggested_domains
        profile.skills_confirmed_at = datetime.now(UTC)
        profile.onboarding_status = "skills_confirmed"

        # Map extracted skills onto taxonomy; create custom skills when unmatched
        mapped = 0
        for extracted in confirmed.skills:
            skill = await self._resolve_or_create_skill(
                name=extracted.name,
                category=extracted.category,
                organization_id=organization_id,
            )
            entity = LearnerSkill(
                user_id=user_id,
                organization_id=organization_id,
                skill_id=skill.id,
                proficiency_level=extracted.proficiency_level or "foundational",
                confidence=extracted.confidence,
                source="resume_ai_confirmed",
                confirmed=True,
                notes=extracted.evidence,
                last_assessed_at=datetime.now(UTC),
            )
            await self.skills.upsert_learner_skill(entity)
            mapped += 1

        if mapped == 0 and confirmed.skills:
            raise ValidationAppError(
                "Could not persist any confirmed skills. Re-check the skill list and try again."
            )

        await self.session.flush()
        await self.audit.log(
            action="learner.skills_confirm",
            entity_type="ai_extraction_record",
            entity_id=record.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "skills_count": len(confirmed.skills),
                "mapped_count": mapped,
                "status": "confirmed",
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info(
            "skills_confirmed",
            user_id=str(user_id),
            extracted=len(confirmed.skills),
            mapped=mapped,
        )
        return await self.list_learner_skills(user_id, organization_id)

    async def _resolve_skill(self, name: str, category: str | None) -> Skill | None:
        aliases = {
            "python": "python_programming",
            "py": "python_programming",
            "aws": "cloud_aws",
            "amazon web services": "cloud_aws",
            "cloud": "cloud_aws",
            "postgres": "postgresql",
            "postgresql": "postgresql",
            "react.js": "react",
            "reactjs": "react",
            "node": "typescript",
            "nodejs": "typescript",
            "node.js": "typescript",
            "llm": "generative_ai",
            "genai": "generative_ai",
            "gen ai": "generative_ai",
            "rag": "rag_engineering",
            "fastapi": "fastapi",
            "rest": "rest_apis",
            "rest api": "rest_apis",
            "rest apis": "rest_apis",
            "ml": "machine_learning",
            "devops": "devops",
            "docker": "devops",
            "kubernetes": "devops",
            "k8s": "devops",
            "prompt": "prompt_engineering",
            "hipaa": "hipaa",
            "fhir": "fhir",
        }
        cleaned = (name or "").strip()
        if not cleaned:
            return None

        found = await self.skills.get_skill_by_name_ci(cleaned)
        if found:
            return found

        code = cleaned.lower().replace(" ", "_").replace("/", "_").replace("-", "_")[:120]
        found = await self.skills.get_skill_by_code(code)
        if found:
            return found

        alias = aliases.get(cleaned.lower())
        if alias:
            found = await self.skills.get_skill_by_code(alias)
            if found:
                return found

        # Try category as weak hint via domain/category filter — fall through
        _ = category
        return None

    async def _resolve_or_create_skill(
        self,
        *,
        name: str,
        category: str | None,
        organization_id: UUID,
    ) -> Skill:
        found = await self._resolve_skill(name, category)
        if found:
            return found

        pillar_code = "ai_genai"
        cat = (category or "").lower()
        if any(k in cat for k in ("health", "clinical", "fhir", "hipaa")):
            pillar_code = "healthcare"
        elif any(k in cat for k in ("life", "pharma", "clinical")):
            pillar_code = "life_sciences"
        elif any(k in cat for k in ("data", "etl", "warehouse")):
            pillar_code = "data_knowledge"
        elif any(k in cat for k in ("security", "compliance", "rai")):
            pillar_code = "security_rai"
        elif any(k in cat for k in ("consult", "stakeholder")):
            pillar_code = "consulting"
        elif any(k in cat for k in ("comm", "leader", "present")):
            pillar_code = "communication"
        elif any(k in cat for k in ("soft", "enterprise", "backend", "frontend", "swe")):
            pillar_code = "enterprise_swe"

        pillar = await self.skills.get_pillar_by_code(pillar_code)
        if not pillar:
            pillar = await self.skills.get_first_pillar()
        if not pillar:
            raise ValidationAppError("Skill taxonomy is not seeded; cannot confirm skills")

        slug = (
            name.strip()
            .lower()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("-", "_")
        )
        slug = "".join(ch for ch in slug if ch.isalnum() or ch == "_")[:80] or "skill"
        code = f"custom_{slug}"[:120]
        # Avoid unique collisions on re-confirm
        existing_code = await self.skills.get_skill_by_code(code)
        if existing_code:
            return existing_code

        skill = Skill(
            code=code,
            name=name.strip()[:255],
            description=f"Created from resume confirmation ({name.strip()})",
            pillar_id=pillar.id,
            category=(category or "general")[:100],
            domain="general",
            difficulty="foundational",
            organization_id=organization_id,
            is_active=True,
        )
        return await self.skills.create_skill(skill)

    async def list_learner_skills(
        self, user_id: UUID, organization_id: UUID
    ) -> list[LearnerSkillOut]:
        rows = await self.skills.list_learner_skills(user_id, organization_id)
        return [
            LearnerSkillOut(
                id=row.id,
                skill_id=row.skill_id,
                skill_name=row.skill.name,
                skill_code=row.skill.code,
                pillar_name=row.skill.pillar.name if row.skill.pillar else None,
                proficiency_level=row.proficiency_level,
                score=row.score,
                confidence=row.confidence,
                source=row.source,
                confirmed=row.confirmed,
                notes=row.notes,
            )
            for row in rows
        ]

    def _resume_out(self, resume: ResumeDocument) -> ResumeDocumentOut:
        return ResumeDocumentOut(
            id=resume.id,
            original_filename=resume.original_filename,
            content_type=resume.content_type,
            file_extension=resume.file_extension,
            file_size_bytes=resume.file_size_bytes,
            extraction_status=resume.extraction_status,
            is_latest=resume.is_latest,
            created_at=resume.created_at,
            has_extracted_text=bool(resume.extracted_text),
        )

    def _extraction_out(self, record: AIExtractionRecord) -> AIExtractionOut:
        return AIExtractionOut(
            id=record.id,
            resume_document_id=record.resume_document_id,
            provider=record.provider,
            model=record.model,
            prompt_version=record.prompt_version,
            status=record.status,
            validated_payload=(
                ResumeExtractionPayload.model_validate(record.validated_payload)
                if record.validated_payload
                else None
            ),
            edited_payload=(
                ResumeExtractionPayload.model_validate(record.edited_payload)
                if record.edited_payload
                else None
            ),
            confirmed_payload=(
                ResumeExtractionPayload.model_validate(record.confirmed_payload)
                if record.confirmed_payload
                else None
            ),
            input_tokens=record.input_tokens,
            output_tokens=record.output_tokens,
            estimated_cost_usd=record.estimated_cost_usd,
            error_message=record.error_message,
            hallucination_risk_score=record.hallucination_risk_score,
            confirmed_at=record.confirmed_at,
        )
