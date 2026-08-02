"""Fast domain course generation prompt (Bedrock-friendly size)."""

PROMPT_VERSION = "domain_course.v1.3-fast"

DOMAIN_BLUEPRINTS: dict[str, str] = {
    "healthcare": (
        "Healthcare FDE: care continuum, clinical vs admin data, FHIR/interop, "
        "claims/prior auth adjacency, HIPAA posture for AI, customer discovery, "
        "GenAI deployment risks with human-in-the-loop."
    ),
    "life_sciences": (
        "Life Sciences FDE: R&D→trial→regulatory path, GxP mindset, clinical data "
        "concepts, PV signals, AI in discovery/development, validation discipline, "
        "sponsor-CRO-site collaboration."
    ),
    "technical": (
        "Technical FDE: customer-environment delivery, GenAI patterns (RAG/agents/evals), "
        "secure SDLC, observability, integration tradeoffs, production readiness."
    ),
}

SYSTEM_PROMPT = """You are an instructional designer for FDE Forge AI.
Build a SHORT, high-quality domain course for Forward Deployed Engineers.

HARD LIMITS (must obey — keep JSON small for Bedrock):
1. Exactly 3 modules.
2. Exactly 4 slides per module (12 slides total).
3. body_markdown: 2–4 short sentences per slide (no essays).
4. learning_goals: 3–5 strings. Module objectives: 2–3 strings each.
5. visual_type: prefer "cards" with 2–3 items[{title,body}] OR "process" with 3 steps[{label,detail}].
   Use "none" + {} if unsure. Skip map/diagram unless trivial.
6. key_takeaway: one short sentence per slide. self_check optional (max 2 in whole course).
7. Cover LEARNER-SELECTED TOPICS first; keep FDE practice + risk briefly.
8. If SOURCE MATERIALS exist, use a few concrete terms only — do not paste long excerpts.
9. Workforce learning only — no clinical medical advice.
10. Return JSON matching the schema only — no markdown fences.
"""


def build_user_prompt(
    *,
    domain: str,
    target_role: str | None,
    other_domains: list[str],
    enrichment_text: str | None = None,
    enrichment_sources: list[str] | None = None,
    selected_topics: list[dict] | None = None,
) -> str:
    blueprint = DOMAIN_BLUEPRINTS.get(domain, DOMAIN_BLUEPRINTS["technical"])
    parts = [
        f"Generate a compact domain course for domain_code={domain}.",
        f"Target FDE role: {target_role or 'General FDE'}",
        f"Learner's other domains: {', '.join(other_domains) or 'none'}",
        "",
        f"BLUEPRINT:\n{blueprint}",
        "",
        "Output: title, summary, learning_goals[], "
        "modules[{title, objectives[], slides[{title, body_markdown, visual_type, "
        "visual_payload, key_takeaway, self_check?}]}].",
        "Remember: 3 modules × 4 slides. Keep text concise.",
    ]
    if selected_topics:
        # Cap topics so the prompt stays small even if learner selected many
        capped = selected_topics[:8]
        topic_lines = "\n".join(
            f"- {t.get('id')}: {t.get('label')} — {t.get('blurb')}"
            for t in capped
        )
        parts.extend(
            [
                "",
                "LEARNER-SELECTED TOPICS (prioritize these; max 8 listed):",
                topic_lines,
            ]
        )
    if enrichment_text and enrichment_text.strip():
        sources = ", ".join(enrichment_sources or []) or "uploaded org documents"
        # Hard cap enrichment — large docs make Bedrock very slow
        clipped = enrichment_text.strip()[:3000]
        parts.extend(
            [
                "",
                "ORGANIZATION SOURCE MATERIALS (brief excerpts only):",
                f"Source files: {sources}",
                clipped,
            ]
        )
    return "\n".join(parts)
