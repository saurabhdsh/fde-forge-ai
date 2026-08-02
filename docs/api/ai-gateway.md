# AI Gateway

Provider-independent interface:

- `generate_text`
- `generate_structured` (JSON schema / Pydantic validation with retries)
- `generate_embedding`
- `stream_text`

## Operational provider

- **OpenAI** — fully implemented

## Adapter stubs (configuration validation only)

- Azure OpenAI
- Anthropic
- AWS Bedrock
- Google Gemini

Selecting an unconfigured or non-enabled provider returns HTTP 503 with a clear configuration error. No fabricated completions.

## Prompt governance

- Resume extraction: `resume_extraction.v1` (stored on `ai_extraction_records.prompt_version`)
- Baseline assessment: `baseline_assessment.v3` (minimum 25 hard expert-level MCQs)
- Domain super-courses: `domain_course.v1.2` (instructional-design scaffold; persisted on `courses.prompt_version`)
- Coding playground: `coding_playground.v1` (minimum 25 hard Python GenAI/agent challenges + AI rubric grading)

Database-backed prompt versioning tables are planned for Phase 3 content studio.

## Guardrails

- Prompt-injection phrase filtering on inbound resume text
- Hallucination-risk heuristic on structured payloads
- Token and estimated cost tracking persisted with extractions
