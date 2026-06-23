"""Gap evidence attachments - Feature 008.

Revision ID: c1d2e3f4a509
Revises: 84c5c822d7b1
Create Date: 2026-06-22
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a509"
down_revision: Union[str, None] = "84c5c822d7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = ("gap_evidence", "gap_evidence_version", "gap_evidence_event")


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _fk_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {fk.get("name") for fk in sa.inspect(conn).get_foreign_keys(table)}


def _create_index_if_missing(conn: sa.engine.Connection, name: str, table: str, columns: list[str]) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "gap_evidence"):
        op.create_table(
            "gap_evidence",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column(
                "assessment_item_id",
                sa.Uuid(as_uuid=True),
                sa.ForeignKey("gap_assessment_item.id"),
                nullable=False,
            ),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("classification", sa.String(30), nullable=False, server_default="uso_interno"),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("inactivated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("inactivated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("inactivation_reason", sa.String(300), nullable=True),
        )

    if not _table_exists(conn, "gap_evidence_version"):
        op.create_table(
            "gap_evidence_version",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_evidence.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("classification", sa.String(30), nullable=False),
            sa.Column("original_filename", sa.String(255), nullable=False),
            sa.Column("storage_key", sa.String(500), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("hash_algorithm", sa.String(20), nullable=False, server_default="sha256"),
            sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("encryption_scheme", sa.String(40), nullable=False, server_default="fernet"),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("mime_type", sa.String(120), nullable=True),
            sa.Column("extension", sa.String(20), nullable=False),
            sa.Column("uploaded_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "evidence_id", "version_number", name="uq_gap_evidence_version_number"),
        )

    if not _table_exists(conn, "gap_evidence_event"):
        op.create_table(
            "gap_evidence_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_evidence.id"), nullable=True),
            sa.Column("version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_evidence_version.id"), nullable=True),
            sa.Column(
                "assessment_item_id",
                sa.Uuid(as_uuid=True),
                sa.ForeignKey("gap_assessment_item.id"),
                nullable=True,
            ),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_gap_evidence_tenant_id", "gap_evidence", ["tenant_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_assessment_item_id", "gap_evidence", ["assessment_item_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_status", "gap_evidence", ["status"])
    _create_index_if_missing(conn, "ix_gap_evidence_current_version_id", "gap_evidence", ["current_version_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_version_tenant_id", "gap_evidence_version", ["tenant_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_version_evidence_id", "gap_evidence_version", ["evidence_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_version_hash", "gap_evidence_version", ["content_hash"])
    _create_index_if_missing(conn, "ix_gap_evidence_event_tenant_id", "gap_evidence_event", ["tenant_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_event_evidence_id", "gap_evidence_event", ["evidence_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_event_item_id", "gap_evidence_event", ["assessment_item_id"])
    _create_index_if_missing(conn, "ix_gap_evidence_event_type", "gap_evidence_event", ["event_type"])


def _create_append_only(conn: sa.engine.Connection) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_gap_evidence_version_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'gap_evidence_version is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_version_append_only ON gap_evidence_version"))
        conn.execute(sa.text("""
            CREATE TRIGGER gap_evidence_version_append_only
            BEFORE UPDATE OR DELETE ON gap_evidence_version
            FOR EACH ROW EXECUTE FUNCTION wtn_gap_evidence_version_append_only();
        """))
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_gap_evidence_event_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'gap_evidence_event is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_event_append_only ON gap_evidence_event"))
        conn.execute(sa.text("""
            CREATE TRIGGER gap_evidence_event_append_only
            BEFORE UPDATE OR DELETE ON gap_evidence_event
            FOR EACH ROW EXECUTE FUNCTION wtn_gap_evidence_event_append_only();
        """))

    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_evidence_version_no_update BEFORE UPDATE ON gap_evidence_version "
            "BEGIN SELECT RAISE(ABORT, 'gap_evidence_version is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_evidence_version_no_delete BEFORE DELETE ON gap_evidence_version "
            "BEGIN SELECT RAISE(ABORT, 'gap_evidence_version is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_evidence_event_no_update BEFORE UPDATE ON gap_evidence_event "
            "BEGIN SELECT RAISE(ABORT, 'gap_evidence_event is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS gap_evidence_event_no_delete BEFORE DELETE ON gap_evidence_event "
            "BEGIN SELECT RAISE(ABORT, 'gap_evidence_event is append-only'); END;"
        ))


def _create_rls(conn: sa.engine.Connection) -> None:
    if conn.dialect.name != "postgresql":
        return
    for table in _SCOPED_TABLES:
        conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;"))
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
        conn.execute(sa.text(
            f"CREATE POLICY tenant_isolation ON {table} "
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
        ))
    if not _fk_exists(conn, "gap_evidence", "fk_gap_evidence_current_version"):
        conn.execute(sa.text(
            "ALTER TABLE gap_evidence ADD CONSTRAINT fk_gap_evidence_current_version "
            "FOREIGN KEY (current_version_id) REFERENCES gap_evidence_version(id)"
        ))


def upgrade() -> None:
    conn = op.get_bind()
    _create_tables(conn)
    _create_indexes(conn)
    _create_append_only(conn)
    _create_rls(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        for table in _SCOPED_TABLES:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
            conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text("ALTER TABLE gap_evidence DROP CONSTRAINT IF EXISTS fk_gap_evidence_current_version"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_version_append_only ON gap_evidence_version"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_gap_evidence_version_append_only()"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_event_append_only ON gap_evidence_event"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_gap_evidence_event_append_only()"))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_version_no_update;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_version_no_delete;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_event_no_update;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS gap_evidence_event_no_delete;"))
    op.drop_table("gap_evidence_event")
    op.drop_table("gap_evidence_version")
    op.drop_table("gap_evidence")
