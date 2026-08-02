.PHONY: help install dev test lint format migrate seed down up build logs clean

help:
	@echo "FDE Forge AI — common targets"
	@echo "  make install   Install local deps (API + web)"
	@echo "  make up        Start Docker Compose stack"
	@echo "  make down      Stop stack"
	@echo "  make migrate   Run Alembic migrations"
	@echo "  make seed      Seed demonstration data"
	@echo "  make test      Run backend + frontend unit tests"
	@echo "  make lint      Lint backend and frontend"
	@echo "  make format    Format backend and frontend"
	@echo "  make dev       Start API + web locally (infra via compose)"
	@echo "  make logs      Tail compose logs"

install:
	cd apps/api && python3.12 -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
	cd apps/web && npm install

up:
	docker compose up --build -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

migrate:
	docker compose exec api alembic -c /app/apps/api/alembic.ini upgrade head

seed:
	docker compose exec api python -m scripts.seed

dev:
	docker compose up -d postgres redis minio mailhog
	@echo "Start API: cd apps/api && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000"
	@echo "Start Web: cd apps/web && npm run dev"
	@echo "Start Worker: cd apps/api && source .venv/bin/activate && celery -A app.worker.celery_app worker -l info"

test:
	cd apps/api && . .venv/bin/activate && pytest -q
	cd apps/web && npm test -- --run

lint:
	cd apps/api && . .venv/bin/activate && ruff check app tests && mypy app
	cd apps/web && npm run lint

format:
	cd apps/api && . .venv/bin/activate && ruff check --fix app tests && black app tests
	cd apps/web && npm run format

clean:
	docker compose down -v
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
