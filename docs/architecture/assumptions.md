# Architecture Assumptions

1. **Primary AI provider for Phase 1** is OpenAI via `OPENAI_API_KEY`. Other providers have adapter interfaces and fail with configuration errors when selected.
2. **Local authentication** (email/password + Argon2 + JWT cookies) is the only complete IdP in Phase 1. Entra ID / Google / SAML / OIDC are documented extension points, not mocked.
3. **Resume AI extraction runs inline** in the API request for the Phase 1 acceptance path. Celery task stubs exist for moving this work fully async in later phases.
4. **System roles** are seeded globally (`organization_id = NULL`) and shared across tenants. Per-tenant custom roles can be added later.
5. **Skills taxonomy** is global for Phase 1; organization-specific skill overlays are supported by the schema (`skills.organization_id`) but not exposed in the UI yet.
6. **MinIO** is used as the S3-compatible store in local/dev. Production should use managed S3 or equivalent.
7. **PostgreSQL 16 + pgvector** is the system of record and initial vector store. Vector embeddings for knowledge fabric are deferred to Phase 3.
8. **Branding** is configurable via env (`APP_NAME`, `APP_TAGLINE`) and `organizations.branding` JSON.
9. **Demo seed passwords** are for development only and must never be used in production configuration.
10. **Healthcare and Life Sciences content** in later phases is educational training material, not medical, legal, or regulatory advice.
