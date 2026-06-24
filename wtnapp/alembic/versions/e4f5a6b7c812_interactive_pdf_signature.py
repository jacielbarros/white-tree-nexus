"""Interactive PDF signature placement - Feature 010.

Revision ID: e4f5a6b7c812
Revises: e3f4a5b6c711
Create Date: 2026-06-23
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4f5a6b7c812"
down_revision: Union[str, None] = "e3f4a5b6c711"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = (
    "document_signature_placements",
    "signed_document_signature_placements",
)
_APPEND_ONLY_TABLES = (
    "document_signature_placements",
    "signed_document_signature_placements",
)


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _column_exists(conn: sa.engine.Connection, table: str, column: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return column in {col["name"] for col in sa.inspect(conn).get_columns(table)}


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    if not _table_exists(conn, table):
        return False
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _json_default(conn: sa.engine.Connection, value: str) -> sa.TextClause:
    if conn.dialect.name == "postgresql":
        return sa.text(f"'{value}'::json")
    return sa.text(f"'{value}'")


def _bool_default(conn: sa.engine.Connection, value: bool) -> sa.TextClause:
    if conn.dialect.name == "postgresql":
        return sa.text("true" if value else "false")
    return sa.text("1" if value else "0")


def _add_column_if_missing(conn: sa.engine.Connection, table: str, column: sa.Column) -> None:
    if not _table_exists(conn, table) or _column_exists(conn, table, column.name):
        return
    op.add_column(table, column)


def _drop_column_if_exists(conn: sa.engine.Connection, table: str, column: str) -> None:
    if _column_exists(conn, table, column):
        op.drop_column(table, column)


def _create_index_if_missing(
    conn: sa.engine.Connection,
    name: str,
    table: str,
    columns: list[str],
) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "document_signature_placements"):
        op.create_table(
            "document_signature_placements",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("preview_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document_previews.id"), nullable=False),
            sa.Column("document_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("placement_revision", sa.Integer(), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=False),
            sa.Column("x_points", sa.Float(), nullable=False),
            sa.Column("y_points", sa.Float(), nullable=False),
            sa.Column("width_points", sa.Float(), nullable=False),
            sa.Column("height_points", sa.Float(), nullable=False),
            sa.Column("page_width_points", sa.Float(), nullable=False),
            sa.Column("page_height_points", sa.Float(), nullable=False),
            sa.Column("coordinate_system", sa.String(40), nullable=False, server_default="pdf_points_bottom_left"),
            sa.Column("origin", sa.String(20), nullable=False, server_default="user"),
            sa.Column("template_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("print_template_versions.id"), nullable=False),
            sa.Column("snapshot_hash", sa.String(64), nullable=False),
            sa.Column("artifact_fingerprint", sa.String(64), nullable=False),
            sa.Column("signature_policy_hash", sa.String(64), nullable=True),
            sa.Column("placement_hash", sa.String(64), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "preview_id", "placement_revision", name="uq_document_signature_placement_revision"),
        )

    if not _table_exists(conn, "signed_document_signature_placements"):
        op.create_table(
            "signed_document_signature_placements",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("signed_document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("signed_documents.id"), nullable=False),
            sa.Column("placement_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document_signature_placements.id"), nullable=False),
            sa.Column("page_number", sa.Integer(), nullable=False),
            sa.Column("x_points", sa.Float(), nullable=False),
            sa.Column("y_points", sa.Float(), nullable=False),
            sa.Column("width_points", sa.Float(), nullable=False),
            sa.Column("height_points", sa.Float(), nullable=False),
            sa.Column("page_width_points", sa.Float(), nullable=False),
            sa.Column("page_height_points", sa.Float(), nullable=False),
            sa.Column("coordinate_system", sa.String(40), nullable=False),
            sa.Column("origin", sa.String(20), nullable=False),
            sa.Column("placement_hash", sa.String(64), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("signed_document_id", name="uq_signed_document_signature_placement_document"),
        )


def _reconcile_columns(conn: sa.engine.Connection) -> None:
    _add_column_if_missing(
        conn,
        "document_previews",
        sa.Column("pdf_page_metrics", sa.JSON(), nullable=False, server_default=_json_default(conn, "[]")),
    )
    _add_column_if_missing(conn, "document_previews", sa.Column("signature_policy_hash", sa.String(64), nullable=True))
    _add_column_if_missing(conn, "document_previews", sa.Column("default_signature_placement", sa.JSON(), nullable=True))

    _add_column_if_missing(
        conn,
        "document_signatures",
        sa.Column(
            "signature_method",
            sa.String(40),
            nullable=False,
            server_default="internal_electronic_signature",
        ),
    )
    _add_column_if_missing(conn, "document_signatures", sa.Column("signature_provider", sa.String(80), nullable=True))
    _add_column_if_missing(
        conn,
        "document_signatures",
        sa.Column("visual_signature_present", sa.Boolean(), nullable=False, server_default=_bool_default(conn, True)),
    )
    _add_column_if_missing(conn, "document_signatures", sa.Column("provider_reference", sa.String(200), nullable=True))
    _add_column_if_missing(conn, "document_signatures", sa.Column("provider_payload_hash", sa.String(64), nullable=True))


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_document_signature_placements_tenant_id", "document_signature_placements", ["tenant_id"])
    _create_index_if_missing(conn, "ix_document_signature_placements_preview_id", "document_signature_placements", ["preview_id"])
    _create_index_if_missing(conn, "ix_document_signature_placements_document_type", "document_signature_placements", ["document_type"])
    _create_index_if_missing(conn, "ix_document_signature_placements_created_by", "document_signature_placements", ["created_by"])
    _create_index_if_missing(
        conn,
        "ix_signed_document_signature_placements_tenant_id",
        "signed_document_signature_placements",
        ["tenant_id"],
    )
    _create_index_if_missing(
        conn,
        "ix_signed_document_signature_placements_document_id",
        "signed_document_signature_placements",
        ["signed_document_id"],
    )
    _create_index_if_missing(
        conn,
        "ix_signed_document_signature_placements_placement_id",
        "signed_document_signature_placements",
        ["placement_id"],
    )


def _create_append_only(conn: sa.engine.Connection) -> None:
    if conn.dialect.name == "postgresql":
        for table in _APPEND_ONLY_TABLES:
            fn = f"wtn_{table}_append_only"
            trigger = f"{table}_append_only"
            conn.execute(sa.text(
                f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$ "
                f"BEGIN RAISE EXCEPTION '{table} is append-only'; END; $$;"
            ))
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {trigger} ON {table}"))
            conn.execute(sa.text(
                f"CREATE TRIGGER {trigger} BEFORE UPDATE OR DELETE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {fn}();"
            ))
    if conn.dialect.name == "sqlite":
        for table in _APPEND_ONLY_TABLES:
            conn.execute(sa.text(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_update BEFORE UPDATE ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"
            ))
            conn.execute(sa.text(
                f"CREATE TRIGGER IF NOT EXISTS {table}_no_delete BEFORE DELETE ON {table} "
                f"BEGIN SELECT RAISE(ABORT, '{table} is append-only'); END;"
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
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
        ))


def upgrade() -> None:
    conn = op.get_bind()
    _reconcile_columns(conn)
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
        for table in _APPEND_ONLY_TABLES:
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table};"))
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS wtn_{table}_append_only();"))
    if conn.dialect.name == "sqlite":
        for table in _APPEND_ONLY_TABLES:
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_update;"))
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_delete;"))
    if _table_exists(conn, "signed_document_signature_placements"):
        op.drop_table("signed_document_signature_placements")
    if _table_exists(conn, "document_signature_placements"):
        op.drop_table("document_signature_placements")

    _drop_column_if_exists(conn, "document_signatures", "provider_payload_hash")
    _drop_column_if_exists(conn, "document_signatures", "provider_reference")
    _drop_column_if_exists(conn, "document_signatures", "visual_signature_present")
    _drop_column_if_exists(conn, "document_signatures", "signature_provider")
    _drop_column_if_exists(conn, "document_signatures", "signature_method")
    _drop_column_if_exists(conn, "document_previews", "default_signature_placement")
    _drop_column_if_exists(conn, "document_previews", "signature_policy_hash")
    _drop_column_if_exists(conn, "document_previews", "pdf_page_metrics")
