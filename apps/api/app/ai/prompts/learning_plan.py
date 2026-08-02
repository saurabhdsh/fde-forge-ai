"""Versioned prompt for personalized learning plan generation."""

PROMPT_VERSION = "learning_plan.v1"

SYSTEM_PROMPT = """You are an enterprise learning coach for FDE Forge AI.
Create a prioritized learning plan for a Forward Deployed Engineer candidate.
Rules:
- Prioritize skills the candidate answered incorrectly or scored weakly.
- Map each item to a provided skill_code only.
- Provide short rationales and realistic estimated_hours (1–12).
- Keep the plan practical for weekly study hours if provided.
- Return JSON only matching the provided schema.
"""


def build_user_prompt(
    *,
    target_role: str | None,
    weekly_hours: int | None,
    weak_skills: list[dict],
    strong_skills: list[dict],
    max_items: int = 8,
) -> str:
    weak = "\n".join(
        f"- {s['code']}: {s['name']} (accuracy={s.get('accuracy', 0):.0%})" for s in weak_skills
    ) or "- (none)"
    strong = "\n".join(f"- {s['code']}: {s['name']}" for s in strong_skills) or "- (none)"
    return (
        f"Build up to {max_items} prioritized learning plan items.\n"
        f"Target FDE role: {target_role or 'General FDE'}\n"
        f"Available weekly hours: {weekly_hours or 8}\n\n"
        f"WEAK / INCORRECT SKILLS:\n{weak}\n\n"
        f"STRONG SKILLS:\n{strong}\n\n"
        "Return summary plus items with skill_code, priority (1=highest), "
        "rationale, and estimated_hours."
    )
