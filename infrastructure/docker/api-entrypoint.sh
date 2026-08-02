#!/bin/sh
set -e

echo "Waiting for database..."
python - <<'PY'
import time
import sys
from sqlalchemy import create_engine, text
from app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
for i in range(60):
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("Database ready")
        sys.exit(0)
    except Exception as exc:
        print(f"DB not ready ({i}): {exc}")
        time.sleep(1)
sys.exit(1)
PY

echo "Running migrations..."
alembic -c /app/apps/api/alembic.ini upgrade head

echo "Seeding demonstration data (idempotent)..."
python -m scripts.seed || true

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
