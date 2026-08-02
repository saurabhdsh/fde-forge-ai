"""Unit tests for Phase 2 assessment scoring helpers and schemas."""

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

from app.ai.prompts.baseline_assessment import is_low_quality_question
from app.schemas.assessment import AssessmentOut, AssessmentQuestionOut
from app.services.assessment_service import proficiency_from_accuracy, resolve_skill_ref


def test_proficiency_bands() -> None:
    assert proficiency_from_accuracy(1.0) == "proficient"
    assert proficiency_from_accuracy(0.6) == "working"
    assert proficiency_from_accuracy(0.59) == "awareness"
    assert proficiency_from_accuracy(0.0) == "awareness"


def test_filters_absurd_distractors() -> None:
    assert is_low_quality_question(
        "What is a challenge of Generative AI in healthcare?",
        [
            "It is always accurate and reliable.",
            "Ensuring data privacy",
            "Model cost",
            "Integration effort",
        ],
    )
    # Soft definition stems are treated as too easy
    assert is_low_quality_question(
        "What is a primary challenge when adopting Generative AI in healthcare?",
        [
            "Ensuring privacy and regulatory compliance",
            "Choosing a GPU brand only",
            "Avoiding all structured data",
            "Removing human review by policy",
        ],
    )


def test_keeps_hard_scenario_stems() -> None:
    assert not is_low_quality_question(
        "A provider customer insists on deploying a generative AI note-assist tool in the charting workflow "
        "before chart-audit sampling is ready. Which FDE action best reduces clinical-adjacent risk while "
        "preserving momentum?",
        [
            "Ship with a constrained pilot scope, human review gate, and explicit out-of-scope use cases",
            "Disable all audit logging to reduce friction for clinicians",
            "Train only on production PHI overnight without a BAA amendment",
            "Promise zero hallucination risk in the SOW to unblock legal",
        ],
    )


def test_resolve_skill_ref_fuzzy() -> None:
    skill = SimpleNamespace(id=uuid4(), code="generative_ai", name="Generative AI")
    by_code = {"generative_ai": skill}
    by_code_lower = {"generative_ai": skill}
    by_name_lower = {"generative ai": skill}
    assert (
        resolve_skill_ref(
            "Generative AI",
            by_code=by_code,
            by_code_lower=by_code_lower,
            by_name_lower=by_name_lower,
        )
        is skill
    )
    assert (
        resolve_skill_ref(
            "generative-ai",
            by_code=by_code,
            by_code_lower=by_code_lower,
            by_name_lower=by_name_lower,
        )
        is skill
    )


def test_pre_submit_question_hides_answer_key() -> None:
    q = AssessmentQuestionOut(
        id=uuid4(),
        skill_id=uuid4(),
        skill_code="genai",
        skill_name="Generative AI",
        stem="What is RAG?",
        choices=["A", "B", "C", "D"],
        sort_order=0,
        correct_index=None,
        explanation=None,
    )
    dumped = q.model_dump()
    assert dumped["correct_index"] is None
    assert dumped["explanation"] is None


def test_assessment_out_shape() -> None:
    out = AssessmentOut(
        id=uuid4(),
        user_id=uuid4(),
        organization_id=uuid4(),
        kind="baseline",
        status="ready",
        created_at=datetime.now(UTC),
        questions=[],
    )
    assert out.status == "ready"
    assert out.score_percent is None
