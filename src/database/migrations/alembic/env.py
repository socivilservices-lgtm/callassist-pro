"""Alembic environment (uses a sync driver derived from the app's async URL)."""
from alembic import context
from sqlalchemy import create_engine

from src.config import get_settings
from src.database.models import Base

target_metadata = Base.metadata


def _sync_url() -> str:
    return (
        get_settings().database_url
        .replace("+aiosqlite", "")
        .replace("+asyncpg", "+psycopg2")
    )


def run_migrations_online() -> None:
    engine = create_engine(_sync_url())
    with engine.connect() as conn:
        context.configure(connection=conn, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_offline() -> None:
    context.configure(url=_sync_url(), target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
