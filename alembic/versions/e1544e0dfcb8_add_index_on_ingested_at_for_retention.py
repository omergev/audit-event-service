"""add index on ingested_at for retention

Revision ID: e1544e0dfcb8
Revises: 4d7727316dd2
Create Date: 2025-08-11 22:38:41.892518

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1544e0dfcb8'
down_revision: Union[str, Sequence[str], None] = '4d7727316dd2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
