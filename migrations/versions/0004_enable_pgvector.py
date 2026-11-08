"""enable pgvector extension

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-08 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Guarded so the migration is a no-op on images without the vector extension
    # (for example the default postgres:17-alpine container).
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM pg_available_extensions WHERE name = 'vector'
                ) THEN
                    CREATE EXTENSION IF NOT EXISTS vector;
                END IF;
            END
            $$;
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP EXTENSION IF EXISTS vector"))
