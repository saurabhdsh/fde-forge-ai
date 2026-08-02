"""Scientifically designed domain course generation prompt."""

PROMPT_VERSION = "domain_course.v1.2"

DOMAIN_BLUEPRINTS: dict[str, str] = {
    "healthcare": (
        "Healthcare FDE super-course covering: care continuum map (patient→provider→payer), "
        "clinical vs administrative data, FHIR/interop realities, prior auth & claims adjacency, "
        "HIPAA/privacy posture for AI systems, customer discovery in provider/payer accounts, "
        "deployment risks for GenAI in clinical-adjacent workflows, evidence and human-in-the-loop. "
        "FDE + industry dual lens."
    ),
    "life_sciences": (
        "Life Sciences FDE super-course covering: R&D→preclinical→trial→regulatory path, "
        "GxP mindset, clinical data standards (CDISC/eSource concepts), pharmacovigilance signals, "
        "AI use-cases in discovery and development, validation/documentation discipline, "
        "sponsor-CRO-site collaboration, inspection readiness. FDE + industry dual lens."
    ),
    "technical": (
        "Technical FDE foundations super-course covering: enterprise delivery for customer environments, "
        "GenAI system patterns (RAG, agents, evals), secure SDLC, observability, "
        "integration with healthcare/LS adjacent systems, architecture tradeoffs, "
        "production readiness and rollback thinking."
    ),
}

SYSTEM_PROMPT = """You are an instructional designer and industry SME for FDE Forge AI.
Build a scientifically structured domain super-course for Forward Deployed Engineers.

Instructional design requirements (must follow):
1. Start from clear learning goals using Bloom verbs (understand, apply, analyze, evaluate).
2. Scaffold: orientation → mental models → domain workflows → FDE practice → risk/governance → synthesis.
3. 5–7 modules; each module has 6–10 slides (technical domain may be 4–5 modules × 5–8 slides).
4. Each slide is DETAILED and useful (not slogans): explain mechanisms, actors, artifacts, failure modes.
5. Every slide includes a visual_type and visual_payload suitable for SVG rendering:
   - map: nodes[{id,label,x,y}], edges[{from,to,label?}]
   - process: steps[{label,detail}]
   - timeline: events[{label,detail}]
   - cards: items[{title,body}]
   - diagram: nodes + edges (same as map)
   - none: empty object
6. For map/diagram: ALWAYS include at least 2 nodes with short labels (≤28 chars), unique ids used by edges,
   and coordinates with padding — x in 12–88 and y in 15–85 (never near 0 or 100 so labels are not clipped).
   Spread nodes; do not stack them at the same x,y. Prefer 3–6 nodes. Edges must reference existing node ids.
7. Never return visual_type other than none with an empty payload; if unsure, use cards with 3–4 items.
8. Include key_takeaway on every slide; add self_check occasionally {question, answer}.
9. Dual perspective on many slides: Industry reality AND Forward Deployed Engineer actions.
10. When LEARNER-SELECTED TOPICS are provided: the course MUST prioritize those topics —
    dedicate modules or slide blocks to each selected topic, keep coverage coherent, and still
    include enough FDE practice + risk/governance. Do not ignore selected topics.
11. When ORGANIZATION SOURCE MATERIALS are provided: (a) sharpen accuracy using those materials,
    (b) weave distinctive terms, processes, and examples from the docs into slides,
    (c) ADD 1–2 extra modules or several additional slides covering topics found in the sources
    that are missing from the base blueprint, (d) do not invent proprietary secrets beyond the docs,
    (e) still keep the instructional scaffold — do not dump the source text raw onto slides.
12. No clinical medical advice; workforce learning only.
13. Return JSON matching the schema only.
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
        f"Generate a full domain super-course for domain_code={domain}.",
        f"Target FDE role: {target_role or 'General FDE'}",
        f"Learner's other domains: {', '.join(other_domains) or 'none'}",
        "",
        f"BLUEPRINT:\n{blueprint}",
        "",
        "Output fields: title, summary, learning_goals (list of strings), "
        "modules[{title, objectives[], slides[{title, body_markdown, visual_type, "
        "visual_payload, key_takeaway, self_check?}]}].",
        "Make body_markdown multi-paragraph and specific. Prefer concrete examples.",
    ]
    if selected_topics:
        topic_lines = "\n".join(
            f"- {t.get('id')}: {t.get('label')} — {t.get('blurb')} [{t.get('group')}]"
            for t in selected_topics
        )
        parts.extend(
            [
                "",
                "LEARNER-SELECTED TOPICS (must cover — one course for this domain):",
                topic_lines,
                "Structure modules around these topics; weave FDE customer practice throughout.",
            ]
        )
    if enrichment_text and enrichment_text.strip():
        sources = ", ".join(enrichment_sources or []) or "uploaded org documents"
        parts.extend(
            [
                "",
                "ORGANIZATION SOURCE MATERIALS (use to enrich + add topics):",
                f"Source files: {sources}",
                "Instructions: Merge blueprint + selected topics with these materials. Prefer "
                "source-grounded detail where they conflict with generic knowledge.",
                "",
                enrichment_text.strip(),
            ]
        )
    return "\n".join(parts)
