"""SQLAlchemy async engine and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


settings = get_settings()

_engine_kwargs: dict = {
    "echo": settings.app_env == "development",
}

if settings.is_sqlite:
    # SQLite (TCS Mac native): single-file DB, no connection pooling
    _engine_kwargs.update(
        {
            "connect_args": {"check_same_thread": False},
            "poolclass": NullPool,
        }
    )
else:
    _engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_size": 10,
            "max_overflow": 20,
        }
    )

engine = create_async_engine(settings.database_url, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
