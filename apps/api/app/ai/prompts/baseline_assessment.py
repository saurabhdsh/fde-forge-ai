"""Versioned prompt for baseline skill assessment generation."""

PROMPT_VERSION = "baseline_assessment.v3"

MIN_QUESTIONS = 25

SYSTEM_PROMPT = """You are a senior enterprise assessment author for FDE Forge AI.
Create VERY HARD multiple-choice questions for experienced Forward Deployed Engineers.

Hard rules:
- Exactly 4 choices per question; exactly one correct answer.
- Map each question to ONE skill_code from the provided list only.
- The stem MUST be about that skill’s actual topic. Do not borrow terms from unrelated skills.
- Difficulty MUST be advanced / expert: multi-step reasoning, tradeoffs, failure modes,
  architecture decisions, governance edge cases, customer-deployment dilemmas.
- Do NOT ask elementary definitions, glossary lookups, or "what does X stand for?" trivia.
- Do NOT ask soft opinion questions with an obvious politically correct answer.
- Distractors must be professionally plausible near-misses (common expert mistakes),
  never absurd absolutes like "always accurate", "never fails", or "no risks".
- Correct answers should NOT be obvious to a junior engineer after a quick skim —
  require domain judgment a seasoned FDE would use under ambiguity.
- Prefer customer-site / production-adjacent scenarios with incomplete information.
- Explanations must briefly justify the correct choice and why strong distractors fail (2–3 sentences).
- Keep language precise for FDE / healthcare / life-sciences / enterprise GenAI contexts.
- Return JSON only matching the provided schema.
- Workforce training assessment — not clinical advice or hiring decisions.
"""


def build_user_prompt(
    *,
    skills: list[dict],
    target_role: str | None,
    domains: list[str],
    question_count: int = MIN_QUESTIONS,
    extra_instruction: str | None = None,
) -> str:
    skill_lines = "\n".join(
        (
            f"- code={s['code']}; name={s['name']}; pillar={s.get('pillar', 'n/a')}; "
            f"category={s.get('category', 'n/a')}; domain={s.get('domain', 'n/a')}"
            + (f"; about={s['description']}" if s.get("description") else "")
        )
        for s in skills
    )
    parts = [
        f"Generate exactly {question_count} VERY HARD multiple-choice questions.",
        f"Target FDE role: {target_role or 'General FDE'}",
        f"Learner domains: {', '.join(domains) if domains else 'general'}",
        "",
        "ALLOWED SKILLS — copy skill_code EXACTLY as written (do not invent codes):",
        skill_lines,
        "",
        "Coverage & difficulty:",
        f"- Produce at least {question_count} questions; distribute across skills (multiple per skill if needed).",
        "- Mix: scenario diagnosis, architecture tradeoff, risk/compliance edge case, "
        "integration failure analysis, eval/ops judgment.",
        "- Every stem must demand non-obvious expert reasoning.",
        "- Avoid easy stems like 'What is X?' or 'Which of the following best defines…'.",
        "- skill_code must be an exact value from the list above (e.g. generative_ai).",
        "",
        "Each question must include: skill_code, stem, choices (4 distinct strings), "
        "correct_index (0-3), explanation.",
    ]
    if extra_instruction:
        parts.extend(["", extra_instruction])
    return "\n".join(parts)


def is_low_quality_question(stem: str, choices: list[str]) -> bool:
    """Heuristic filter for unfair, degenerate, or too-easy MCQs."""
    banned_fragments = (
        "always accurate",
        "always reliable",
        "never fails",
        "has no risks",
        "no privacy concerns",
        "irrelevant in all",
        "none of the above",
        "all of the above",
    )
    blob = " ".join([stem, *choices]).lower()
    if any(f in blob for f in banned_fragments):
        return True
    # Reject near-duplicate choices
    normalized = [c.strip().lower() for c in choices]
    if len(set(normalized)) < 4:
        return True
    if len(stem.strip()) < 40:
        return True
    easy_prefixes = (
        "what is ",
        "what does ",
        "which of the following best defines",
        "which of the following is the definition",
        "define ",
        "which option means",
    )
    stem_l = stem.strip().lower()
    if any(stem_l.startswith(p) for p in easy_prefixes):
        return True
    return False
