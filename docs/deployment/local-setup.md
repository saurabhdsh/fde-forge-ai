# Local Setup

## Prerequisites

- Docker + Docker Compose
- Optional: Python 3.12, Node 22 for local (non-container) development

## Steps

```bash
cp .env.example .env
# Edit OPENAI_API_KEY
docker compose up --build
```

Migrations and seed run automatically on API container start.

## Manual migrate / seed

```bash
make migrate
make seed
```

## Local API without Docker app containers

```bash
docker compose up -d postgres redis minio mailhog
cd apps/api && python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
export $(grep -v '^#' ../../.env | xargs)
# Point DATABASE_URL to localhost
uvicorn app.main:app --reload
```

## Tests

```bash
# Unit tests that do not need DB
cd apps/api && pytest tests/test_security.py tests/test_resume_schema.py tests/test_document_extraction.py tests/test_permissions.py -q
```
