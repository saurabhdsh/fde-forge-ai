"""DB column types that work on PostgreSQL (Docker/EC2) and SQLite (TCS Mac)."""

from __future__ import annotations

from sqlalchemy import JSON, Uuid

# Prefer portable SQLAlchemy 2 types over postgresql.UUID / JSONB
GUID = Uuid(as_uuid=True)
JSONType = JSON
