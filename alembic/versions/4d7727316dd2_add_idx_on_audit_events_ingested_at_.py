"""add idx on audit_events(ingested_at, event_id)

Revision ID: 4d7727316dd2
Revises: 9085549f9274
Create Date: 2025-08-10 15:42:09.110396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d7727316dd2'
down_revision: Union[str, Sequence[str], None] = '9085549f9274'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INDEX_NAME = "idx_audit_events_ingested_at_event_id"
TABLE_NAME = "audit_events"

def upgrade() -> None:
    # Create a composite index to support ORDER BY ingested_at, event_id efficiently.
    # Note:
    # - Using a regular CREATE INDEX here (not CONCURRENTLY) for simplicity in dev.
    # - For very large tables in production, consider doing it CONCURRENTLY with manual DDL.
    op.create_index(
        INDEX_NAME,
        TABLE_NAME,
        ["ingested_at", "event_id"],
        unique=False,
        postgresql_using="btree",
    )


def downgrade() -> None:
    # Drop the composite index if exists.
    op.drop_index(INDEX_NAME, table_name=TABLE_NAME)
