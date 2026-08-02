"""Prompt for FDE coding playground assessment generation."""

PROMPT_VERSION = "coding_playground.v1"
MIN_QUESTIONS = 25

SYSTEM_PROMPT = """You are a senior FDE assessment author for FDE Forge AI.
Create HARD Python coding challenges for Forward Deployed Engineers building GenAI systems,
tool-calling agents, RAG pipelines, eval harnesses, and domain integrations
(healthcare / life sciences / enterprise).

Rules:
- Exactly the requested number of questions.
- Language: Python 3.
- Each task must be implementable in a single file / function or small class.
- Focus areas (mix across the set): agent tool contracts, ReAct-style loops, structured output parsing,
  RAG chunking/retrieval glue, prompt+memory plumbing, eval scorers, retry/backoff, PII/redaction,
  FHIR/claims-adjacent data transforms (no clinical advice), GxP-minded audit logging,
  secure config, observability hooks, JSON schema validation, rate limiting, idempotency.
- Difficulty: hard — not toy “print hello”; require correct edge-case handling.
- Provide starter_code with clear TODO and function signatures.
- Provide rubric as 3–5 criteria strings a grader can check.
- Provide a concise reference_solution (correct-but-compact).
- Domains: tag domain_focus as healthcare | life_sciences | technical | general.
- No real credentials, no requests to live PHI, workforce training only.
- Return JSON matching the schema only.
"""


def build_user_prompt(
    *,
    domains: list[str],
    target_role: str | None,
    skills: list[str],
    question_count: int = MIN_QUESTIONS,
) -> str:
    return (
        f"Generate exactly {question_count} HARD Python coding assessment questions.\n"
        f"Target FDE role: {target_role or 'General FDE'}\n"
        f"Learner domains: {', '.join(domains) or 'technical'}\n"
        f"Confirmed skills (bias coverage when relevant): {', '.join(skills[:20]) or 'genai, agents'}\n\n"
        "Coverage requirements:\n"
        "- At least 10 questions about agent development (tools, planners, memory, handoffs).\n"
        "- At least 8 questions about GenAI systems (RAG, evals, structured generation, guardrails).\n"
        "- Remaining questions: domain-adjacent data/integration tasks for the learner domains.\n"
        "- Spread domain_focus across the learner's domains; use technical/general for shared skills.\n\n"
        "Each question fields: title, prompt_markdown, language ('python'), starter_code, "
        "topic_tags (list), domain_focus, difficulty ('hard'), rubric (list of strings), "
        "reference_solution.\n"
        "prompt_markdown must state inputs/outputs and edge cases clearly."
    )


GRADE_SYSTEM_PROMPT = """You are a strict FDE coding grader.
Score each submission 0–100 against the rubric and a compact reference solution.
Pass threshold intent: score >= 70 means passed.
Be fair to alternate correct approaches. Penalize missing edge cases, insecure patterns,
fabricated APIs, or empty stubs. Return JSON only matching the schema.
"""


def build_grade_prompt(*, items: list[dict]) -> str:
    blocks = []
    for i, item in enumerate(items, start=1):
        blocks.append(
            f"### Item {i}\n"
            f"question_id: {item['question_id']}\n"
            f"title: {item['title']}\n"
            f"prompt:\n{item['prompt'][:2500]}\n"
            f"rubric: {item['rubric']}\n"
            f"reference_solution:\n{item.get('reference_solution') or '(none)'}\n"
            f"candidate_code:\n{item['code'][:6000]}\n"
        )
    return (
        "Grade each coding submission. For every item return question_id, score (0-100), "
        "passed (bool), feedback (2-4 sentences), rubric_scores (map criterion→0-10).\n\n"
        + "\n".join(blocks)
    )
