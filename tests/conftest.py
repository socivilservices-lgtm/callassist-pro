import pytest_asyncio

from src.database import db as dbmod
from src.database.db import Database


@pytest_asyncio.fixture
async def database(monkeypatch):
    d = Database("sqlite+aiosqlite:///:memory:")
    from sqlalchemy.pool import StaticPool
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    d.engine = create_async_engine(d.url, poolclass=StaticPool, connect_args={"check_same_thread": False})
    d._factory = async_sessionmaker(d.engine, expire_on_commit=False)
    await d.create_all()
    monkeypatch.setattr(dbmod, "_db", d)
    yield d
    await d.dispose()
