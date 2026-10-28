"""Async database engine / session management (SQLite dev, PostgreSQL prod)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.database.models import Base


class Database:
    """Owns the async engine and session factory."""

    def __init__(self, url: str | None = None) -> None:
        self.url = url or get_settings().database_url
        self.engine: AsyncEngine = create_async_engine(self.url, future=True)
        self._factory = async_sessionmaker(self.engine, expire_on_commit=False)

    async def create_all(self) -> None:
        """Create tables (dev convenience; use Alembic in production)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Yield a session, committing on success and rolling back on error."""
        async with self._factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()


_db: Database | None = None


def get_db() -> Database:
    """Return the process-wide Database instance."""
    global _db
    if _db is None:
        _db = Database()
    return _db
