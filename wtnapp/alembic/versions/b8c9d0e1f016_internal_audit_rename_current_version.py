"""Auditoria Interna — renomeia internal_audit.current_report_version_id → current_version_id.

Auto-correção: bancos que criaram `internal_audit` via `create_all()` ANTES do rename (commit do
domínio de auditoria) ficaram com a coluna antiga `current_report_version_id`; como a migration
`a7b8c9d0e015` é idempotente (`_table_exists`), ela pulou o `create_table` e a coluna não foi
renomeada. Esta migration renomeia a coluna quando aplicável. **No-op** em bancos novos (já criados
com `current_version_id`) ou já corrigidos.

Revision ID: b8c9d0e1f016
Revises: a7b8c9d0e015
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b8c9d0e1f016"
down_revision: Union[str, None] = "a7b8c9d0e015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(conn, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table)}


def upgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("internal_audit"):
        return
    cols = _columns(conn, "internal_audit")
    if "current_report_version_id" in cols and "current_version_id" not in cols:
        op.alter_column("internal_audit", "current_report_version_id", new_column_name="current_version_id")


def downgrade() -> None:
    conn = op.get_bind()
    if not sa.inspect(conn).has_table("internal_audit"):
        return
    cols = _columns(conn, "internal_audit")
    if "current_version_id" in cols and "current_report_version_id" not in cols:
        op.alter_column("internal_audit", "current_version_id", new_column_name="current_report_version_id")
