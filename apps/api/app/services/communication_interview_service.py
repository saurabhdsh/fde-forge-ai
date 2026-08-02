"""Tavus live interview start/end + OpenAI rubric grading."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway, sanitize_for_prompt
from app.ai.prompts.communication_interview import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_conversational_context,
    build_grade_prompt,
)
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.integrations.tavus_client import TavusClient
from app.models.communication_interview import CommunicationInterview
from app.repositories.communication_interview import CommunicationInterviewRepository
from app.repositories.identity import UserRepository
from app.repositories.learner import LearnerRepository
from app.repositories.skills import SkillsRepository
from app.schemas.communication_interview import (
    CommunicationInterviewOut,
    GradedInterviewPayload,
    TranscriptTurn,
)
from app.services.audit_service import AuditService
from app.services.course_service import CourseService

logger = get_logger(__name__)


class CommunicationInterviewService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CommunicationInterviewRepository(session)
        self.learners = LearnerRepository(session)
        self.skills = SkillsRepository(session)
        self.users = UserRepository(session)
        self.audit = AuditService(session)
        self.ai = AIGateway()
        self.tavus = TavusClient()
        self.settings = get_settings()

    async def start(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
        test_mode: bool | None = None,
    ) -> CommunicationInterviewOut:
        if not self.settings.tavus_configured:
            raise ConfigurationError(
                "TAVUS_API_KEY is not configured. Set TAVUS_API_KEY to enable live interviews."
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        if not profile or not profile.skills_confirmed_at:
            raise ValidationAppError(
                "Confirm your skills before starting the communication interview"
            )

        course_service = CourseService(self.session)
        if not await course_service.is_assessment_unlocked(user_id, organization_id):
            raise ValidationAppError(
                "Complete all required domain courses before starting the communication interview"
            )

        latest = await self.repo.latest_for_user(user_id, organization_id)
        if latest and latest.status in {"live", "ended", "scoring"}:
            raise ConflictError("A communication interview is already in progress")

        domains = list(profile.domain_preferences or []) or ["technical"]
        learner_skills = await self.skills.list_learner_skills(user_id, organization_id)
        skill_names = [
            ls.skill.name for ls in learner_skills if ls.confirmed and ls.skill
        ][:24]

        user = await self.users.get_by_id(user_id)
        candidate_name = None
        if user:
            candidate_name = " ".join(
                p for p in [user.first_name, user.last_name] if p
            ).strip() or user.username

        use_test = (
            bool(test_mode)
            if test_mode is not None
            else bool(self.settings.tavus_test_mode)
        )
        # test_mode only allowed outside production unless explicitly configured
        if use_test and self.settings.app_env == "production" and test_mode is True:
            use_test = False

        context = sanitize_for_prompt(
            build_conversational_context(
                domains=[str(d) for d in domains],
                target_role=profile.target_fde_role,
                skills=skill_names,
                candidate_name=candidate_name,
            ),
            max_chars=8000,
        )

        callback_url = None
        base = (self.settings.tavus_callback_base_url or "").rstrip("/")
        if base:
            secret = (self.settings.tavus_webhook_secret or "").strip()
            callback_url = f"{base}/api/v1/communication-interviews/webhooks/tavus"
            if secret:
                callback_url = f"{callback_url}?secret={secret}"

        interview = CommunicationInterview(
            user_id=user_id,
            organization_id=organization_id,
            status="live",
            prompt_version=PROMPT_VERSION,
            provider="tavus",
            domains=domains,
            started_at=datetime.now(UTC),
            test_mode=use_test,
        )
        await self.repo.create(interview)

        try:
            payload = await self.tavus.create_conversation(
                conversation_name=f"FDE interview {str(interview.id)[:8]}",
                conversational_context=context,
                callback_url=callback_url,
                test_mode=use_test,
            )
            conversation_id = str(payload.get("conversation_id") or "")
            conversation_url = payload.get("conversation_url")
            if not conversation_id:
                raise ValidationAppError("Tavus did not return a conversation_id")
            interview.tavus_conversation_id = conversation_id
            interview.conversation_url = conversation_url
            if use_test or payload.get("status") == "ended":
                interview.status = "ended"
                interview.ended_at = datetime.now(UTC)
            await self.session.flush()
        except Exception as exc:
            interview.status = "failed"
            interview.error_message = str(exc)[:2000]
            await self.session.flush()
            await self.audit.log(
                action="communication_interview.failed",
                entity_type="communication_interview",
                entity_id=interview.id,
                organization_id=organization_id,
                actor_id=actor_id,
                after={"error": interview.error_message},
                correlation_id=correlation_id,
            )
            raise

        await self.audit.log(
            action="communication_interview.started",
            entity_type="communication_interview",
            entity_id=interview.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "conversation_id": interview.tavus_conversation_id,
                "test_mode": use_test,
            },
            correlation_id=correlation_id,
        )

        if interview.status == "ended":
            await self.grade(
                interview_id=interview.id,
                organization_id=organization_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
            )
            refreshed = await self.repo.get_by_id(interview.id, organization_id)
            assert refreshed is not None
            return self._to_out(refreshed)

        return self._to_out(interview)

    async def end(
        self,
        *,
        interview_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> CommunicationInterviewOut:
        interview = await self.repo.get_by_id(interview_id, organization_id)
        if not interview or interview.user_id != user_id:
            raise NotFoundError("Communication interview not found")
        if interview.status == "scored":
            return self._to_out(interview)
        if interview.status == "failed":
            raise ConflictError("Interview failed and cannot be ended")

        if interview.tavus_conversation_id and interview.status == "live":
            await self.tavus.end_conversation(interview.tavus_conversation_id)

        if interview.status == "live":
            interview.status = "ended"
            interview.ended_at = datetime.now(UTC)
            await self.session.flush()
            await self.audit.log(
                action="communication_interview.ended",
                entity_type="communication_interview",
                entity_id=interview.id,
                organization_id=organization_id,
                actor_id=actor_id,
                after={"conversation_id": interview.tavus_conversation_id},
                correlation_id=correlation_id,
            )

        return await self.grade(
            interview_id=interview.id,
            organization_id=organization_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

    async def grade(
        self,
        *,
        interview_id: UUID,
        organization_id: UUID,
        actor_id: UUID | None,
        correlation_id: str | None,
    ) -> CommunicationInterviewOut:
        interview = await self.repo.get_by_id(interview_id, organization_id)
        if not interview:
            raise NotFoundError("Communication interview not found")
        if interview.status == "scored":
            return self._to_out(interview)

        interview.status = "scoring"
        await self.session.flush()

        turns: list[dict] = list(interview.transcript or [])
        if interview.tavus_conversation_id and not interview.test_mode:
            try:
                remote = await self.tavus.get_conversation(
                    interview.tavus_conversation_id, verbose=True
                )
                extracted = TavusClient.extract_transcript(remote)
                if extracted:
                    turns = extracted
                    interview.transcript = turns
            except Exception as exc:
                logger.warning("tavus_transcript_fetch_failed", error=str(exc))
        elif interview.test_mode and not turns:
            turns = [
                {
                    "role": "assistant",
                    "content": "Thanks for joining. Tell me about a recent GenAI delivery.",
                },
                {
                    "role": "user",
                    "content": (
                        "I led a RAG prototype for claims triage, clarified stakeholder ambiguity, "
                        "and communicated HIPAA risk tradeoffs in an exec update."
                    ),
                },
            ]
            interview.transcript = turns

        if not turns and not interview.test_mode:
            # Transcript may arrive via webhook later
            interview.status = "scoring"
            await self.session.flush()
            return self._to_out(interview)

        profile = await self.learners.get_by_user(interview.user_id, organization_id)
        domains = [str(d) for d in (interview.domains or [])]

        if not self.settings.ai_configured:
            interview.status = "scored"
            interview.score_percent = 0.0
            interview.dimension_count = 0
            interview.coach_summary = (
                "Interview ended, but OPENAI_API_KEY is not configured for rubric grading."
            )
            interview.rubric_scores = {}
            interview.scored_at = datetime.now(UTC)
            interview.provider = interview.provider or "tavus"
            await self.session.flush()
            return self._to_out(interview)

        try:
            result = await self.ai.generate_structured(
                prompt=build_grade_prompt(
                    domains=domains,
                    target_role=profile.target_fde_role if profile else None,
                    transcript=turns,
                ),
                schema=GradedInterviewPayload,
                system=SYSTEM_PROMPT,
                temperature=0.2,
                max_output_tokens=4096,
            )
            graded = GradedInterviewPayload.model_validate(result.data)
            interview.score_percent = round(float(graded.score_percent), 1)
            interview.dimension_count = len(graded.dimensions)
            interview.rubric_scores = {
                "dimensions": [d.model_dump() for d in graded.dimensions],
                "strengths": graded.strengths,
                "improvements": graded.improvements,
            }
            interview.coach_summary = graded.coach_summary
            interview.evidence_quotes = list(graded.evidence_quotes or [])[:8]
            interview.model = result.model
            interview.provider = f"tavus+{result.provider}"
            interview.prompt_version = PROMPT_VERSION
            interview.status = "scored"
            interview.scored_at = datetime.now(UTC)
            interview.error_message = None
            await self.session.flush()
            await self.audit.log(
                action="communication_interview.scored",
                entity_type="communication_interview",
                entity_id=interview.id,
                organization_id=organization_id,
                actor_id=actor_id,
                after={"score_percent": interview.score_percent},
                correlation_id=correlation_id,
            )
        except Exception as exc:
            interview.status = "failed"
            interview.error_message = f"Grading failed: {exc}"[:2000]
            await self.session.flush()
            await self.audit.log(
                action="communication_interview.failed",
                entity_type="communication_interview",
                entity_id=interview.id,
                organization_id=organization_id,
                actor_id=actor_id,
                after={"error": interview.error_message},
                correlation_id=correlation_id,
            )
            raise

        return self._to_out(interview)

    async def handle_tavus_webhook(self, payload: dict) -> None:
        conversation_id = str(
            payload.get("conversation_id")
            or payload.get("properties", {}).get("conversation_id")
            or ""
        )
        event_type = str(payload.get("event_type") or payload.get("message_type") or "")
        if not conversation_id:
            return

        interview = await self.repo.get_by_conversation_id(conversation_id)
        if not interview:
            logger.warning("tavus_webhook_unknown_conversation", conversation_id=conversation_id)
            return

        # Capture transcript from webhook body if present
        props = payload.get("properties") or {}
        if event_type == "application.transcription_ready" or props.get("transcript"):
            raw = props.get("transcript") or []
            turns = []
            for item in raw:
                if not isinstance(item, dict):
                    continue
                content = (item.get("content") or "").strip()
                if not content:
                    continue
                turns.append(
                    {
                        "role": (item.get("role") or "user").strip(),
                        "content": content,
                        "timestamp": item.get("timestamp"),
                        "seconds_from_start": item.get("seconds_from_start"),
                    }
                )
            if turns:
                interview.transcript = turns

        if interview.status == "live":
            interview.status = "ended"
            interview.ended_at = datetime.now(UTC)
            await self.session.flush()

        if interview.status in {"ended", "scoring"} and interview.status != "scored":
            await self.grade(
                interview_id=interview.id,
                organization_id=interview.organization_id,
                actor_id=None,
                correlation_id=None,
            )

    async def get(
        self, interview_id: UUID, user_id: UUID, organization_id: UUID
    ) -> CommunicationInterviewOut:
        interview = await self.repo.get_by_id(interview_id, organization_id)
        if not interview or interview.user_id != user_id:
            raise NotFoundError("Communication interview not found")
        if interview.status == "scoring":
            try:
                return await self.grade(
                    interview_id=interview.id,
                    organization_id=organization_id,
                    actor_id=user_id,
                    correlation_id=None,
                )
            except Exception:
                refreshed = await self.repo.get_by_id(interview_id, organization_id)
                assert refreshed is not None
                return self._to_out(refreshed)
        return self._to_out(interview)

    async def get_latest(
        self, user_id: UUID, organization_id: UUID
    ) -> CommunicationInterviewOut | None:
        interview = await self.repo.latest_for_user(user_id, organization_id)
        if not interview:
            return None
        if interview.status == "scoring":
            try:
                return await self.grade(
                    interview_id=interview.id,
                    organization_id=organization_id,
                    actor_id=user_id,
                    correlation_id=None,
                )
            except Exception:
                refreshed = await self.repo.latest_for_user(user_id, organization_id)
                assert refreshed is not None
                return self._to_out(refreshed)
        return self._to_out(interview)

    def export(
        self, *, interview: CommunicationInterview, fmt: str = "markdown"
    ) -> tuple[str | bytes, str, str]:
        fmt = (fmt or "markdown").lower()
        payload = {
            "id": str(interview.id),
            "status": interview.status,
            "score_percent": interview.score_percent,
            "domains": interview.domains,
            "rubric_scores": interview.rubric_scores,
            "coach_summary": interview.coach_summary,
            "evidence_quotes": interview.evidence_quotes,
            "transcript": interview.transcript,
            "started_at": interview.started_at.isoformat() if interview.started_at else None,
            "ended_at": interview.ended_at.isoformat() if interview.ended_at else None,
            "scored_at": interview.scored_at.isoformat() if interview.scored_at else None,
            "test_mode": interview.test_mode,
        }
        if fmt == "json":
            content = json.dumps(payload, indent=2)
            return content, f"communication-interview-{interview.id}.json", "application/json"

        dims = (interview.rubric_scores or {}).get("dimensions") or []
        dim_lines = [
            f"- **{d.get('label', d.get('id'))}**: {d.get('score')}/5 — {d.get('feedback', '')}"
            for d in dims
            if isinstance(d, dict)
        ]
        transcript_lines = [
            f"- **{t.get('role')}**: {t.get('content')}"
            for t in (interview.transcript or [])
            if isinstance(t, dict)
        ]
        evidence = interview.evidence_quotes or []
        md_parts = [
            "# Communication interview export",
            "",
            f"- Status: `{interview.status}`",
            f"- Score: **{interview.score_percent if interview.score_percent is not None else '—'}%**",
            f"- Domains: {', '.join(str(d) for d in (interview.domains or [])) or '—'}",
            "",
            "## Coach summary",
            interview.coach_summary or "—",
            "",
            "## Rubric",
            *(dim_lines or ["—"]),
            "",
            "## Evidence",
            *([f"- {q}" for q in evidence] if evidence else ["—"]),
            "",
            "## Transcript",
            *(transcript_lines or ["—"]),
            "",
        ]
        md = "\n".join(md_parts)
        return md, f"communication-interview-{interview.id}.md", "text/markdown; charset=utf-8"

    def _to_out(self, interview: CommunicationInterview) -> CommunicationInterviewOut:
        transcript = []
        for t in interview.transcript or []:
            if isinstance(t, dict):
                transcript.append(
                    TranscriptTurn(
                        role=str(t.get("role") or "user"),
                        content=str(t.get("content") or ""),
                        timestamp=t.get("timestamp"),
                        seconds_from_start=t.get("seconds_from_start"),
                    )
                )
        return CommunicationInterviewOut(
            id=interview.id,
            status=interview.status,
            domains=list(interview.domains or []),
            conversation_url=interview.conversation_url,
            tavus_conversation_id=interview.tavus_conversation_id,
            provider=interview.provider,
            model=interview.model,
            prompt_version=interview.prompt_version,
            score_percent=interview.score_percent,
            dimension_count=interview.dimension_count,
            transcript=transcript if interview.status in {"scored", "scoring", "ended"} else [],
            rubric_scores=dict(interview.rubric_scores or {}),
            coach_summary=interview.coach_summary,
            evidence_quotes=list(interview.evidence_quotes or []),
            started_at=interview.started_at,
            ended_at=interview.ended_at,
            scored_at=interview.scored_at,
            error_message=interview.error_message,
            test_mode=bool(interview.test_mode),
            created_at=interview.created_at,
        )
