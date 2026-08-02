"""Prompts for communication interview rubric grading."""

PROMPT_VERSION = "communication_interview.v1"

DIMENSIONS = [
    ("clarity", "Clarity & concision"),
    ("structure", "Structured storytelling"),
    ("stakeholder_empathy", "Stakeholder empathy"),
    ("technical_storytelling", "Technical storytelling"),
    ("composure", "Composure under pressure"),
]

SYSTEM_PROMPT = """You are a senior Forward Deployed Engineer interview coach for FDE Forge AI.
Grade a candidate's live communication interview transcript against a strict soft-skills rubric.

Score each dimension 0–5:
0 = not demonstrated / absent
1 = weak
2 = developing
3 = solid baseline
4 = strong
5 = exceptional (exec-ready)

Rules:
- Be fair but exacting; cite short evidence quotes from the candidate (role=user) only.
- Penalize rambling, buzzword salads, no structure, defensive pushback handling, or missing tradeoffs.
- Reward crisp executive framing, clarifying questions, risk awareness (HIPAA/GxP/PII when relevant),
  and calm handling of ambiguity.
- overall score_percent is 0–100, coherent to the dimension average (avg/5 * 100).
- Return JSON matching the schema only.
"""


def build_grade_prompt(
    *,
    domains: list[str],
    target_role: str | None,
    transcript: list[dict],
) -> str:
    lines = []
    for i, turn in enumerate(transcript[:80], start=1):
        role = turn.get("role", "user")
        content = (turn.get("content") or "")[:1200]
        lines.append(f"{i}. [{role}] {content}")
    transcript_block = "\n".join(lines) or "(empty transcript)"
    dims = ", ".join(f"{d[0]} ({d[1]})" for d in DIMENSIONS)
    return (
        "Grade this FDE communication interview transcript.\n"
        f"Target FDE role: {target_role or 'General FDE'}\n"
        f"Learner domains: {', '.join(domains) or 'technical'}\n"
        f"Required dimensions (use these ids): {dims}\n\n"
        "Return: score_percent (0-100), dimensions (id,label,score 0-5,feedback), "
        "coach_summary (3-5 sentences), evidence_quotes (2-5 strings from candidate), "
        "strengths (list), improvements (list).\n\n"
        f"Transcript:\n{transcript_block}"
    )


def build_conversational_context(
    *,
    domains: list[str],
    target_role: str | None,
    skills: list[str],
    candidate_name: str | None,
) -> str:
    name = candidate_name or "the candidate"
    return (
        f"You are a senior FDE hiring partner interviewing {name} for a Forward Deployed Engineer role "
        f"focused on {', '.join(domains) or 'enterprise GenAI'}. "
        f"Target role: {target_role or 'Customer-facing FDE'}. "
        f"Candidate skills to probe: {', '.join(skills[:16]) or 'GenAI systems and agents'}. "
        "Run a 12–15 minute behavioral + technical-communication interview. "
        "Open warmly, then ask about a recent GenAI/agent delivery, stakeholder pushback, ambiguity, "
        "an executive update, and domain risk (privacy, compliance, safety). "
        "Ask one question at a time, follow up on vague answers, and keep a professional tone. "
        "Do not reveal scoring rubrics. End by thanking them and saying results will be scored shortly."
    )
