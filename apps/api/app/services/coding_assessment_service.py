"""Coding playground generation, interactive submit, and AI rubric grading."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.prompts.coding_playground import (
    GRADE_SYSTEM_PROMPT,
    MIN_QUESTIONS,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_grade_prompt,
    build_user_prompt,
)
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.models.coding_assessment import CodingAssessment, CodingQuestion, CodingSubmission
from app.repositories.coding_assessment import CodingAssessmentRepository
from app.repositories.learner import LearnerRepository
from app.repositories.skills import SkillsRepository
from app.schemas.coding_assessment import (
    CodingAnswerIn,
    CodingAssessmentOut,
    CodingDraftRequest,
    CodingQuestionOut,
    CodingSubmitRequest,
    GeneratedCodingPayload,
    GradedCodingPayload,
)
from app.services.audit_service import AuditService
from app.services.course_service import CourseService

logger = get_logger(__name__)


class CodingAssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = CodingAssessmentRepository(session)
        self.learners = LearnerRepository(session)
        self.skills = SkillsRepository(session)
        self.audit = AuditService(session)
        self.ai = AIGateway()
        self.settings = get_settings()

    def _add_questions(
        self,
        assessment_id: UUID,
        questions: list,
        *,
        start_order: int,
        existing_titles: set[str],
        limit: int,
    ) -> int:
        order = start_order
        for q in questions:
            if order >= limit:
                break
            title = (q.title or "").strip()
            prompt = (q.prompt_markdown or "").strip()
            starter = (q.starter_code or "").strip()
            if len(title) < 4 or len(prompt) < 40 or len(starter) < 10:
                continue
            if title.lower() in existing_titles:
                continue
            self.session.add(
                CodingQuestion(
                    assessment_id=assessment_id,
                    title=title,
                    prompt_markdown=prompt,
                    language=(q.language or "python").strip().lower() or "python",
                    starter_code=starter,
                    topic_tags=list(q.topic_tags or [])[:8],
                    domain_focus=(q.domain_focus or "technical")[:50],
                    difficulty=(q.difficulty or "hard")[:40],
                    rubric=[str(r).strip() for r in (q.rubric or []) if str(r).strip()][:6],
                    reference_solution=(q.reference_solution or "").strip() or None,
                    sort_order=order,
                )
            )
            existing_titles.add(title.lower())
            order += 1
        return order

    async def create(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> CodingAssessmentOut:
        if not self.settings.ai_configured:
            raise ConfigurationError(
                "No AI provider ready. Set OPENAI_API_KEY or enable Bedrock (BEDROCK_ENABLED=true + AWS creds)."
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        if not profile or not profile.skills_confirmed_at:
            raise ValidationAppError(
                "Confirm your skills before starting the coding assessment"
            )

        course_service = CourseService(self.session)
        if not await course_service.is_assessment_unlocked(user_id, organization_id):
            raise ValidationAppError(
                "Complete all required domain courses before starting the coding assessment"
            )

        latest = await self.repo.latest_for_user(user_id, organization_id)
        if latest and latest.status in {"generating", "ready", "in_progress"}:
            raise ConflictError("A coding assessment is already in progress")

        domains = list(profile.domain_preferences or []) or ["technical"]
        learner_skills = await self.skills.list_learner_skills(user_id, organization_id)
        skill_names = [
            ls.skill.name for ls in learner_skills if ls.confirmed and ls.skill
        ][:24]

        assessment = CodingAssessment(
            user_id=user_id,
            organization_id=organization_id,
            status="generating",
            prompt_version=PROMPT_VERSION,
            domains=domains,
            started_at=datetime.now(UTC),
        )
        await self.repo.create(assessment)

        try:
            result = await self.ai.generate_structured(
                prompt=build_user_prompt(
                    domains=[str(d) for d in domains],
                    target_role=profile.target_fde_role,
                    skills=skill_names,
                    question_count=MIN_QUESTIONS,
                ),
                schema=GeneratedCodingPayload,
                system=SYSTEM_PROMPT,
                temperature=0.35,
                max_output_tokens=12288,
            )
            payload = GeneratedCodingPayload.model_validate(result.data)
            titles: set[str] = set()
            order = self._add_questions(
                assessment.id,
                payload.questions,
                start_order=0,
                existing_titles=titles,
                limit=MIN_QUESTIONS,
            )
            await self.session.flush()

            attempts = 0
            while order < MIN_QUESTIONS and attempts < 2:
                attempts += 1
                need = MIN_QUESTIONS - order
                top_result = await self.ai.generate_structured(
                    prompt=build_user_prompt(
                        domains=[str(d) for d in domains],
                        target_role=profile.target_fde_role,
                        skills=skill_names,
                        question_count=need + 4,
                    )
                    + f"\nAdditional batch {attempts}: NEW questions only.",
                    schema=GeneratedCodingPayload,
                    system=SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=8192,
                )
                result = top_result
                top_payload = GeneratedCodingPayload.model_validate(top_result.data)
                order = self._add_questions(
                    assessment.id,
                    top_payload.questions,
                    start_order=order,
                    existing_titles=titles,
                    limit=MIN_QUESTIONS,
                )
                await self.session.flush()

            refreshed = await self.repo.get_by_id(assessment.id, organization_id)
            assert refreshed is not None
            if len(refreshed.questions) < MIN_QUESTIONS:
                raise ValidationAppError(
                    f"Could not build {MIN_QUESTIONS} coding questions "
                    f"(got {len(refreshed.questions)}). Retry starting the coding assessment."
                )

            assessment.status = "ready"
            assessment.provider = result.provider
            assessment.model = result.model
            assessment.total_count = len(refreshed.questions)
            assessment.error_message = None
        except ConfigurationError:
            assessment.status = "failed"
            assessment.error_message = "OPENAI_API_KEY is not configured"
            await self.session.flush()
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("coding_assessment_generation_failed", error=str(exc))
            assessment.status = "failed"
            assessment.error_message = str(exc)
            await self.session.flush()
            raise

        await self.session.flush()
        await self.audit.log(
            action="coding_assessment.generated",
            entity_type="coding_assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"question_count": assessment.total_count, "domains": domains},
            correlation_id=correlation_id,
        )
        out = await self.repo.get_by_id(assessment.id, organization_id)
        assert out is not None
        return self._to_out(out)

    async def get_latest(
        self, user_id: UUID, organization_id: UUID
    ) -> CodingAssessmentOut | None:
        assessment = await self.repo.latest_for_user(user_id, organization_id)
        if not assessment:
            return None
        return self._to_out(assessment)

    async def get(
        self, assessment_id: UUID, user_id: UUID, organization_id: UUID
    ) -> CodingAssessmentOut:
        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Coding assessment not found")
        if assessment.status == "ready":
            assessment.status = "in_progress"
            await self.session.flush()
        return self._to_out(assessment)

    async def submit(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        payload: CodingSubmitRequest,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> CodingAssessmentOut:
        if not self.settings.ai_configured:
            raise ConfigurationError(
                "No AI provider ready. Set OPENAI_API_KEY or enable Bedrock (BEDROCK_ENABLED=true + AWS creds)."
            )

        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Coding assessment not found")
        if assessment.status not in {"ready", "in_progress"}:
            raise ConflictError("Coding assessment cannot be submitted in its current state")

        by_id = {q.id: q for q in assessment.questions}
        if len(payload.answers) != len(by_id):
            raise ValidationAppError("Submit code for every coding question")

        seen: set[UUID] = set()
        items_for_grade: list[dict] = []
        pending: list[tuple[CodingQuestion, str]] = []

        for ans in payload.answers:
            if ans.question_id in seen:
                raise ValidationAppError("Duplicate answer for a question")
            seen.add(ans.question_id)
            question = by_id.get(ans.question_id)
            if not question:
                raise ValidationAppError("Unknown question in submission")
            code = (ans.code or "").strip()
            if len(code) < 8:
                raise ValidationAppError(f"Code too short for question: {question.title}")
            pending.append((question, code))
            items_for_grade.append(
                {
                    "question_id": str(question.id),
                    "title": question.title,
                    "prompt": question.prompt_markdown,
                    "rubric": question.rubric or [],
                    "reference_solution": question.reference_solution,
                    "code": code,
                }
            )

        grade_map: dict[str, object] = {}
        chunk_size = 5
        for i in range(0, len(items_for_grade), chunk_size):
            chunk = items_for_grade[i : i + chunk_size]
            try:
                grade_result = await self.ai.generate_structured(
                    prompt=build_grade_prompt(items=chunk),
                    schema=GradedCodingPayload,
                    system=GRADE_SYSTEM_PROMPT,
                    temperature=0.1,
                    max_output_tokens=4096,
                )
                graded = GradedCodingPayload.model_validate(grade_result.data)
                for r in graded.results:
                    grade_map[str(r.question_id)] = r
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "coding_grade_chunk_failed",
                    error=str(exc),
                    chunk_start=i,
                    chunk_size=len(chunk),
                )
                # Continue grading remaining chunks; unscored items use heuristic fallback

        passed = 0
        for question, code in pending:
            graded = grade_map.get(str(question.id))
            if graded is None:
                score = 40.0 if code != (question.starter_code or "").strip() else 10.0
                is_pass = False
                feedback = "Automated grader did not return a score for this item."
                rubric_scores: dict = {}
            else:
                score = float(max(0, min(100, graded.score)))  # type: ignore[attr-defined]
                is_pass = bool(graded.passed) or score >= 70  # type: ignore[attr-defined]
                feedback = graded.feedback  # type: ignore[attr-defined]
                rubric_scores = dict(graded.rubric_scores or {})  # type: ignore[attr-defined]
            if is_pass:
                passed += 1
            self.session.add(
                CodingSubmission(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    code=code,
                    score=score,
                    passed=is_pass,
                    feedback=feedback,
                    rubric_scores=rubric_scores,
                )
            )

        total = len(by_id)
        assessment.passed_count = passed
        assessment.total_count = total
        assessment.score_percent = round((passed / total) * 100, 1) if total else 0.0
        assessment.submitted_at = datetime.now(UTC)
        assessment.status = "scored"
        await self.session.flush()

        await self.audit.log(
            action="coding_assessment.submitted",
            entity_type="coding_assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "passed_count": passed,
                "total_count": total,
                "score_percent": assessment.score_percent,
            },
            correlation_id=correlation_id,
        )
        refreshed = await self.repo.get_by_id(assessment.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def save_draft(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        payload: CodingDraftRequest,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> CodingAssessmentOut:
        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Coding assessment not found")
        if assessment.status not in {"ready", "in_progress"}:
            raise ConflictError("Drafts can only be saved for an in-progress coding assessment")

        by_id = {q.id for q in assessment.questions}
        clean: list[dict] = []
        for ans in payload.answers:
            if ans.question_id not in by_id:
                continue
            code = (ans.code or "").rstrip()
            clean.append({"question_id": str(ans.question_id), "code": code})
        assessment.draft_payload = {"answers": clean}
        if assessment.status == "ready":
            assessment.status = "in_progress"
        await self.session.flush()
        await self.audit.log(
            action="coding_assessment.draft_saved",
            entity_type="coding_assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"answer_count": len(clean)},
            correlation_id=correlation_id,
        )
        return self._to_out(assessment)

    def export(
        self,
        *,
        assessment: CodingAssessment,
        fmt: str = "markdown",
    ) -> tuple[str, str, str]:
        fmt = (fmt or "markdown").lower().strip()
        stamp = (assessment.submitted_at or assessment.created_at).strftime("%Y%m%d")
        base = f"coding-assessment-{stamp}"
        draft = (assessment.draft_payload or {}).get("answers") or []
        draft_by_q = {
            str(a.get("question_id")): a.get("code", "")
            for a in draft
            if isinstance(a, dict)
        }

        if fmt == "json":
            import json

            payload = {
                "id": str(assessment.id),
                "status": assessment.status,
                "score_percent": assessment.score_percent,
                "passed_count": assessment.passed_count,
                "total_count": assessment.total_count,
                "domains": list(assessment.domains or []),
                "submitted_at": assessment.submitted_at.isoformat()
                if assessment.submitted_at
                else None,
                "questions": [
                    {
                        "id": str(q.id),
                        "title": q.title,
                        "prompt": q.prompt_markdown,
                        "language": q.language,
                        "starter_code": q.starter_code,
                        "code": (
                            q.submission.code
                            if q.submission and assessment.status == "scored"
                            else draft_by_q.get(str(q.id), q.starter_code)
                        ),
                        "score": q.submission.score
                        if q.submission and assessment.status == "scored"
                        else None,
                        "passed": q.submission.passed
                        if q.submission and assessment.status == "scored"
                        else None,
                        "feedback": q.submission.feedback
                        if q.submission and assessment.status == "scored"
                        else None,
                    }
                    for q in assessment.questions
                ],
            }
            return json.dumps(payload, indent=2), f"{base}.json", "application/json"

        lines = [
            "# Coding assessment export",
            f"- Status: {assessment.status}",
            f"- Passed: {assessment.passed_count}/{assessment.total_count}",
            f"- Score: {assessment.score_percent if assessment.score_percent is not None else '—'}%",
            "",
        ]
        for i, q in enumerate(assessment.questions, start=1):
            code = (
                q.submission.code
                if q.submission and assessment.status == "scored"
                else draft_by_q.get(str(q.id), q.starter_code)
            )
            lines.append(f"## Q{i}. {q.title}")
            lines.append(q.prompt_markdown)
            lines.append("")
            lines.append("```" + (q.language or "python"))
            lines.append(code or "")
            lines.append("```")
            if assessment.status == "scored" and q.submission:
                lines.append(
                    f"- Result: {'Passed' if q.submission.passed else 'Needs work'} "
                    f"({q.submission.score})"
                )
                if q.submission.feedback:
                    lines.append(f"- Feedback: {q.submission.feedback}")
            lines.append("")
        return "\n".join(lines), f"{base}.md", "text/markdown; charset=utf-8"

    def _to_out(self, assessment: CodingAssessment) -> CodingAssessmentOut:
        reveal = assessment.status == "scored"
        draft_raw = (assessment.draft_payload or {}).get("answers") or []
        draft_answers: list[CodingAnswerIn] = []
        draft_by_q: dict[str, str] = {}
        for item in draft_raw:
            if not isinstance(item, dict):
                continue
            try:
                qid = UUID(str(item.get("question_id")))
            except (TypeError, ValueError):
                continue
            code = str(item.get("code") or "")
            draft_by_q[str(qid)] = code
            draft_answers.append(CodingAnswerIn(question_id=qid, code=code))

        questions: list[CodingQuestionOut] = []
        for q in assessment.questions:
            sub = q.submission
            questions.append(
                CodingQuestionOut(
                    id=q.id,
                    title=q.title,
                    prompt_markdown=q.prompt_markdown,
                    language=q.language,
                    starter_code=q.starter_code,
                    topic_tags=list(q.topic_tags or []),
                    domain_focus=q.domain_focus,
                    difficulty=q.difficulty,
                    sort_order=q.sort_order,
                    submitted_code=(
                        sub.code
                        if sub and reveal
                        else (draft_by_q.get(str(q.id)) if not reveal else None)
                    ),
                    score=sub.score if sub and reveal else None,
                    passed=sub.passed if sub and reveal else None,
                    feedback=sub.feedback if sub and reveal else None,
                )
            )
        return CodingAssessmentOut(
            id=assessment.id,
            status=assessment.status,
            domains=list(assessment.domains or []),
            provider=assessment.provider,
            model=assessment.model,
            prompt_version=assessment.prompt_version,
            score_percent=assessment.score_percent,
            passed_count=assessment.passed_count,
            total_count=assessment.total_count,
            started_at=assessment.started_at,
            submitted_at=assessment.submitted_at,
            error_message=assessment.error_message,
            created_at=assessment.created_at,
            questions=questions,
            draft_answers=draft_answers if not reveal else [],
        )
