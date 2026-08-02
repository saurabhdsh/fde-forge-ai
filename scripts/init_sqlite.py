"""Initialize SQLite schema for TCS Mac (no Alembic / Postgres extensions)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
sys.path.insert(0, str(ROOT))

from app.core.database import Base, engine  # noqa: E402
from app.models import *  # noqa: E402,F401,F403


async def main() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("SQLite schema ready")


if __name__ == "__main__":
    asyncio.run(main())
