"""Ensure print preview snapshot columns.

Revision ID: e3f4a5b6c711
Revises: d2e3f4a5b610
Create Date: 2026-06-23
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3f4a5b6c711"
down_revision: Union[str, None] = "d2e3f4a5b610"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return column in {col["name"] for col in sa.inspect(conn).get_columns(table)}


def _json_default(conn: sa.engine.Connection) -> sa.TextClause:
    if conn.dialect.name == "postgresql":
        return sa.text("'{}'::json")
    return sa.text("'{}'")


def _add_json_column_if_missing(conn: sa.engine.Connection, table: str, column: str) -> None:
    if _column_exists(conn, table, column):
        return
    op.add_column(
        table,
        sa.Column(column, sa.JSON(), nullable=False, server_default=_json_default(conn)),
    )
    op.alter_column(table, column, server_default=None)


def _drop_column_if_exists(conn: sa.engine.Connection, table: str, column: str) -> None:
    if _column_exists(conn, table, column):
        op.drop_column(table, column)


def upgrade() -> None:
    conn = op.get_bind()
    _add_json_column_if_missing(conn, "document_previews", "snapshot_json")
    _add_json_column_if_missing(conn, "document_previews", "rendered_variables")
    _add_json_column_if_missing(conn, "signed_document_snapshots", "snapshot_json")
    _add_json_column_if_missing(conn, "signed_document_snapshots", "rendered_variables")


def downgrade() -> None:
    conn = op.get_bind()
    _drop_column_if_exists(conn, "signed_document_snapshots", "rendered_variables")
    _drop_column_if_exists(conn, "signed_document_snapshots", "snapshot_json")
    _drop_column_if_exists(conn, "document_previews", "rendered_variables")
    _drop_column_if_exists(conn, "document_previews", "snapshot_json")
