"""Add composite index on (ingested_at, event_id)

Revision ID: 68b6975b4233
Revises: e1544e0dfcb8
Create Date: 2025-08-12 23:23:06.152018

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68b6975b4233'
down_revision: Union[str, Sequence[str], None] = 'e1544e0dfcb8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # Ensure idempotency: drop the single-column index if present, then
    # create the composite index only if it does not already exist
    # (checking both legacy and new names).
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename  = 'audit_events'
              AND indexname  = 'ix_audit_events_ingested_at'
        ) THEN
            EXECUTE 'DROP INDEX IF EXISTS ix_audit_events_ingested_at';
        END IF;

        IF NOT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename  = 'audit_events'
              AND indexname IN (
                  'ix_audit_events_ingested_at_event_id',
                  'idx_audit_events_ingested_at_event_id'
              )
        ) THEN
            EXECUTE 'CREATE INDEX idx_audit_events_ingested_at_event_id ON public.audit_events (ingested_at, event_id)';
        END IF;
    END
    $$;
    """)

def downgrade() -> None:
    # Recreate the single-column index only if the composite one existed,
    # and drop the composite index if present.
    op.execute("""
    DO $$
    BEGIN
        IF EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename  = 'audit_events'
              AND indexname IN (
                  'ix_audit_events_ingested_at_event_id',
                  'idx_audit_events_ingested_at_event_id'
              )
        ) THEN
            -- Drop composite index (handle either name)
            IF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'audit_events'
                  AND indexname  = 'ix_audit_events_ingested_at_event_id'
            ) THEN
                EXECUTE 'DROP INDEX ix_audit_events_ingested_at_event_id';
            ELSIF EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'audit_events'
                  AND indexname  = 'idx_audit_events_ingested_at_event_id'
            ) THEN
                EXECUTE 'DROP INDEX idx_audit_events_ingested_at_event_id';
            END IF;

            -- Restore single-column index (only if it does not exist)
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname = 'public'
                  AND tablename  = 'audit_events'
                  AND indexname  = 'ix_audit_events_ingested_at'
            ) THEN
                EXECUTE 'CREATE INDEX ix_audit_events_ingested_at ON public.audit_events (ingested_at)';
            END IF;
        END IF;
    END
    $$;
    """)

