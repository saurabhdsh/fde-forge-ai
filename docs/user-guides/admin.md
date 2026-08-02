# Admin Guide (Phase 1–2)

1. Sign in as `Saurabh` (org admin) with organization slug `acme-health`.
2. Use **User Management** to create candidates in your organization.
3. Use **Course sources** to upload PDF/DOCX materials that enrich AI domain course generation (tag by Healthcare / Life sciences / Technical / All).
4. Use **Interview readiness** to see who finished MCQ and Coding at ≥70% and is ready for a manual human interview.
5. Use **Audit Logs** to verify login, profile, resume, curriculum, assessment, and plan events.
6. Configure AI: prefer AWS Bedrock on Mac/AWS (`BEDROCK_ENABLED=true`, see `docs/BEDROCK.md`) with OpenAI as fallback (`OPENAI_API_KEY`). Recreate the API container after changing `.env`.
