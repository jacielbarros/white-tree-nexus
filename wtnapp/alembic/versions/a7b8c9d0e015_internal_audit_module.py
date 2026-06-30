"""Auditoria Interna (Feature 014, Fase 2) — domínio internal_audit_*.

Cria programa/auditoria/checklist/constatação/evento, com RLS e trigger append-only em
`internal_audit_event`. Idempotente. `down_revision="f6a7b8c9d014"` (evidência transversal).

Revision ID: a7b8c9d0e015
Revises: f6a7b8c9d014
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a7b8c9d0e015"
down_revision: Union[str, None] = "f6a7b8c9d014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED = (
    "internal_audit_program", "internal_audit", "internal_audit_checklist_item",
    "internal_audit_finding", "internal_audit_event",
)


def _table_exists(conn, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _idx(conn, name, table, cols):
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, cols)


def _create_tables(conn) -> None:
    if not _table_exists(conn, "internal_audit_program"):
        op.create_table(
            "internal_audit_program",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("objective", sa.Text(), nullable=True),
            sa.Column("period_start", sa.Date(), nullable=True),
            sa.Column("period_end", sa.Date(), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "internal_audit"):
        op.create_table(
            "internal_audit",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("program_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit_program.id"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("scope", sa.Text(), nullable=False),
            sa.Column("criteria", sa.Text(), nullable=False),
            sa.Column("auditor_member_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("period_start", sa.Date(), nullable=True),
            sa.Column("period_end", sa.Date(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("draft_status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_internal_audit_code"),
        )
    if not _table_exists(conn, "internal_audit_checklist_item"):
        op.create_table(
            "internal_audit_checklist_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("audit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit.id"), nullable=False),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("criterion", sa.Text(), nullable=False),
            sa.Column("result", sa.String(20), nullable=False, server_default="pendente"),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "internal_audit_finding"):
        op.create_table(
            "internal_audit_finding",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("audit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit.id"), nullable=False),
            sa.Column("checklist_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit_checklist_item.id"), nullable=True),
            sa.Column("finding_type", sa.String(30), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("promotable", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("nonconformity_ref", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "internal_audit_event"):
        op.create_table(
            "internal_audit_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("audit_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit.id"), nullable=True),
            sa.Column("entity_type", sa.String(30), nullable=False),
            sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )


def _create_indexes(conn) -> None:
    _idx(conn, "ix_internal_audit_program_tenant_id", "internal_audit_program", ["tenant_id"])
    _idx(conn, "ix_internal_audit_tenant_id", "internal_audit", ["tenant_id"])
    _idx(conn, "ix_internal_audit_program_id", "internal_audit", ["program_id"])
    _idx(conn, "ix_internal_audit_status", "internal_audit", ["status"])
    _idx(conn, "ix_internal_audit_checklist_tenant_id", "internal_audit_checklist_item", ["tenant_id"])
    _idx(conn, "ix_internal_audit_checklist_audit_id", "internal_audit_checklist_item", ["audit_id"])
    _idx(conn, "ix_internal_audit_checklist_target", "internal_audit_checklist_item", ["target_type", "target_id"])
    _idx(conn, "ix_internal_audit_finding_tenant_id", "internal_audit_finding", ["tenant_id"])
    _idx(conn, "ix_internal_audit_finding_audit_id", "internal_audit_finding", ["audit_id"])
    _idx(conn, "ix_internal_audit_finding_type", "internal_audit_finding", ["finding_type"])
    _idx(conn, "ix_internal_audit_finding_target", "internal_audit_finding", ["target_type", "target_id"])
    _idx(conn, "ix_internal_audit_finding_promotable", "internal_audit_finding", ["promotable"])
    _idx(conn, "ix_internal_audit_event_tenant_id", "internal_audit_event", ["tenant_id"])
    _idx(conn, "ix_internal_audit_event_audit_id", "internal_audit_event", ["audit_id"])
    _idx(conn, "ix_internal_audit_event_type", "internal_audit_event", ["event_type"])


def _append_only(conn) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text(
            "CREATE OR REPLACE FUNCTION wtn_internal_audit_event_append_only() RETURNS trigger "
            "LANGUAGE plpgsql AS $$ BEGIN IF TG_OP IN ('UPDATE','DELETE') THEN "
            "RAISE EXCEPTION 'internal_audit_event is append-only'; END IF; RETURN NEW; END; $$;"
        ))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS internal_audit_event_append_only ON internal_audit_event"))
        conn.execute(sa.text(
            "CREATE TRIGGER internal_audit_event_append_only BEFORE UPDATE OR DELETE ON internal_audit_event "
            "FOR EACH ROW EXECUTE FUNCTION wtn_internal_audit_event_append_only();"
        ))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS internal_audit_event_no_update BEFORE UPDATE ON internal_audit_event "
            "BEGIN SELECT RAISE(ABORT, 'internal_audit_event is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS internal_audit_event_no_delete BEFORE DELETE ON internal_audit_event "
            "BEGIN SELECT RAISE(ABORT, 'internal_audit_event is append-only'); END;"
        ))


def _create_rls(conn) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table in _SCOPED:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
        conn.execute(sa.text(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
        ))


def upgrade() -> None:
    conn = op.get_bind()
    _create_tables(conn)
    _create_indexes(conn)
    _append_only(conn)
    _create_rls(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for table in _SCOPED:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
            conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS internal_audit_event_append_only ON internal_audit_event"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_internal_audit_event_append_only()"))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS internal_audit_event_no_update;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS internal_audit_event_no_delete;"))
    op.drop_table("internal_audit_event")
    op.drop_table("internal_audit_finding")
    op.drop_table("internal_audit_checklist_item")
    op.drop_table("internal_audit")
    op.drop_table("internal_audit_program")
