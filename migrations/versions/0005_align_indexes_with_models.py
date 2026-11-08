"""align 0001/0002 unique constraints and index names with the models

0001/0002 created `UNIQUE` constraints plus plain indexes. The models declare
`unique=True, index=True`, which is a single unique index. Databases built by
`Base.metadata.create_all` already have the model shape and must be stamped
at head instead of running this migration.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-08 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column, unique constraint name created by 0001/0002, index name)
_UNIQUE_INDEXES: list[tuple[str, str, str, str]] = [
    ("api_keys", "key_hash", "api_keys_key_hash_key", "ix_api_keys_key_hash"),
    (
        "background_jobs",
        "celery_task_id",
        "background_jobs_celery_task_id_key",
        "ix_background_jobs_celery_task_id",
    ),
    (
        "billing_customers",
        "stripe_customer_id",
        "billing_customers_stripe_customer_id_key",
        "ix_billing_customers_stripe_customer_id",
    ),
    (
        "billing_customers",
        "user_id",
        "billing_customers_user_id_key",
        "ix_billing_customers_user_id",
    ),
    ("feature_flags", "key", "feature_flags_key_key", "ix_feature_flags_key"),
    ("organizations", "slug", "organizations_slug_key", "ix_organizations_slug"),
    (
        "subscriptions",
        "stripe_subscription_id",
        "subscriptions_stripe_subscription_id_key",
        "ix_subscriptions_stripe_subscription_id",
    ),
]

# (old name, new name)
_RENAMED_INDEXES: list[tuple[str, str]] = [
    ("ix_org_members_organization_id", "ix_organization_members_organization_id"),
    ("ix_org_members_user_id", "ix_organization_members_user_id"),
]


def upgrade() -> None:
    for table, column, constraint, index in _UNIQUE_INDEXES:
        op.execute(f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"')
        op.drop_index(index, table_name=table)
        op.create_index(index, table, [column], unique=True)

    for old, new in _RENAMED_INDEXES:
        op.execute(f'ALTER INDEX IF EXISTS "{old}" RENAME TO "{new}"')

    op.drop_index("ix_notifications_read_at", table_name="notifications")


def downgrade() -> None:
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])

    for old, new in _RENAMED_INDEXES:
        op.execute(f'ALTER INDEX IF EXISTS "{new}" RENAME TO "{old}"')

    for table, column, constraint, index in reversed(_UNIQUE_INDEXES):
        op.drop_index(index, table_name=table)
        op.create_index(index, table, [column])
        op.create_unique_constraint(constraint, table, [column])
