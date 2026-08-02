"""Baseline assessment generation, scoring, and skill updates."""

from __future__ import annotations

import random
from collections import defaultdict
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.prompts.baseline_assessment import (
    MIN_QUESTIONS,
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    build_user_prompt,
    is_low_quality_question,
)
from app.core.config import get_settings
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    NotFoundError,
    ValidationAppError,
)
from app.core.logging import get_logger
from app.models.assessment import Assessment, AssessmentAnswer, AssessmentQuestion
from app.models.skills import LearnerSkill, Skill, SkillEvidence
from app.repositories.assessment import AssessmentRepository
from app.repositories.learner import LearnerRepository
from app.repositories.skills import SkillsRepository
from app.schemas.assessment import (
    AssessmentDraftRequest,
    AssessmentOut,
    AssessmentQuestionOut,
    AssessmentSubmitRequest,
    GeneratedAssessmentPayload,
    GeneratedQuestion,
)
from app.services.audit_service import AuditService
from app.services.learning_plan_service import LearningPlanService
logger = get_logger(__name__)


def proficiency_from_accuracy(accuracy: float) -> str:
    if accuracy >= 1.0:
        return "proficient"
    if accuracy >= 0.6:
        return "working"
    return "awareness"


def resolve_skill_ref(
    ref: str,
    *,
    by_code: dict[str, Skill],
    by_code_lower: dict[str, Skill],
    by_name_lower: dict[str, Skill],
) -> Skill | None:
    """Map AI skill_code/name loosely onto taxonomy skills."""
    raw = (ref or "").strip()
    if not raw:
        return None
    if raw in by_code:
        return by_code[raw]
    key = raw.lower().replace(" ", "_").replace("-", "_")
    if key in by_code_lower:
        return by_code_lower[key]
    if raw.lower() in by_name_lower:
        return by_name_lower[raw.lower()]
    # Fuzzy: code contained / name contained
    for code, skill in by_code_lower.items():
        if code in key or key in code:
            return skill
    for name, skill in by_name_lower.items():
        if name in raw.lower() or raw.lower() in name:
            return skill
    return None


class AssessmentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AssessmentRepository(session)
        self.learners = LearnerRepository(session)
        self.skills = SkillsRepository(session)
        self.audit = AuditService(session)
        self.ai = AIGateway()
        self.settings = get_settings()
        self.plans = LearningPlanService(session)

    async def create_baseline(
        self,
        *,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AssessmentOut:
        if not self.settings.ai_configured:
            raise ConfigurationError(
                "No AI provider ready. Set OPENAI_API_KEY or enable Bedrock (BEDROCK_ENABLED=true + AWS creds)."
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        if not profile or not profile.skills_confirmed_at:
            raise ValidationAppError(
                "Confirm your skills before starting a baseline assessment"
            )

        from app.services.course_service import CourseService

        course_service = CourseService(self.session)
        if not await course_service.is_assessment_unlocked(user_id, organization_id):
            raise ValidationAppError(
                "Complete all required domain courses before starting the assessment"
            )

        learner_skills = await self.skills.list_learner_skills(user_id, organization_id)
        confirmed = [ls for ls in learner_skills if ls.confirmed]
        if not confirmed:
            raise ValidationAppError("No confirmed skills available for assessment")

        latest = await self.repo.latest_for_user(user_id, organization_id)
        if latest and latest.status in {"generating", "ready", "in_progress"}:
            raise ConflictError("An assessment is already in progress")

        assessment = Assessment(
            user_id=user_id,
            organization_id=organization_id,
            kind="baseline",
            status="generating",
            prompt_version=PROMPT_VERSION,
            started_at=datetime.now(UTC),
        )
        await self.repo.create(assessment)

        skill_payload = [
            {
                "code": ls.skill.code,
                "name": ls.skill.name,
                "pillar": ls.skill.pillar.name if ls.skill.pillar else None,
                "category": ls.skill.category,
                "domain": ls.skill.domain,
                "description": (ls.skill.description or "")[:240] or None,
            }
            for ls in confirmed
            if ls.skill
        ]
        skill_payload = skill_payload[:24]
        question_count = MIN_QUESTIONS

        allowed_codes = [s["code"] for s in skill_payload]
        by_code = await self.repo.get_skill_map(allowed_codes)
        by_code_lower = {c.lower(): sk for c, sk in by_code.items()}
        by_name_lower = {sk.name.lower(): sk for sk in by_code.values()}

        try:
            order = 0
            skipped_unmapped = 0
            skipped_quality = 0
            used_stems: set[str] = set()
            result = None

            def try_add(q: GeneratedQuestion, *, strict: bool) -> bool:
                nonlocal order, skipped_unmapped, skipped_quality
                if order >= question_count:
                    return False
                skill = resolve_skill_ref(
                    q.skill_code,
                    by_code=by_code,
                    by_code_lower=by_code_lower,
                    by_name_lower=by_name_lower,
                )
                if not skill:
                    skipped_unmapped += 1
                    logger.warning(
                        "assessment_skill_unmapped",
                        skill_code=q.skill_code,
                        allowed=allowed_codes,
                    )
                    return False
                choices = [str(c).strip() for c in q.choices]
                if len(choices) != 4 or q.correct_index < 0 or q.correct_index > 3:
                    skipped_quality += 1
                    return False
                stem = q.stem.strip()
                if stem.lower() in used_stems:
                    return False
                if strict and is_low_quality_question(stem, choices):
                    skipped_quality += 1
                    logger.warning(
                        "assessment_question_filtered",
                        skill_code=q.skill_code,
                        stem=stem[:120],
                    )
                    return False
                if not strict:
                    if len(set(c.lower() for c in choices)) < 4 or len(stem) < 24:
                        skipped_quality += 1
                        return False
                indexed = list(enumerate(choices))
                random.shuffle(indexed)
                new_choices = [c for _, c in indexed]
                new_correct = next(
                    i for i, (orig_i, _) in enumerate(indexed) if orig_i == q.correct_index
                )
                self.session.add(
                    AssessmentQuestion(
                        assessment_id=assessment.id,
                        skill_id=skill.id,
                        stem=stem,
                        choices=new_choices,
                        correct_index=new_correct,
                        explanation=(q.explanation or "").strip() or None,
                        sort_order=order,
                    )
                )
                used_stems.add(stem.lower())
                order += 1
                return True

            async def generate_batch(
                *,
                count: int,
                extra_instruction: str | None = None,
            ):
                ai_result = await self.ai.generate_structured(
                    prompt=build_user_prompt(
                        skills=skill_payload,
                        target_role=profile.target_fde_role,
                        domains=list(profile.domain_preferences or []),
                        question_count=count,
                        extra_instruction=extra_instruction,
                    ),
                    schema=GeneratedAssessmentPayload,
                    system=SYSTEM_PROMPT,
                    temperature=0.35,
                    max_output_tokens=12288,
                )
                return GeneratedAssessmentPayload.model_validate(ai_result.data), ai_result

            payload, result = await generate_batch(count=question_count)
            for q in payload.questions:
                try_add(q, strict=True)

            attempts = 0
            while order < question_count and attempts < 2:
                attempts += 1
                need = question_count - order
                top_up, result = await generate_batch(
                    count=need + 4,
                    extra_instruction=(
                        f"Additional batch: generate {need + 4} NEW very hard questions "
                        "that do NOT duplicate these stems:\n- "
                        + "\n- ".join(sorted(used_stems)[:40])
                    ),
                )
                for q in top_up.questions:
                    try_add(q, strict=True)
                if order < question_count:
                    for q in top_up.questions:
                        try_add(q, strict=False)

            await self.session.flush()

            if order < question_count or result is None:
                raise ValidationAppError(
                    f"Could not build the required {question_count} hard assessment questions. "
                    f"Kept {order} after filtering "
                    f"({skipped_unmapped} unmapped skill codes, {skipped_quality} filtered). "
                    "Retry starting the assessment."
                )
            assessment.status = "ready"
            assessment.provider = result.provider
            assessment.model = result.model
            assessment.total_count = order
            assessment.error_message = None
            logger.info(
                "assessment_generated",
                questions=order,
                skipped_unmapped=skipped_unmapped,
                skipped_quality=skipped_quality,
                prompt_version=PROMPT_VERSION,
            )
        except ConfigurationError:
            assessment.status = "failed"
            assessment.error_message = "OPENAI_API_KEY is not configured"
            await self.session.flush()
            raise
        except Exception as exc:  # noqa: BLE001
            logger.error("assessment_generation_failed", error=str(exc))
            assessment.status = "failed"
            assessment.error_message = str(exc)
            await self.session.flush()
            raise
        await self.session.flush()
        await self.audit.log(
            action="assessment.generated",
            entity_type="assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"kind": "baseline", "question_count": assessment.total_count},
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        refreshed = await self.repo.get_by_id(assessment.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed, reveal_answers=False)

    async def get_latest(self, user_id: UUID, organization_id: UUID) -> AssessmentOut | None:
        assessment = await self.repo.latest_for_user(user_id, organization_id)
        if not assessment:
            return None
        reveal = assessment.status == "scored"
        return self._to_out(assessment, reveal_answers=reveal)

    async def get(
        self, assessment_id: UUID, user_id: UUID, organization_id: UUID
    ) -> AssessmentOut:
        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Assessment not found")
        if assessment.status == "ready":
            assessment.status = "in_progress"
            await self.session.flush()
        reveal = assessment.status == "scored"
        return self._to_out(assessment, reveal_answers=reveal)

    async def submit(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        payload: AssessmentSubmitRequest,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AssessmentOut:
        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Assessment not found")
        if assessment.status not in {"ready", "in_progress"}:
            raise ConflictError("Assessment cannot be submitted in its current state")

        by_id = {q.id: q for q in assessment.questions}
        if len(payload.answers) != len(by_id):
            raise ValidationAppError("Submit an answer for every question")

        seen: set[UUID] = set()
        correct = 0
        per_skill: dict[UUID, list[bool]] = defaultdict(list)

        for ans in payload.answers:
            if ans.question_id in seen:
                raise ValidationAppError("Duplicate answer for a question")
            seen.add(ans.question_id)
            question = by_id.get(ans.question_id)
            if not question:
                raise ValidationAppError("Unknown question in submission")
            is_correct = ans.selected_index == question.correct_index
            if is_correct:
                correct += 1
            per_skill[question.skill_id].append(is_correct)
            await self.repo.add_answer(
                AssessmentAnswer(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    selected_index=ans.selected_index,
                    is_correct=is_correct,
                )
            )

        total = len(by_id)
        assessment.correct_count = correct
        assessment.total_count = total
        assessment.score_percent = round((correct / total) * 100, 1) if total else 0.0
        assessment.submitted_at = datetime.now(UTC)
        assessment.status = "scored"

        for skill_id, results in per_skill.items():
            accuracy = sum(1 for r in results if r) / len(results)
            level = proficiency_from_accuracy(accuracy)
            entity = LearnerSkill(
                user_id=user_id,
                organization_id=organization_id,
                skill_id=skill_id,
                proficiency_level=level,
                score=round(accuracy * 100, 1),
                confidence=round(accuracy, 2),
                source="assessment",
                confirmed=True,
                notes=f"Baseline assessment {assessment.id}",
                last_assessed_at=datetime.now(UTC),
            )
            saved = await self.skills.upsert_learner_skill(entity)
            self.session.add(
                SkillEvidence(
                    learner_skill_id=saved.id,
                    organization_id=organization_id,
                    evidence_type="assessment_result",
                    source_entity_type="assessment",
                    source_entity_id=str(assessment.id),
                    summary=f"Accuracy {accuracy:.0%} → {level}",
                    metadata_={"accuracy": accuracy, "attempts": len(results)},
                )
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        if profile:
            profile.onboarding_status = "assessment_completed"

        await self.session.flush()
        await self.audit.log(
            action="assessment.submitted",
            entity_type="assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "score_percent": assessment.score_percent,
                "correct_count": correct,
                "total_count": total,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Generate learning plan from gaps (best-effort if AI fails — assessment still scored)
        try:
            await self.plans.generate_from_assessment(
                assessment=assessment,
                user_id=user_id,
                organization_id=organization_id,
                actor_id=actor_id,
                correlation_id=correlation_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("learning_plan_generation_failed", error=str(exc))

        refreshed = await self.repo.get_by_id(assessment.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed, reveal_answers=True)

    async def save_draft(
        self,
        *,
        assessment_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        payload: AssessmentDraftRequest,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> AssessmentOut:
        assessment = await self.repo.get_by_id(assessment_id, organization_id)
        if not assessment or assessment.user_id != user_id:
            raise NotFoundError("Assessment not found")
        if assessment.status not in {"ready", "in_progress"}:
            raise ConflictError("Drafts can only be saved for an in-progress assessment")

        by_id = {q.id for q in assessment.questions}
        clean: list[dict] = []
        for ans in payload.answers:
            if ans.question_id not in by_id:
                continue
            if ans.selected_index < 0 or ans.selected_index > 3:
                continue
            clean.append(
                {
                    "question_id": str(ans.question_id),
                    "selected_index": ans.selected_index,
                }
            )
        assessment.draft_payload = {"answers": clean}
        if assessment.status == "ready":
            assessment.status = "in_progress"
        await self.session.flush()
        await self.audit.log(
            action="assessment.draft_saved",
            entity_type="assessment",
            entity_id=assessment.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"answer_count": len(clean)},
            correlation_id=correlation_id,
        )
        return self._to_out(assessment, reveal_answers=False)

    def export(
        self,
        *,
        assessment: Assessment,
        fmt: str = "markdown",
    ) -> tuple[str, str, str]:
        """Return (content, filename, media_type)."""
        fmt = (fmt or "markdown").lower().strip()
        stamp = (assessment.submitted_at or assessment.created_at).strftime("%Y%m%d")
        base = f"baseline-assessment-{stamp}"
        answers_by_q = {a.question_id: a for a in assessment.answers}
        draft = (assessment.draft_payload or {}).get("answers") or []
        draft_by_q = {str(a.get("question_id")): a for a in draft if isinstance(a, dict)}

        if fmt == "json":
            payload = {
                "id": str(assessment.id),
                "kind": assessment.kind,
                "status": assessment.status,
                "score_percent": assessment.score_percent,
                "correct_count": assessment.correct_count,
                "total_count": assessment.total_count,
                "submitted_at": assessment.submitted_at.isoformat()
                if assessment.submitted_at
                else None,
                "questions": [
                    {
                        "id": str(q.id),
                        "skill": q.skill.name if q.skill else None,
                        "stem": q.stem,
                        "choices": list(q.choices or []),
                        "selected_index": (
                            answers_by_q[q.id].selected_index
                            if q.id in answers_by_q
                            else draft_by_q.get(str(q.id), {}).get("selected_index")
                        ),
                        "correct_index": q.correct_index
                        if assessment.status == "scored"
                        else None,
                        "is_correct": answers_by_q[q.id].is_correct
                        if q.id in answers_by_q
                        else None,
                        "explanation": q.explanation
                        if assessment.status == "scored"
                        else None,
                    }
                    for q in assessment.questions
                ],
            }
            import json

            return json.dumps(payload, indent=2), f"{base}.json", "application/json"

        lines = [
            "# Baseline assessment export",
            f"- Status: {assessment.status}",
            f"- Score: {assessment.score_percent if assessment.score_percent is not None else '—'}%",
            f"- Correct: {assessment.correct_count}/{assessment.total_count}",
            "",
        ]
        for i, q in enumerate(assessment.questions, start=1):
            ans = answers_by_q.get(q.id)
            draft_sel = draft_by_q.get(str(q.id), {}).get("selected_index")
            selected = ans.selected_index if ans else draft_sel
            lines.append(f"## Q{i}. {q.stem}")
            for ci, choice in enumerate(q.choices or []):
                mark = "→ " if selected == ci else "  "
                lines.append(f"{mark}{ci + 1}. {choice}")
            if assessment.status == "scored" and ans:
                lines.append(
                    f"- Result: {'Correct' if ans.is_correct else 'Incorrect'}"
                )
                lines.append(f"- Correct choice: {(q.choices or [''])[q.correct_index]}")
                if q.explanation:
                    lines.append(f"- Explanation: {q.explanation}")
            lines.append("")
        return "\n".join(lines), f"{base}.md", "text/markdown; charset=utf-8"

    def _to_out(self, assessment: Assessment, *, reveal_answers: bool) -> AssessmentOut:
        from app.schemas.assessment import AssessmentAnswerIn

        answers_by_q = {a.question_id: a for a in assessment.answers}
        draft_raw = (assessment.draft_payload or {}).get("answers") or []
        draft_answers: list[AssessmentAnswerIn] = []
        draft_by_q: dict[str, int] = {}
        for item in draft_raw:
            if not isinstance(item, dict):
                continue
            try:
                qid = UUID(str(item.get("question_id")))
                sel = int(item.get("selected_index"))
            except (TypeError, ValueError):
                continue
            draft_by_q[str(qid)] = sel
            draft_answers.append(AssessmentAnswerIn(question_id=qid, selected_index=sel))

        questions: list[AssessmentQuestionOut] = []
        for q in assessment.questions:
            ans = answers_by_q.get(q.id)
            selected = ans.selected_index if ans else draft_by_q.get(str(q.id))
            questions.append(
                AssessmentQuestionOut(
                    id=q.id,
                    skill_id=q.skill_id,
                    skill_code=q.skill.code if q.skill else None,
                    skill_name=q.skill.name if q.skill else None,
                    stem=q.stem,
                    choices=list(q.choices or []),
                    sort_order=q.sort_order,
                    correct_index=q.correct_index if reveal_answers else None,
                    explanation=q.explanation if reveal_answers else None,
                    selected_index=selected if reveal_answers or ans or selected is not None else None,
                    is_correct=ans.is_correct if ans else None,
                )
            )
        return AssessmentOut(
            id=assessment.id,
            user_id=assessment.user_id,
            organization_id=assessment.organization_id,
            kind=assessment.kind,
            status=assessment.status,
            provider=assessment.provider,
            model=assessment.model,
            prompt_version=assessment.prompt_version,
            score_percent=assessment.score_percent,
            correct_count=assessment.correct_count,
            total_count=assessment.total_count,
            started_at=assessment.started_at,
            submitted_at=assessment.submitted_at,
            error_message=assessment.error_message,
            created_at=assessment.created_at,
            questions=questions,
            draft_answers=draft_answers if not reveal_answers else [],
        )
