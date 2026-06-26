"""Asset / Process / Scope module - Feature 011.

Revision ID: b1c2d3e4f015
Revises: a6b7c8d9e014
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b1c2d3e4f015"
down_revision: Union[str, None] = "a6b7c8d9e014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = ("asset_items", "asset_relationships", "asset_gap_links", "asset_item_events")


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _create_index_if_missing(conn: sa.engine.Connection, name: str, table: str, columns: list[str]) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "asset_items"):
        op.create_table(
            "asset_items",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("item_type", sa.String(30), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("business_unit", sa.String(160), nullable=True),
            sa.Column("responsible_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("owner_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("custodian_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("record_status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("scope_status", sa.String(20), nullable=False),
            sa.Column("scope_justification", sa.Text(), nullable=True),
            sa.Column("location", sa.String(255), nullable=True),
            sa.Column("related_system_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=True),
            sa.Column("related_process_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=True),
            sa.Column("related_supplier_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=True),
            sa.Column("has_personal_data", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("has_sensitive_data", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("compliance_notes", sa.Text(), nullable=True),
            sa.Column("confidentiality", sa.String(20), nullable=True),
            sa.Column("integrity", sa.String(20), nullable=True),
            sa.Column("availability", sa.String(20), nullable=True),
            sa.Column("criticality", sa.String(20), nullable=True),
            sa.Column("criticality_is_manual", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("last_review_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("context_origin_type", sa.String(40), nullable=True),
            sa.Column("context_origin_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("archived_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("archive_reason", sa.String(500), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_asset_items_tenant_code"),
        )

    if not _table_exists(conn, "asset_relationships"):
        op.create_table(
            "asset_relationships",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("source_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("relationship_type", sa.String(30), nullable=False),
            sa.Column("target_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id", "source_item_id", "relationship_type", "target_item_id",
                name="uq_asset_relationship",
            ),
        )

    if not _table_exists(conn, "asset_gap_links"):
        op.create_table(
            "asset_gap_links",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("gap_catalog_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_catalog_item.id"), nullable=False),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "item_id", "gap_catalog_item_id", name="uq_asset_gap_link"),
        )

    if not _table_exists(conn, "asset_item_events"):
        op.create_table(
            "asset_item_events",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("field_name", sa.String(60), nullable=True),
            sa.Column("old_value", sa.Text(), nullable=True),
            sa.Column("new_value", sa.Text(), nullable=True),
            sa.Column("reason", sa.String(500), nullable=True),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_asset_items_tenant_id", "asset_items", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_items_item_type", "asset_items", ["item_type"])
    _create_index_if_missing(conn, "ix_asset_items_scope_status", "asset_items", ["scope_status"])
    _create_index_if_missing(conn, "ix_asset_items_responsible_user_id", "asset_items", ["responsible_user_id"])
    _create_index_if_missing(conn, "ix_asset_items_next_review_at", "asset_items", ["next_review_at"])
    _create_index_if_missing(conn, "ix_asset_relationships_tenant_id", "asset_relationships", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_relationships_source_item_id", "asset_relationships", ["source_item_id"])
    _create_index_if_missing(conn, "ix_asset_relationships_target_item_id", "asset_relationships", ["target_item_id"])
    _create_index_if_missing(conn, "ix_asset_gap_links_tenant_id", "asset_gap_links", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_gap_links_item_id", "asset_gap_links", ["item_id"])
    _create_index_if_missing(conn, "ix_asset_gap_links_gap_catalog_item_id", "asset_gap_links", ["gap_catalog_item_id"])
    _create_index_if_missing(conn, "ix_asset_item_events_tenant_id", "asset_item_events", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_item_events_item_id", "asset_item_events", ["item_id"])
    _create_index_if_missing(conn, "ix_asset_item_events_event_type", "asset_item_events", ["event_type"])


def _create_append_only(conn: sa.engine.Connection) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_asset_item_events_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'asset_item_events is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS asset_item_events_append_only ON asset_item_events"))
        conn.execute(sa.text("""
            CREATE TRIGGER asset_item_events_append_only
            BEFORE UPDATE OR DELETE ON asset_item_events
            FOR EACH ROW EXECUTE FUNCTION wtn_asset_item_events_append_only();
        """))

    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS asset_item_events_no_update BEFORE UPDATE ON asset_item_events "
            "BEGIN SELECT RAISE(ABORT, 'asset_item_events is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS asset_item_events_no_delete BEFORE DELETE ON asset_item_events "
            "BEGIN SELECT RAISE(ABORT, 'asset_item_events is append-only'); END;"
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
        conn.execute(sa.text("DROP TRIGGER IF EXISTS asset_item_events_append_only ON asset_item_events"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_asset_item_events_append_only()"))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS asset_item_events_no_update;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS asset_item_events_no_delete;"))
    op.drop_table("asset_item_events")
    op.drop_table("asset_gap_links")
    op.drop_table("asset_relationships")
    op.drop_table("asset_items")
