"""NC/Ações Corretivas (10.2) + Análise Crítica (9.3) + Melhoria/PDCA (10.1) — Feature 015 / 5b.

Cria 7 tabelas (`nonconformity`, `corrective_action`, `nonconformity_verification`,
`nonconformity_event`, `management_review`, `improvement`, `improvement_event`), com RLS e triggers
append-only em `nonconformity_event`/`improvement_event`. Idempotente. **Não** altera tabelas da 5a
(o `internal_audit_finding.nonconformity_ref` já existe; a escrita é em runtime, na promoção).

Revision ID: c9d0e1f2a017
Revises: b8c9d0e1f016
Create Date: 2026-06-30
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c9d0e1f2a017"
down_revision: Union[str, None] = "b8c9d0e1f016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED = (
    "nonconformity", "corrective_action", "nonconformity_verification", "nonconformity_event",
    "management_review", "improvement", "improvement_event",
)
_APPEND_ONLY = ("nonconformity_event", "improvement_event")


def _table_exists(conn, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _idx(conn, name, table, cols):
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, cols)


def _create_tables(conn) -> None:
    if not _table_exists(conn, "nonconformity"):
        op.create_table(
            "nonconformity",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("origin", sa.String(30), nullable=False),
            sa.Column("source_finding_id", sa.Uuid(as_uuid=True), sa.ForeignKey("internal_audit_finding.id"), nullable=True),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("severity", sa.String(20), nullable=False),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("root_cause", sa.Text(), nullable=True),
            sa.Column("root_cause_method", sa.String(120), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("opened_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("closed_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_nonconformity_code"),
        )
    if not _table_exists(conn, "corrective_action"):
        op.create_table(
            "corrective_action",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("nonconformity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("nonconformity.id"), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("responsible_member_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="planned"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "nonconformity_verification"):
        op.create_table(
            "nonconformity_verification",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("nonconformity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("nonconformity.id"), nullable=False),
            sa.Column("result", sa.String(20), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("verified_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "nonconformity_event"):
        op.create_table(
            "nonconformity_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("nonconformity_id", sa.Uuid(as_uuid=True), sa.ForeignKey("nonconformity.id"), nullable=True),
            sa.Column("entity_type", sa.String(30), nullable=False),
            sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )
    if not _table_exists(conn, "management_review"):
        op.create_table(
            "management_review",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("review_date", sa.Date(), nullable=False),
            sa.Column("inputs", sa.JSON(), nullable=False),
            sa.Column("outputs", sa.JSON(), nullable=False),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("draft_status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if not _table_exists(conn, "improvement"):
        op.create_table(
            "improvement",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("origin", sa.String(30), nullable=False),
            sa.Column("source_ref", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_improvement_code"),
        )
    if not _table_exists(conn, "improvement_event"):
        op.create_table(
            "improvement_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("improvement_id", sa.Uuid(as_uuid=True), sa.ForeignKey("improvement.id"), nullable=True),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )


def _create_indexes(conn) -> None:
    _idx(conn, "ix_nonconformity_tenant_id", "nonconformity", ["tenant_id"])
    _idx(conn, "ix_nonconformity_status", "nonconformity", ["status"])
    _idx(conn, "ix_nonconformity_severity", "nonconformity", ["severity"])
    _idx(conn, "ix_nonconformity_source_finding_id", "nonconformity", ["source_finding_id"])
    _idx(conn, "ix_nonconformity_target", "nonconformity", ["target_type", "target_id"])
    _idx(conn, "ix_corrective_action_tenant_id", "corrective_action", ["tenant_id"])
    _idx(conn, "ix_corrective_action_nonconformity_id", "corrective_action", ["nonconformity_id"])
    _idx(conn, "ix_corrective_action_status", "corrective_action", ["status"])
    _idx(conn, "ix_nc_verification_tenant_id", "nonconformity_verification", ["tenant_id"])
    _idx(conn, "ix_nc_verification_nonconformity_id", "nonconformity_verification", ["nonconformity_id"])
    _idx(conn, "ix_nonconformity_event_tenant_id", "nonconformity_event", ["tenant_id"])
    _idx(conn, "ix_nonconformity_event_nc_id", "nonconformity_event", ["nonconformity_id"])
    _idx(conn, "ix_nonconformity_event_type", "nonconformity_event", ["event_type"])
    _idx(conn, "ix_management_review_tenant_id", "management_review", ["tenant_id"])
    _idx(conn, "ix_management_review_date", "management_review", ["review_date"])
    _idx(conn, "ix_improvement_tenant_id", "improvement", ["tenant_id"])
    _idx(conn, "ix_improvement_status", "improvement", ["status"])
    _idx(conn, "ix_improvement_origin", "improvement", ["origin"])
    _idx(conn, "ix_improvement_target", "improvement", ["target_type", "target_id"])
    _idx(conn, "ix_improvement_event_tenant_id", "improvement_event", ["tenant_id"])
    _idx(conn, "ix_improvement_event_improvement_id", "improvement_event", ["improvement_id"])
    _idx(conn, "ix_improvement_event_type", "improvement_event", ["event_type"])


def _append_only(conn, table) -> None:
    if conn.dialect.name == "postgresql":
        fn = f"wtn_{table}_append_only"
        conn.execute(sa.text(
            f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$ "
            f"BEGIN IF TG_OP IN ('UPDATE','DELETE') THEN RAISE EXCEPTION '{table} is append-only'; "
            f"END IF; RETURN NEW; END; $$;"
        ))
        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
        conn.execute(sa.text(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {fn}();"
        ))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"))
        conn.execute(sa.text(f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"))


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
    for table in _APPEND_ONLY:
        _append_only(conn, table)
    _create_rls(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for table in _SCOPED:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
            conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        for table in _APPEND_ONLY:
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS wtn_{table}_append_only()"))
    if conn.dialect.name == "sqlite":
        for table in _APPEND_ONLY:
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_update;"))
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_delete;"))
    op.drop_table("improvement_event")
    op.drop_table("improvement")
    op.drop_table("management_review")
    op.drop_table("nonconformity_event")
    op.drop_table("nonconformity_verification")
    op.drop_table("corrective_action")
    op.drop_table("nonconformity")
