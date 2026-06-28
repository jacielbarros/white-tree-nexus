"""Risk management module - Feature 012.

Revision ID: c2d3e4f5a116
Revises: b1c2d3e4f015
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a116"
down_revision: Union[str, None] = "b1c2d3e4f015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Tabelas tenant-scoped (recebem RLS). As 2 sementes (threat_seed_item, vulnerability_seed_item)
# são platform-level e NÃO recebem RLS — mesma exceção documentada do Gap.
_SCOPED_TABLES = (
    "risk_methodology",
    "org_threat",
    "org_vulnerability",
    "asset_threat_link",
    "asset_vulnerability_link",
    "risk",
    "risk_asset_link",
    "risk_treatment_control",
    "risk_plan",
    "risk_events",
)


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _create_index_if_missing(conn, name: str, table: str, columns: list[str]) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "threat_seed_item"):
        op.create_table(
            "threat_seed_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("origin", sa.String(20), nullable=True),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("code", name="uq_threat_seed_code"),
        )

    if not _table_exists(conn, "vulnerability_seed_item"):
        op.create_table(
            "vulnerability_seed_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("order", sa.Integer(), nullable=False, server_default="0"),
            sa.UniqueConstraint("code", name="uq_vulnerability_seed_code"),
        )

    if not _table_exists(conn, "risk_methodology"):
        op.create_table(
            "risk_methodology",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("is_configured", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("probability_scale", sa.JSON(), nullable=False),
            sa.Column("impact_scale", sa.JSON(), nullable=False),
            sa.Column("risk_levels", sa.JSON(), nullable=False),
            sa.Column("risk_matrix", sa.JSON(), nullable=False),
            sa.Column("acceptance", sa.JSON(), nullable=False),
            sa.Column("cia_impact_map", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uq_risk_methodology_tenant"),
        )

    if not _table_exists(conn, "org_threat"):
        op.create_table(
            "org_threat",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("seed_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("threat_seed_item.id"), nullable=True),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("origin", sa.String(20), nullable=True),
            sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archive_reason", sa.String(500), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_org_threat_tenant_code"),
        )

    if not _table_exists(conn, "org_vulnerability"):
        op.create_table(
            "org_vulnerability",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("seed_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("vulnerability_seed_item.id"), nullable=True),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("category", sa.String(20), nullable=False),
            sa.Column("gap_catalog_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_catalog_item.id"), nullable=True),
            sa.Column("is_custom", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archive_reason", sa.String(500), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_org_vulnerability_tenant_code"),
        )

    if not _table_exists(conn, "asset_threat_link"):
        op.create_table(
            "asset_threat_link",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("asset_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("threat_id", sa.Uuid(as_uuid=True), sa.ForeignKey("org_threat.id"), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "asset_item_id", "threat_id", name="uq_asset_threat_link"),
        )

    if not _table_exists(conn, "asset_vulnerability_link"):
        op.create_table(
            "asset_vulnerability_link",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("asset_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("vulnerability_id", sa.Uuid(as_uuid=True), sa.ForeignKey("org_vulnerability.id"), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "asset_item_id", "vulnerability_id", name="uq_asset_vulnerability_link"),
        )

    if not _table_exists(conn, "risk"):
        op.create_table(
            "risk",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("code", sa.String(20), nullable=False),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("threat_id", sa.Uuid(as_uuid=True), sa.ForeignKey("org_threat.id"), nullable=False),
            sa.Column("vulnerability_id", sa.Uuid(as_uuid=True), sa.ForeignKey("org_vulnerability.id"), nullable=False),
            sa.Column("probability_level", sa.Integer(), nullable=True),
            sa.Column("impact_level", sa.Integer(), nullable=True),
            sa.Column("impact_derived_level", sa.Integer(), nullable=True),
            sa.Column("impact_is_override", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("impact_override_reason", sa.Text(), nullable=True),
            sa.Column("inherent_level_key", sa.String(20), nullable=True),
            sa.Column("above_acceptance", sa.Boolean(), nullable=True),
            sa.Column("owner_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, server_default="identified"),
            sa.Column("treatment_option", sa.String(20), nullable=True),
            sa.Column("treatment_note", sa.Text(), nullable=True),
            sa.Column("residual_probability_level", sa.Integer(), nullable=True),
            sa.Column("residual_impact_level", sa.Integer(), nullable=True),
            sa.Column("residual_level_key", sa.String(20), nullable=True),
            sa.Column("residual_above_acceptance", sa.Boolean(), nullable=True),
            sa.Column("acceptance_reason", sa.Text(), nullable=True),
            sa.Column("accepted_owner_user_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("accepted_by_user_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("archive_reason", sa.String(500), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "code", name="uq_risk_tenant_code"),
        )

    if not _table_exists(conn, "risk_asset_link"):
        op.create_table(
            "risk_asset_link",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("risk_id", sa.Uuid(as_uuid=True), sa.ForeignKey("risk.id"), nullable=False),
            sa.Column("asset_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("asset_items.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("risk_id", "asset_item_id", name="uq_risk_asset_link"),
        )

    if not _table_exists(conn, "risk_treatment_control"):
        op.create_table(
            "risk_treatment_control",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("risk_id", sa.Uuid(as_uuid=True), sa.ForeignKey("risk.id"), nullable=False),
            sa.Column("gap_catalog_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_catalog_item.id"), nullable=True),
            sa.Column("custom_control_label", sa.String(300), nullable=True),
            sa.Column("responsible_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("due_date", sa.Date(), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(conn, "risk_plan"):
        op.create_table(
            "risk_plan",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("draft_status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uq_risk_plan_tenant"),
        )

    if not _table_exists(conn, "risk_events"):
        op.create_table(
            "risk_events",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("risk_id", sa.Uuid(as_uuid=True), sa.ForeignKey("risk.id"), nullable=True),
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
    _create_index_if_missing(conn, "ix_risk_methodology_tenant_id", "risk_methodology", ["tenant_id"])
    _create_index_if_missing(conn, "ix_org_threat_tenant_id", "org_threat", ["tenant_id"])
    _create_index_if_missing(conn, "ix_org_threat_seed_item_id", "org_threat", ["seed_item_id"])
    _create_index_if_missing(conn, "ix_org_vulnerability_tenant_id", "org_vulnerability", ["tenant_id"])
    _create_index_if_missing(conn, "ix_org_vulnerability_seed_item_id", "org_vulnerability", ["seed_item_id"])
    _create_index_if_missing(conn, "ix_asset_threat_link_tenant_id", "asset_threat_link", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_threat_link_asset_item_id", "asset_threat_link", ["asset_item_id"])
    _create_index_if_missing(conn, "ix_asset_threat_link_threat_id", "asset_threat_link", ["threat_id"])
    _create_index_if_missing(conn, "ix_asset_vulnerability_link_tenant_id", "asset_vulnerability_link", ["tenant_id"])
    _create_index_if_missing(conn, "ix_asset_vulnerability_link_asset_item_id", "asset_vulnerability_link", ["asset_item_id"])
    _create_index_if_missing(conn, "ix_asset_vulnerability_link_vulnerability_id", "asset_vulnerability_link", ["vulnerability_id"])
    _create_index_if_missing(conn, "ix_risk_tenant_id", "risk", ["tenant_id"])
    _create_index_if_missing(conn, "ix_risk_status", "risk", ["status"])
    _create_index_if_missing(conn, "ix_risk_owner_user_id", "risk", ["owner_user_id"])
    _create_index_if_missing(conn, "ix_risk_inherent_level_key", "risk", ["inherent_level_key"])
    _create_index_if_missing(conn, "ix_risk_asset_link_tenant_id", "risk_asset_link", ["tenant_id"])
    _create_index_if_missing(conn, "ix_risk_asset_link_risk_id", "risk_asset_link", ["risk_id"])
    _create_index_if_missing(conn, "ix_risk_asset_link_asset_item_id", "risk_asset_link", ["asset_item_id"])
    _create_index_if_missing(conn, "ix_risk_treatment_control_tenant_id", "risk_treatment_control", ["tenant_id"])
    _create_index_if_missing(conn, "ix_risk_treatment_control_risk_id", "risk_treatment_control", ["risk_id"])
    _create_index_if_missing(conn, "ix_risk_treatment_control_gap_catalog_item_id", "risk_treatment_control", ["gap_catalog_item_id"])
    _create_index_if_missing(conn, "ix_risk_plan_tenant_id", "risk_plan", ["tenant_id"])
    _create_index_if_missing(conn, "ix_risk_events_tenant_id", "risk_events", ["tenant_id"])
    _create_index_if_missing(conn, "ix_risk_events_risk_id", "risk_events", ["risk_id"])
    _create_index_if_missing(conn, "ix_risk_events_event_type", "risk_events", ["event_type"])


def _create_append_only(conn: sa.engine.Connection) -> None:
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION wtn_risk_events_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'risk_events is append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS risk_events_append_only ON risk_events"))
        conn.execute(sa.text("""
            CREATE TRIGGER risk_events_append_only
            BEFORE UPDATE OR DELETE ON risk_events
            FOR EACH ROW EXECUTE FUNCTION wtn_risk_events_append_only();
        """))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS risk_events_no_update BEFORE UPDATE ON risk_events "
            "BEGIN SELECT RAISE(ABORT, 'risk_events is append-only'); END;"
        ))
        conn.execute(sa.text(
            "CREATE TRIGGER IF NOT EXISTS risk_events_no_delete BEFORE DELETE ON risk_events "
            "BEGIN SELECT RAISE(ABORT, 'risk_events is append-only'); END;"
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
        conn.execute(sa.text("DROP TRIGGER IF EXISTS risk_events_append_only ON risk_events"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS wtn_risk_events_append_only()"))
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS risk_events_no_update;"))
        conn.execute(sa.text("DROP TRIGGER IF EXISTS risk_events_no_delete;"))
    for table in (
        "risk_events", "risk_plan", "risk_treatment_control", "risk_asset_link", "risk",
        "asset_vulnerability_link", "asset_threat_link", "org_vulnerability", "org_threat",
        "risk_methodology", "vulnerability_seed_item", "threat_seed_item",
    ):
        op.drop_table(table)
