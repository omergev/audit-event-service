"""add idx on audit_events(ingested_at, event_id)

Revision ID: 4d7727316dd2
Revises: 9085549f9274
Create Date: 2025-08-10 15:42:09.110396

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4d7727316dd2'
down_revision = '9085549f9274'
branch_labels = None
depends_on = None

INDEX_NAME = "idx_audit_events_ingested_at"
TABLE_NAME = "audit_events"

def upgrade() -> None:
    """Create a btree index on ingested_at for efficient retention deletes and ordering."""
    # Safety: create only if not exists (Alembic lacks a built-in flag, so use raw SQL for Postgres).
    conn = op.get_bind()
    conn.execute(
        sa.text(
            f"CREATE INDEX IF NOT EXISTS {INDEX_NAME} ON {TABLE_NAME} USING btree (ingested_at)"
        )
    )


def downgrade() -> None:
    # Drop the composite index if exists.
    conn = op.get_bind()
    conn.execute(
        sa.text(
            f"DROP INDEX IF EXISTS {INDEX_NAME}"
        )
    )
