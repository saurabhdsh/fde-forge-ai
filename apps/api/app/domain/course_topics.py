"""Domain course topic catalogs for learner topic selection widgets.

One course is generated per domain; selected topics shape / enrich that course.
"""

from __future__ import annotations

from typing import TypedDict


class TopicDef(TypedDict):
    id: str
    label: str
    blurb: str
    group: str


DOMAIN_TOPICS: dict[str, list[TopicDef]] = {
    "healthcare": [
        # Care delivery & ecosystem
        {
            "id": "hc_care_continuum",
            "label": "Care continuum map",
            "blurb": "Patient → provider → payer journey",
            "group": "Ecosystem",
        },
        {
            "id": "hc_provider_ops",
            "label": "Provider operations",
            "blurb": "Hospitals, ambulatory, IDN workflows",
            "group": "Ecosystem",
        },
        {
            "id": "hc_payer_ops",
            "label": "Payer operations",
            "blurb": "Membership, benefits, utilization",
            "group": "Ecosystem",
        },
        {
            "id": "hc_value_based",
            "label": "Value-based care",
            "blurb": "Risk, quality, shared savings",
            "group": "Ecosystem",
        },
        {
            "id": "hc_customer_discovery",
            "label": "Customer discovery",
            "blurb": "Provider & payer buying centers",
            "group": "Ecosystem",
        },
        # Data & interop
        {
            "id": "hc_clinical_vs_admin",
            "label": "Clinical vs admin data",
            "blurb": "Charts, claims, identity",
            "group": "Data & interop",
        },
        {
            "id": "hc_fhir_interop",
            "label": "FHIR & interop",
            "blurb": "APIs, EHRs, integration reality",
            "group": "Data & interop",
        },
        {
            "id": "hc_ehr_workflows",
            "label": "EHR workflows",
            "blurb": "Orders, notes, CDS adjacency",
            "group": "Data & interop",
        },
        {
            "id": "hc_claims_prior_auth",
            "label": "Claims & prior auth",
            "blurb": "Adjudication, PA pain points",
            "group": "Data & interop",
        },
        {
            "id": "hc_quality_measures",
            "label": "Quality measures",
            "blurb": "HEDIS, Star, outcomes data",
            "group": "Data & interop",
        },
        {
            "id": "hc_rpm_telehealth",
            "label": "RPM & telehealth",
            "blurb": "Remote monitoring, virtual care",
            "group": "Data & interop",
        },
        # Privacy & risk
        {
            "id": "hc_hipaa_privacy",
            "label": "HIPAA & privacy",
            "blurb": "BAAs, PHI minimization",
            "group": "Privacy & risk",
        },
        {
            "id": "hc_security_identity",
            "label": "Security & identity",
            "blurb": "Access, audit, break-glass",
            "group": "Privacy & risk",
        },
        {
            "id": "hc_ai_clinical_risk",
            "label": "AI clinical-adjacent risk",
            "blurb": "HITL, evidence, hallucination",
            "group": "Privacy & risk",
        },
        {
            "id": "hc_deployment_patterns",
            "label": "Deployment patterns",
            "blurb": "Pilots, sandboxes, rollbacks",
            "group": "Privacy & risk",
        },
        # GenAI in HC
        {
            "id": "hc_genai_documentation",
            "label": "GenAI documentation",
            "blurb": "Ambient notes, summarization",
            "group": "GenAI in HC",
        },
        {
            "id": "hc_genai_coding",
            "label": "Coding & revenue cycle AI",
            "blurb": "CDI, coding assist risks",
            "group": "GenAI in HC",
        },
        {
            "id": "hc_genai_member",
            "label": "Member & patient AI",
            "blurb": "Chat, navigation, literacy",
            "group": "GenAI in HC",
        },
        {
            "id": "hc_eval_monitoring",
            "label": "Eval & monitoring",
            "blurb": "Groundedness, drift, audit",
            "group": "GenAI in HC",
        },
        {
            "id": "hc_fde_playbook",
            "label": "FDE customer playbook",
            "blurb": "Discovery → pilot → scale",
            "group": "GenAI in HC",
        },
    ],
    "life_sciences": [
        # Pipeline
        {
            "id": "ls_rd_path",
            "label": "R&D → trial path",
            "blurb": "Discovery to Phase 3 map",
            "group": "Pipeline",
        },
        {
            "id": "ls_preclinical",
            "label": "Preclinical & safety",
            "blurb": "GLP, tox, CMC adjacency",
            "group": "Pipeline",
        },
        {
            "id": "ls_clinical_ops",
            "label": "Clinical operations",
            "blurb": "Sites, CROs, monitoring",
            "group": "Pipeline",
        },
        {
            "id": "ls_regulatory",
            "label": "Regulatory path",
            "blurb": "IND/NDA/BLA mindset",
            "group": "Pipeline",
        },
        {
            "id": "ls_pharmacovigilance",
            "label": "Pharmacovigilance",
            "blurb": "Signals, AE reporting",
            "group": "Pipeline",
        },
        {
            "id": "ls_market_access",
            "label": "Market access",
            "blurb": "HEOR, evidence, payers",
            "group": "Pipeline",
        },
        # Quality & data
        {
            "id": "ls_gxp",
            "label": "GxP mindset",
            "blurb": "GCP/GMP/GLP discipline",
            "group": "Quality & data",
        },
        {
            "id": "ls_cdisc",
            "label": "CDISC & clinical data",
            "blurb": "SDTM, ADaM, eSource",
            "group": "Quality & data",
        },
        {
            "id": "ls_validation",
            "label": "CSV & validation",
            "blurb": "IQ/OQ/PQ for AI systems",
            "group": "Quality & data",
        },
        {
            "id": "ls_inspection",
            "label": "Inspection readiness",
            "blurb": "Audit trails, ALCOA+",
            "group": "Quality & data",
        },
        {
            "id": "ls_sponsor_cro",
            "label": "Sponsor–CRO–site",
            "blurb": "Collaboration & handoffs",
            "group": "Quality & data",
        },
        {
            "id": "ls_real_world",
            "label": "Real-world evidence",
            "blurb": "RWD/RWE, registries",
            "group": "Quality & data",
        },
        # AI & FDE
        {
            "id": "ls_ai_discovery",
            "label": "AI in discovery",
            "blurb": "Targets, screening, ML",
            "group": "AI & FDE",
        },
        {
            "id": "ls_ai_trials",
            "label": "AI in trials",
            "blurb": "Recruitment, protocol design",
            "group": "AI & FDE",
        },
        {
            "id": "ls_ai_medical",
            "label": "Medical & safety AI",
            "blurb": "Lit review, PV assist",
            "group": "AI & FDE",
        },
        {
            "id": "ls_documentation",
            "label": "Documentation culture",
            "blurb": "Traceability for AI work",
            "group": "AI & FDE",
        },
        {
            "id": "ls_deployment",
            "label": "LS deployment risks",
            "blurb": "Validated environments",
            "group": "AI & FDE",
        },
        {
            "id": "ls_fde_playbook",
            "label": "FDE pharma playbook",
            "blurb": "Stakeholder & evidence",
            "group": "AI & FDE",
        },
        {
            "id": "ls_manufacturing",
            "label": "Manufacturing / CMC AI",
            "blurb": "Process, quality, MES",
            "group": "AI & FDE",
        },
        {
            "id": "ls_labeling",
            "label": "Labeling & medical affairs",
            "blurb": "Claims, promo compliance",
            "group": "AI & FDE",
        },
    ],
    "technical": [
        {
            "id": "tech_enterprise_delivery",
            "label": "Enterprise delivery",
            "blurb": "Customer envs & constraints",
            "group": "Foundations",
        },
        {
            "id": "tech_genai_systems",
            "label": "GenAI systems",
            "blurb": "RAG, agents, evals",
            "group": "Foundations",
        },
        {
            "id": "tech_secure_sdlc",
            "label": "Secure SDLC",
            "blurb": "Threats, secrets, supply chain",
            "group": "Foundations",
        },
        {
            "id": "tech_observability",
            "label": "Observability",
            "blurb": "Logs, traces, model monitors",
            "group": "Foundations",
        },
        {
            "id": "tech_integration",
            "label": "HC/LS integration",
            "blurb": "Interop patterns for FDEs",
            "group": "Foundations",
        },
        {
            "id": "tech_production",
            "label": "Production readiness",
            "blurb": "Rollback, SLOs, incident",
            "group": "Foundations",
        },
    ],
}


def topics_for_domain(domain: str) -> list[TopicDef]:
    return list(DOMAIN_TOPICS.get(domain, []))


def resolve_topics(domain: str, selected_ids: list[str] | None) -> list[TopicDef]:
    catalog = {t["id"]: t for t in topics_for_domain(domain)}
    ids = selected_ids or []
    out: list[TopicDef] = []
    for tid in ids:
        if tid in catalog and catalog[tid] not in out:
            out.append(catalog[tid])
    return out


def default_topic_ids(domain: str, limit: int = 6) -> list[str]:
    """Reasonable starter set if learner hasn't chosen yet."""
    return [t["id"] for t in topics_for_domain(domain)[:limit]]
