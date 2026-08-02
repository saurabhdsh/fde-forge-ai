"""Personalized learning plan generation and item updates."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.gateway import AIGateway
from app.ai.prompts.learning_plan import (
    PROMPT_VERSION as PLAN_PROMPT_VERSION,
)
from app.ai.prompts.learning_plan import (
    SYSTEM_PROMPT,
    build_user_prompt,
)
from app.core.config import get_settings
from app.core.exceptions import ConfigurationError, NotFoundError, ValidationAppError
from app.core.logging import get_logger
from app.models.assessment import Assessment
from app.models.learning_plan import LearningPlan, LearningPlanItem
from app.repositories.learner import LearnerRepository
from app.repositories.learning_plan import LearningPlanRepository
from app.schemas.learning_plan import (
    GeneratedLearningPlanPayload,
    LearningPlanItemOut,
    LearningPlanItemUpdate,
    LearningPlanOut,
)
from app.services.audit_service import AuditService

logger = get_logger(__name__)


class LearningPlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LearningPlanRepository(session)
        self.learners = LearnerRepository(session)
        self.audit = AuditService(session)
        self.ai = AIGateway()
        self.settings = get_settings()

    async def get_latest(self, user_id: UUID, organization_id: UUID) -> LearningPlanOut | None:
        plan = await self.repo.latest_for_user(user_id, organization_id)
        if not plan:
            return None
        return self._to_out(plan)

    async def update_item(
        self,
        *,
        item_id: UUID,
        user_id: UUID,
        organization_id: UUID,
        payload: LearningPlanItemUpdate,
        actor_id: UUID,
        correlation_id: str | None,
    ) -> LearningPlanOut:
        item = await self.repo.get_item(item_id, organization_id)
        if not item or item.plan.user_id != user_id:
            raise NotFoundError("Learning plan item not found")
        item.status = payload.status
        if all(i.status == "done" for i in item.plan.items):
            item.plan.status = "completed"
        elif any(i.status in {"in_progress", "done"} for i in item.plan.items):
            item.plan.status = "active"
        await self.session.flush()
        await self.audit.log(
            action="learning_plan.item_update",
            entity_type="learning_plan_item",
            entity_id=item.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={"status": item.status},
            correlation_id=correlation_id,
        )
        refreshed = await self.repo.get_by_id(item.plan_id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    async def generate_from_assessment(
        self,
        *,
        assessment: Assessment,
        user_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        correlation_id: str | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> LearningPlanOut:
        if not self.settings.ai_configured:
            raise ConfigurationError(
                "OPENAI_API_KEY is not configured. Set OPENAI_API_KEY to enable learning plans."
            )

        profile = await self.learners.get_by_user(user_id, organization_id)
        answers_by_q = {a.question_id: a for a in assessment.answers}
        per_skill: dict[UUID, list[bool]] = defaultdict(list)
        skill_meta: dict[UUID, tuple[str, str]] = {}
        for q in assessment.questions:
            ans = answers_by_q.get(q.id)
            if not ans or not q.skill:
                continue
            per_skill[q.skill_id].append(ans.is_correct)
            skill_meta[q.skill_id] = (q.skill.code, q.skill.name)

        weak: list[dict] = []
        strong: list[dict] = []
        for skill_id, results in per_skill.items():
            code, name = skill_meta[skill_id]
            accuracy = sum(1 for r in results if r) / len(results)
            entry = {"code": code, "name": name, "accuracy": accuracy}
            if accuracy < 1.0:
                weak.append(entry)
            else:
                strong.append(entry)
        weak.sort(key=lambda x: x["accuracy"])
        if not weak:
            # Still produce a light plan from strong skills for continued growth
            weak = [{"code": c, "name": n, "accuracy": 0.5} for c, n in list(skill_meta.values())[:3]]

        result = await self.ai.generate_structured(
            prompt=build_user_prompt(
                target_role=profile.target_fde_role if profile else None,
                weekly_hours=profile.available_weekly_hours if profile else 8,
                weak_skills=weak,
                strong_skills=strong,
            ),
            schema=GeneratedLearningPlanPayload,
            system=SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=3000,
        )
        payload = GeneratedLearningPlanPayload.model_validate(result.data)
        code_map = await self.repo.get_skill_map(
            list({i.skill_code for i in payload.items})
        )

        plan = LearningPlan(
            user_id=user_id,
            organization_id=organization_id,
            source_assessment_id=assessment.id,
            status="active",
            summary=payload.summary,
            provider=result.provider,
            model=result.model,
        )
        await self.repo.create(plan)

        priority = 1
        for item in sorted(payload.items, key=lambda x: x.priority):
            skill = code_map.get(item.skill_code)
            if not skill:
                continue
            self.session.add(
                LearningPlanItem(
                    plan_id=plan.id,
                    skill_id=skill.id,
                    priority=priority,
                    status="todo",
                    rationale=item.rationale,
                    estimated_hours=item.estimated_hours,
                )
            )
            priority += 1

        if priority == 1:
            raise ValidationAppError("Learning plan contained no mapped skills")

        if profile:
            profile.onboarding_status = "plan_ready"

        await self.session.flush()
        await self.audit.log(
            action="learning_plan.generated",
            entity_type="learning_plan",
            entity_id=plan.id,
            organization_id=organization_id,
            actor_id=actor_id,
            after={
                "source_assessment_id": str(assessment.id),
                "item_count": priority - 1,
                "prompt_version": PLAN_PROMPT_VERSION,
            },
            correlation_id=correlation_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        refreshed = await self.repo.get_by_id(plan.id, organization_id)
        assert refreshed is not None
        return self._to_out(refreshed)

    def _to_out(self, plan: LearningPlan) -> LearningPlanOut:
        items = [
            LearningPlanItemOut(
                id=i.id,
                skill_id=i.skill_id,
                skill_code=i.skill.code if i.skill else None,
                skill_name=i.skill.name if i.skill else None,
                priority=i.priority,
                status=i.status,
                rationale=i.rationale,
                estimated_hours=i.estimated_hours,
            )
            for i in plan.items
        ]
        return LearningPlanOut(
            id=plan.id,
            user_id=plan.user_id,
            organization_id=plan.organization_id,
            source_assessment_id=plan.source_assessment_id,
            status=plan.status,
            summary=plan.summary,
            provider=plan.provider,
            model=plan.model,
            created_at=plan.created_at,
            items=items,
            completed_count=sum(1 for i in items if i.status == "done"),
            total_count=len(items),
        )
