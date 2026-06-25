"""Context issue strategic nature.

Revision ID: f5a6b7c8d913
Revises: e4f5a6b7c812
Create Date: 2026-06-24
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d913"
down_revision: Union[str, None] = "e4f5a6b7c812"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return column in {col["name"] for col in sa.inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "context_issues"):
        return
    if not _column_exists(conn, "context_issues", "nature"):
        op.add_column(
            "context_issues",
            sa.Column(
                "nature",
                sa.Enum(
                    "contextual",
                    "strength",
                    "weakness",
                    "opportunity",
                    "threat",
                    name="issuenature",
                    native_enum=False,
                    length=20,
                ),
                nullable=False,
                server_default="contextual",
            ),
        )
    conn.execute(sa.text("UPDATE context_issues SET nature = 'contextual' WHERE nature IS NULL"))


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "context_issues", "nature"):
        op.drop_column("context_issues", "nature")
