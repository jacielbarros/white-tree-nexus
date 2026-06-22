"""Gap guidance — Feature 007: orientação de avaliação por item + legenda global.

Adiciona colunas de orientação a gap_seed_item (referencia, como_avaliar, evidencias_esperadas,
nota) e cria gap_legend_entry e gap_guidance_event (todas PLATFORM-level, sem tenant_id, sem RLS —
mesma natureza do catálogo-base do Gap). gap_guidance_event é append-only (gatilho UPDATE/DELETE).
Idempotente: roda mesmo com colunas/tabelas já criadas pelo create_all() do startup.

Revision ID: a9b0c1d2e308
Revises: f8a9b0c1d207
Create Date: 2026-06-22
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a9b0c1d2e308"
down_revision = "f8a9b0c1d207"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    return column in [c["name"] for c in sa.inspect(conn).get_columns(table)]


def upgrade() -> None:
    conn = op.get_bind()

    # --- Colunas de orientação em gap_seed_item (guardadas por existência) ---
    if _table_exists(conn, "gap_seed_item"):
        if not _column_exists(conn, "gap_seed_item", "referencia"):
            op.add_column("gap_seed_item", sa.Column("referencia", sa.String(120), nullable=False, server_default=""))
        if not _column_exists(conn, "gap_seed_item", "como_avaliar"):
            op.add_column("gap_seed_item", sa.Column("como_avaliar", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        if not _column_exists(conn, "gap_seed_item", "evidencias_esperadas"):
            op.add_column("gap_seed_item", sa.Column("evidencias_esperadas", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
        if not _column_exists(conn, "gap_seed_item", "nota"):
            op.add_column("gap_seed_item", sa.Column("nota", sa.Text(), nullable=True))

    # --- Legenda global (platform-level, sem tenant_id) ---
    if not _table_exists(conn, "gap_legend_entry"):
        op.create_table(
            "gap_legend_entry",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("kind", sa.String(10), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("label", sa.String(60), nullable=False),
            sa.Column("definition", sa.Text(), nullable=False, server_default=""),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("kind", "code", name="uq_gap_legend_kind_code"),
        )

    # --- Trilha append-only (platform-level, sem tenant_id) ---
    if not _table_exists(conn, "gap_guidance_event"):
        op.create_table(
            "gap_guidance_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("target_type", sa.String(20), nullable=False),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("field", sa.String(40), nullable=False),
            sa.Column("old_value", sa.Text(), nullable=True),
            sa.Column("new_value", sa.Text(), nullable=True),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_gap_guidance_event_target", "gap_guidance_event", ["target_type", "target_id"])

    # --- Append-only trigger (idempotente) ---
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_gap_guidance_event_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'gap_guidance_event is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_guidance_event_append_only ON gap_guidance_event"))
        conn.execute(sa.text("""
            CREATE TRIGGER gap_guidance_event_append_only
            BEFORE UPDATE OR DELETE ON gap_guidance_event
            FOR EACH ROW EXECUTE FUNCTION wtn_gap_guidance_event_append_only();
        """))

    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_guidance_event_no_update BEFORE UPDATE ON gap_guidance_event "
            "BEGIN SELECT RAISE(ABORT, 'gap_guidance_event is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_guidance_event_no_delete BEFORE DELETE ON gap_guidance_event "
            "BEGIN SELECT RAISE(ABORT, 'gap_guidance_event is append-only'); END;"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_guidance_event_append_only ON gap_guidance_event"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_gap_guidance_event_append_only()"))

    op.drop_table("gap_guidance_event")
    op.drop_table("gap_legend_entry")
    for col in ("nota", "evidencias_esperadas", "como_avaliar", "referencia"):
        op.drop_column("gap_seed_item", col)
