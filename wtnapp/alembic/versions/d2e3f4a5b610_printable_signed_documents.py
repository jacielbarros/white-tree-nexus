"""Printable signed documents - Feature 009.

Revision ID: d2e3f4a5b610
Revises: c1d2e3f4a509
Create Date: 2026-06-23
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e3f4a5b610"
down_revision: Union[str, None] = "c1d2e3f4a509"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = (
    "print_templates",
    "print_template_versions",
    "document_previews",
    "signed_documents",
    "signed_document_snapshots",
    "document_signatures",
    "document_access_events",
)
_APPEND_ONLY_TABLES = (
    "print_template_versions",
    "signed_documents",
    "signed_document_snapshots",
    "document_signatures",
    "document_access_events",
)


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _create_index_if_missing(
    conn: sa.engine.Connection,
    name: str,
    table: str,
    columns: list[str],
) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "print_templates"):
        op.create_table(
            "print_templates",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("scope", sa.String(20), nullable=False),
            sa.Column("document_type", sa.String(40), nullable=False),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("default_classification", sa.String(30), nullable=False, server_default="uso_interno"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "document_type", "name", name="uq_print_template_tenant_type_name"),
        )

    if not _table_exists(conn, "print_template_versions"):
        op.create_table(
            "print_template_versions",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("template_id", sa.Uuid(as_uuid=True), sa.ForeignKey("print_templates.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("renderer", sa.String(40), nullable=False, server_default="reportlab_v1"),
            sa.Column("layout_schema", sa.JSON(), nullable=False),
            sa.Column("allowed_variables", sa.JSON(), nullable=False),
            sa.Column("required_sections", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("template_id", "version_number", name="uq_print_template_version_number"),
        )

    if not _table_exists(conn, "document_previews"):
        op.create_table(
            "document_previews",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("document_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("source_document_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document_versions.id"), nullable=True),
            sa.Column("template_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("print_template_versions.id"), nullable=False),
            sa.Column("classification", sa.String(30), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("artifact_fingerprint", sa.String(64), nullable=False),
            sa.Column("template_hash", sa.String(64), nullable=False),
            sa.Column("snapshot_hash", sa.String(64), nullable=False),
            sa.Column("preview_pdf_hash", sa.String(64), nullable=False),
            sa.Column("preview_storage_key", sa.String(500), nullable=False),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("rendered_variables", sa.JSON(), nullable=False),
            sa.Column("warnings", sa.JSON(), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(conn, "signed_documents"):
        op.create_table(
            "signed_documents",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("document_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_type", sa.String(40), nullable=False),
            sa.Column("source_artifact_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("source_document_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document_versions.id"), nullable=True),
            sa.Column("preview_id", sa.Uuid(as_uuid=True), sa.ForeignKey("document_previews.id"), nullable=False),
            sa.Column("template_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("print_template_versions.id"), nullable=False),
            sa.Column("version_number", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="signed"),
            sa.Column("classification", sa.String(30), nullable=False),
            sa.Column("identifier", sa.String(80), nullable=False),
            sa.Column("pdf_hash", sa.String(64), nullable=False),
            sa.Column("snapshot_hash", sa.String(64), nullable=False),
            sa.Column("hash_algorithm", sa.String(20), nullable=False, server_default="sha256"),
            sa.Column("pdf_storage_key", sa.String(500), nullable=False),
            sa.Column("size_bytes", sa.Integer(), nullable=False),
            sa.Column("signed_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "document_type",
                "source_artifact_type",
                "source_artifact_id",
                "version_number",
                name="uq_signed_document_version_number",
            ),
            sa.UniqueConstraint("tenant_id", "identifier", name="uq_signed_document_identifier"),
        )

    if not _table_exists(conn, "signed_document_snapshots"):
        op.create_table(
            "signed_document_snapshots",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("signed_document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("signed_documents.id"), nullable=False),
            sa.Column("artifact_fingerprint", sa.String(64), nullable=False),
            sa.Column("template_hash", sa.String(64), nullable=False),
            sa.Column("snapshot_hash", sa.String(64), nullable=False),
            sa.Column("rendered_variables", sa.JSON(), nullable=False),
            sa.Column("snapshot_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("signed_document_id", name="uq_signed_document_snapshot_document"),
        )

    if not _table_exists(conn, "document_signatures"):
        op.create_table(
            "document_signatures",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("signed_document_id", sa.Uuid(as_uuid=True), sa.ForeignKey("signed_documents.id"), nullable=False),
            sa.Column("signer_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("signer_role", sa.String(60), nullable=False),
            sa.Column("signer_name", sa.String(200), nullable=False),
            sa.Column("signer_email", sa.String(320), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("pdf_hash", sa.String(64), nullable=False),
            sa.Column("algorithm", sa.String(20), nullable=False, server_default="sha256"),
            sa.Column("level", sa.String(20), nullable=False, server_default="advanced"),
            sa.Column("auth_context", sa.JSON(), nullable=False),
            sa.Column("ip", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
        )

    if not _table_exists(conn, "document_access_events"):
        op.create_table(
            "document_access_events",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("entity_type", sa.String(60), nullable=False),
            sa.Column("entity_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("actor_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("actor_role", sa.String(60), nullable=True),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_print_templates_tenant_id", "print_templates", ["tenant_id"])
    _create_index_if_missing(conn, "ix_print_templates_document_type", "print_templates", ["document_type"])
    _create_index_if_missing(conn, "ix_print_templates_scope", "print_templates", ["scope"])
    _create_index_if_missing(conn, "ix_print_templates_status", "print_templates", ["status"])
    _create_index_if_missing(conn, "ix_print_template_versions_tenant_id", "print_template_versions", ["tenant_id"])
    _create_index_if_missing(conn, "ix_print_template_versions_template_id", "print_template_versions", ["template_id"])
    _create_index_if_missing(conn, "ix_print_template_versions_hash", "print_template_versions", ["content_hash"])
    _create_index_if_missing(conn, "ix_document_previews_tenant_id", "document_previews", ["tenant_id"])
    _create_index_if_missing(conn, "ix_document_previews_document_type", "document_previews", ["document_type"])
    _create_index_if_missing(conn, "ix_document_previews_source", "document_previews", ["source_artifact_type", "source_artifact_id"])
    _create_index_if_missing(conn, "ix_document_previews_status", "document_previews", ["status"])
    _create_index_if_missing(conn, "ix_document_previews_created_by", "document_previews", ["created_by"])
    _create_index_if_missing(conn, "ix_signed_documents_tenant_id", "signed_documents", ["tenant_id"])
    _create_index_if_missing(conn, "ix_signed_documents_document_type", "signed_documents", ["document_type"])
    _create_index_if_missing(conn, "ix_signed_documents_source", "signed_documents", ["source_artifact_type", "source_artifact_id"])
    _create_index_if_missing(conn, "ix_signed_documents_signed_at", "signed_documents", ["signed_at"])
    _create_index_if_missing(conn, "ix_signed_document_snapshots_tenant_id", "signed_document_snapshots", ["tenant_id"])
    _create_index_if_missing(conn, "ix_signed_document_snapshots_document_id", "signed_document_snapshots", ["signed_document_id"])
    _create_index_if_missing(conn, "ix_document_signatures_tenant_id", "document_signatures", ["tenant_id"])
    _create_index_if_missing(conn, "ix_document_signatures_document_id", "document_signatures", ["signed_document_id"])
    _create_index_if_missing(conn, "ix_document_signatures_signer_user_id", "document_signatures", ["signer_user_id"])
    _create_index_if_missing(conn, "ix_document_access_events_tenant_id", "document_access_events", ["tenant_id"])
    _create_index_if_missing(conn, "ix_document_access_events_entity", "document_access_events", ["entity_type", "entity_id"])
    _create_index_if_missing(conn, "ix_document_access_events_event_type", "document_access_events", ["event_type"])
    _create_index_if_missing(conn, "ix_document_access_events_actor_user_id", "document_access_events", ["actor_user_id"])


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
            "USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
            "WITH CHECK (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
        ))


def _seed_templates(conn: sa.engine.Connection) -> None:
    from wtnapp.data.print_template_seed import default_templates
    from wtnapp.services.print_template_service import template_content_hash

    now = datetime.now(timezone.utc)
    for definition in default_templates():
        template_id = conn.execute(
            sa.text(
                "SELECT id FROM print_templates WHERE tenant_id IS NULL AND scope = 'system' "
                "AND document_type = :document_type AND name = :name"
            ),
            {"document_type": definition["document_type"], "name": definition["name"]},
        ).scalar()
        if template_id is None:
            # str(): pysqlite não aceita bind de uuid.UUID em SQL cru; psycopg aceita a string
            # numa coluna uuid. Mantém o `alembic upgrade head` funcional em SQLite e PostgreSQL.
            template_id = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO print_templates "
                    "(id, tenant_id, scope, document_type, name, description, status, default_classification, "
                    "current_version_id, created_by, created_at, updated_at) "
                    "VALUES (:id, NULL, 'system', :document_type, :name, :description, 'active', "
                    ":classification, NULL, NULL, :created_at, :updated_at)"
                ),
                {
                    "id": template_id,
                    "document_type": definition["document_type"],
                    "name": definition["name"],
                    "description": definition.get("description"),
                    "classification": definition["default_classification"],
                    "created_at": now,
                    "updated_at": now,
                },
            )
        desired_hash = template_content_hash(
            layout_schema=definition["layout_schema"],
            allowed_variables=definition["allowed_variables"],
            required_sections=definition["required_sections"],
        )
        version_id = conn.execute(
            sa.text(
                "SELECT id FROM print_template_versions "
                "WHERE template_id = :template_id AND content_hash = :content_hash"
            ),
            {"template_id": template_id, "content_hash": desired_hash},
        ).scalar()
        if version_id is None:
            next_number = (
                conn.execute(
                    sa.text("SELECT COALESCE(MAX(version_number), 0) + 1 FROM print_template_versions WHERE template_id = :template_id"),
                    {"template_id": template_id},
                ).scalar()
                or 1
            )
            version_id = str(uuid.uuid4())
            conn.execute(
                sa.text(
                    "INSERT INTO print_template_versions "
                    "(id, tenant_id, template_id, version_number, renderer, layout_schema, allowed_variables, "
                    "required_sections, content_hash, created_by, created_at) "
                    "VALUES (:id, NULL, :template_id, :version_number, 'reportlab_v1', :layout_schema, "
                    ":allowed_variables, :required_sections, :content_hash, NULL, :created_at)"
                ),
                {
                    "id": version_id,
                    "template_id": template_id,
                    "version_number": int(next_number),
                    "layout_schema": json.dumps(definition["layout_schema"], ensure_ascii=False),
                    "allowed_variables": json.dumps(definition["allowed_variables"], ensure_ascii=False),
                    "required_sections": json.dumps(definition["required_sections"], ensure_ascii=False),
                    "content_hash": desired_hash,
                    "created_at": now,
                },
            )
        current = conn.execute(
            sa.text("SELECT current_version_id FROM print_templates WHERE id = :template_id"),
            {"template_id": template_id},
        ).scalar()
        if str(current) != str(version_id):
            conn.execute(
                sa.text(
                    "UPDATE print_templates SET current_version_id = :version_id, status = 'active', updated_at = :updated_at "
                    "WHERE id = :template_id"
                ),
                {"version_id": version_id, "template_id": template_id, "updated_at": now},
            )


def upgrade() -> None:
    conn = op.get_bind()
    _create_tables(conn)
    _create_indexes(conn)
    _create_append_only(conn)
    _seed_templates(conn)
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
    for table in reversed(_SCOPED_TABLES):
        if _table_exists(conn, table):
            op.drop_table(table)
