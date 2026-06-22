"""backfill gap guidance seed

Revision ID: 84c5c822d7b1
Revises: a9b0c1d2e308
Create Date: 2026-06-22 11:31:22.658859
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy.orm import Session


revision: str = '84c5c822d7b1'
down_revision: Union[str, None] = 'a9b0c1d2e308'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Populate Feature 007 guidance fields and global legend for existing databases."""
    from wtnapp.services.gap_seed_service import load_seed

    bind = op.get_bind()
    session = Session(bind=bind)
    try:
        load_seed(session)
        session.flush()
    finally:
        session.close()


def downgrade() -> None:
    # Data backfill is intentionally not reverted: platform guidance can be edited after upgrade.
    pass
