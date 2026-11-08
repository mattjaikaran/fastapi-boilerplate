"""LangGraph runtime configuration.

The recursion limit comes from ``AGENT_MAX_STEPS``; checkpoints are stored in
the application's existing Postgres database. Settings are read lazily so
importing this module needs no environment file.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver


def recursion_limit() -> int:
    """Return the super-step cap for one graph run."""
    from app.config.settings import settings

    return settings.AGENT_MAX_STEPS


def checkpointer_dsn() -> str:
    """Return the app database DSN in the libpq form psycopg expects."""
    from app.config.settings import settings

    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


@asynccontextmanager
async def postgres_checkpointer() -> AsyncIterator[AsyncPostgresSaver]:
    """Yield a Postgres checkpointer, creating its tables if missing.

    The setup step is idempotent, so callers can enter this context per run.
    """
    async with AsyncPostgresSaver.from_conn_string(checkpointer_dsn()) as saver:
        await saver.setup()
        yield saver
