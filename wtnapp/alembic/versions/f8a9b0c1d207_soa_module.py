"""SoA module — Feature 005: Statement of Applicability (Declaração de Aplicabilidade).

Cria soa, soa_item, soa_item_event (todas com tenant_id + RLS) + gatilho append-only em
soa_item_event. Idempotente: roda mesmo com as tabelas já criadas pelo create_all() do startup.

Revision ID: f8a9b0c1d207
Revises: e7f8a9b0c106
Create Date: 2026-06-21
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "f8a9b0c1d207"
down_revision = "e7f8a9b0c106"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def upgrade() -> None:
    conn = op.get_bind()

    if not _table_exists(conn, "soa"):
        op.create_table(
            "soa",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("gap_assessment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment.id"), nullable=True),
            sa.Column("draft_status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uq_soa_tenant"),
        )
        op.create_index("ix_soa_tenant_id", "soa", ["tenant_id"])

    if not _table_exists(conn, "soa_item"):
        op.create_table(
            "soa_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("soa_id", sa.Uuid(as_uuid=True), sa.ForeignKey("soa.id"), nullable=False),
            sa.Column("catalog_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_catalog_item.id"), nullable=False),
            sa.Column("gap_assessment_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment_item.id"), nullable=True),
            sa.Column("ref_code", sa.String(20), nullable=False),
            sa.Column("theme", sa.String(20), nullable=True),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("applicable", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("inclusion_reasons", sa.JSON(), nullable=False),
            sa.Column("inclusion_note", sa.Text(), nullable=True),
            sa.Column("exclusion_justification", sa.Text(), nullable=True),
            sa.Column("implementation_status", sa.String(20), nullable=True),
            sa.Column("responsible", sa.String(200), nullable=True),
            sa.Column("deadline", sa.Date(), nullable=True),
            sa.Column("risks_treated", sa.Text(), nullable=True),
            sa.Column("expected_evidence", sa.Text(), nullable=True),
            sa.Column("evidence_refs", sa.Text(), nullable=True),
            sa.Column("observations", sa.Text(), nullable=True),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("soa_id", "catalog_item_id", name="uq_soa_item_catalog"),
        )
        op.create_index("ix_soa_item_tenant_id", "soa_item", ["tenant_id"])
        op.create_index("ix_soa_item_soa_id", "soa_item", ["soa_id"])

    if not _table_exists(conn, "soa_item_event"):
        op.create_table(
            "soa_item_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("soa_item.id"), nullable=False),
            sa.Column("field", sa.String(40), nullable=False),
            sa.Column("old_value", sa.String(120), nullable=True),
            sa.Column("new_value", sa.String(120), nullable=True),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_soa_item_event_tenant_id", "soa_item_event", ["tenant_id"])
        op.create_index("ix_soa_item_event_item_id", "soa_item_event", ["item_id"])

    # RLS + gatilho append-only (PostgreSQL only — idempotente)
    if conn.dialect.name == "postgresql":
        for table in ("soa", "soa_item", "soa_item_event"):
            conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
            conn.execute(sa.text(
                f"CREATE POLICY {table}_tenant_isolation ON {table} "
                f"USING (tenant_id::text = current_setting('app.tenant_id', true))"
            ))
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_soa_item_event_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'soa_item_event is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS soa_item_event_append_only ON soa_item_event"))
        conn.execute(sa.text("""
            CREATE TRIGGER soa_item_event_append_only
            BEFORE UPDATE OR DELETE ON soa_item_event
            FOR EACH ROW EXECUTE FUNCTION wtn_soa_item_event_append_only();
        """))

    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS soa_item_event_no_update BEFORE UPDATE ON soa_item_event "
            "BEGIN SELECT RAISE(ABORT, 'soa_item_event is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS soa_item_event_no_delete BEFORE DELETE ON soa_item_event "
            "BEGIN SELECT RAISE(ABORT, 'soa_item_event is append-only'); END;"
        ))


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS soa_item_event_append_only ON soa_item_event"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_soa_item_event_append_only()"))

    op.drop_table("soa_item_event")
    op.drop_table("soa_item")
    op.drop_table("soa")
