# Architecture Overview

```mermaid
flowchart LR
  Web[React Web] -->|HTTPS cookies| API[FastAPI]
  API --> PG[(PostgreSQL + pgvector)]
  API --> Redis[(Redis)]
  API --> MinIO[(MinIO / S3)]
  API --> OpenAI[OpenAI API]
  Worker[Celery Worker] --> Redis
  Worker --> PG
  Worker --> MinIO
```

## Layering

- **API routes** — thin HTTP adapters under `app/api/v1/routes`
- **Services** — business logic (`app/services`)
- **Repositories** — persistence (`app/repositories`)
- **AI gateway** — provider-independent interface (`app/ai`)
- **Domain** — permissions and taxonomy constants (`app/domain`)

## Multi-tenancy

Every enterprise-owned row includes `organization_id`. Services and repositories filter by the authenticated user's organization. Cross-tenant access is denied unless the actor is a platform super admin for specific operations.

## Auth

- Argon2 password hashing
- Short-lived JWT access tokens in HttpOnly cookies
- Rotating refresh tokens (hashed at rest)
- CSRF token for cookie-authenticated mutating requests
- Failed-login tracking and temporary lockout

## Phase 1 data flow (resume → skills)

```mermaid
sequenceDiagram
  participant L as Learner
  participant W as Web
  participant A as API
  participant S as MinIO
  participant O as OpenAI
  participant D as PostgreSQL

  L->>W: Upload resume
  W->>A: POST /learners/me/resume
  A->>S: Store object
  A->>A: Extract text (PyMuPDF/docx)
  A->>O: Structured extraction
  O-->>A: JSON skills
  A->>D: Persist extraction record
  A-->>W: Validated payload
  L->>W: Edit + confirm
  W->>A: POST .../confirm
  A->>D: learner_skills + audit
```
