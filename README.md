# FDE Forge AI

**Transform AI Engineers into Customer-Ready Forward Deployed Engineers.**

Enterprise AI-powered Forward Deployed Engineer training platform. Phase 1 delivers a working vertical slice: multi-tenant authentication, RBAC, organization management, audit logging, learner onboarding, resume upload to object storage, real document text extraction, OpenAI structured skill extraction, learner confirmation, and skill profile persistence.

## Quick start

### One command (recommended)

```bash
cd fde-forge-ai
chmod +x setup.sh scripts/stop.sh
./setup.sh
```

| Machine | What `setup.sh` does |
|---------|----------------------|
| **TCS Mac (no Docker)** | Like Knowledge Fabric: **SQLite** + local uploads + npm + Python venv + **Bedrock**. No Homebrew/Postgres/Redis/MinIO. |
| **AWS EC2 (Docker)** | `docker compose up --build -d --scale worker=2` with Bedrock via instance IAM role. |

After native setup you also get:
- `./start_all.sh` — start API + web
- `./start_backend.sh` / `./start_frontend.sh`
- `./scripts/stop.sh` — stop background processes

Stop Docker: `docker compose down`

Force a mode: `FORCE_MODE=native ./setup.sh` or `FORCE_MODE=docker ./setup.sh`  
EC2 workers: `WORKER_REPLICAS=4 ./setup.sh`

### Manual Docker

```bash
cp .env.example .env
# Set OPENAI_API_KEY (fallback) and/or enable Bedrock — see docs/BEDROCK.md
docker compose up --build
```

Services:

| Service    | URL                         |
|------------|-----------------------------|
| Web UI     | http://localhost:5173       |
| API docs   | http://localhost:8000/docs  |
| MinIO      | http://localhost:9001       |
| MailHog    | http://localhost:8025       |
| Grafana    | http://localhost:3001       |
| Prometheus | http://localhost:9090       |

### Demonstration credentials (development only)

| Role                 | Email                         | Password              |
|----------------------|-------------------------------|-----------------------|
| Platform / Org Admin | `admin@fdeforge.example.com`        | `admin123`   |
| Academy Admin        | `academy.admin@fdeforge.example.com`| `admin123`   |
| Mentor               | `mentor@fdeforge.example.com`       | `admin123`   |
| Evaluator            | `evaluator@fdeforge.example.com`    | `admin123`   |
| Learners             | `learner1@fdeforge.example.com` … `learner3@` | `ChangeMeLearner123!` |

Organization slug: `acme-health`

## Phase 1 acceptance path

1. `docker compose up --build`
2. Sign in as `admin@fdeforge.example.com` / `admin123` with organization `acme-health`
3. Create or use a learner under **Users**
4. Sign in as learner (e.g. `learner1@fdeforge.example.com`)
5. Open **Onboarding**, complete profile and consents
6. Upload a real PDF or DOCX resume
7. Confirm file stored in MinIO, text extracted, OpenAI returns schema-validated skills
8. Edit and confirm skills
9. View **Skills** profile (PostgreSQL-backed)
10. As admin, verify **Audit Logs**
11. Restart stack (`docker compose restart`) and confirm data remains

Without `OPENAI_API_KEY`, resume upload still stores the file and extracts text; AI extraction returns a clear configuration error (never fabricated skills).

## Makefile

```bash
make up        # docker compose up --build -d
make down
make migrate
make seed
make test
make lint
make format
```

## Repository layout

See `docs/architecture/` for design documents. Monorepo structure:

- `apps/web` — React 19 + Vite + MUI
- `apps/api` — FastAPI + SQLAlchemy + Alembic
- `apps/worker` — Celery worker packaging
- `packages/` — shared packages (prompts, taxonomy, config)
- `infrastructure/` — Docker, K8s, Helm, Terraform, monitoring
- `scripts/seed.py` — idempotent demonstration seed

## Documentation

- [Local setup](docs/deployment/local-setup.md)
- [Architecture](docs/architecture/overview.md)
- [Assumptions](docs/architecture/assumptions.md)
- [Deferred capabilities](docs/architecture/deferred-capabilities.md)
- [Security model](docs/security/security-model.md)
- [Multi-tenancy](docs/architecture/multi-tenancy.md)
- [AI gateway](docs/api/ai-gateway.md)
- [Healthcare governance](docs/domain/healthcare-governance.md)
- [Life Sciences governance](docs/domain/life-sciences-governance.md)
- [Learner guide](docs/user-guides/learner.md)
- [Admin guide](docs/user-guides/admin.md)

## Phased roadmap

| Phase | Focus |
|-------|--------|
| 1 | Auth, RBAC, orgs, audit, learner profile, resume AI extraction |
| 2 (current) | Assessments, learning plans, domain courses (gate before assessment), learner + admin dashboards |
| 3 | Curriculum, AI content studio, knowledge fabric, copilot |
| 4 | Coding labs, architecture studio, simulations, projects |
| 5 | Readiness engine, certification, deployment matching, leadership analytics |

## License

Proprietary — all rights reserved.
