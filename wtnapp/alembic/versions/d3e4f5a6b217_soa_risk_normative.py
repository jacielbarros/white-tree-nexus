"""SoA Normativa (Feature 013) — coluna risk_links em soa_item.

Adiciona `soa_item.risk_links` (JSON) — projeção estruturada dos riscos tratados vinda do soa-feed
(Feature 012). Idempotente: o `create_all()` do startup pode já ter criado a coluna em DB zerado;
em tabela preexistente, a coluna é adicionada com guarda de coluna + backfill.

Revision ID: d3e4f5a6b217
Revises: c2d3e4f5a116
Create Date: 2026-06-29
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "d3e4f5a6b217"
down_revision = "c2d3e4f5a116"
branch_labels = None
depends_on = None


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    return column in [c["name"] for c in sa.inspect(conn).get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "soa_item", "risk_links"):
        op.add_column(
            "soa_item",
            sa.Column("risk_links", sa.JSON(), nullable=False, server_default="[]"),
        )
    # Backfill idempotente (cobre linhas preexistentes / server_default ausente).
    op.execute("UPDATE soa_item SET risk_links = '[]' WHERE risk_links IS NULL")


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "soa_item", "risk_links"):
        op.drop_column("soa_item", "risk_links")
