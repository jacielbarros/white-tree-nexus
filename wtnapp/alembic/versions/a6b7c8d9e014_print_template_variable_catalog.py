"""Print template variable catalog.

Revision ID: a6b7c8d9e014
Revises: f5a6b7c8d913
Create Date: 2026-06-25
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a6b7c8d9e014"
down_revision: Union[str, None] = "f5a6b7c8d913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "print_template_variables"
_SEED_NAMESPACE = uuid.UUID("f74a9f41-e8b2-482e-8d16-bacb59e3c8c4")


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _columns(conn: sa.engine.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {column["name"] for column in sa.inspect(conn).get_columns(table)}


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _add_column_if_missing(conn: sa.engine.Connection, table: str, column: sa.Column) -> None:
    if column.name not in _columns(conn, table):
        op.add_column(table, column)


def _create_index_if_missing(conn: sa.engine.Connection, name: str, table: str, columns: list[str]) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_or_update_table(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, _TABLE):
        op.create_table(
            _TABLE,
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=True),
            sa.Column("scope", sa.String(20), nullable=False, server_default="tenant"),
            sa.Column("document_type", sa.String(40), nullable=False),
            sa.Column("variable_key", sa.String(80), nullable=False),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("description", sa.String(500), nullable=True),
            sa.Column("value_type", sa.String(30), nullable=False, server_default="string"),
            sa.Column("required_by_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("optional_by_default", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "document_type", "variable_key", name="uq_print_template_variable_key"),
        )
        return

    _add_column_if_missing(conn, _TABLE, sa.Column("tenant_id", sa.Uuid(as_uuid=True), nullable=True))
    _add_column_if_missing(conn, _TABLE, sa.Column("scope", sa.String(20), nullable=False, server_default="tenant"))
    _add_column_if_missing(conn, _TABLE, sa.Column("document_type", sa.String(40), nullable=False, server_default="gap_report"))
    _add_column_if_missing(conn, _TABLE, sa.Column("variable_key", sa.String(80), nullable=False, server_default="organization_name"))
    _add_column_if_missing(conn, _TABLE, sa.Column("label", sa.String(120), nullable=False, server_default="Variavel"))
    _add_column_if_missing(conn, _TABLE, sa.Column("description", sa.String(500), nullable=True))
    _add_column_if_missing(conn, _TABLE, sa.Column("value_type", sa.String(30), nullable=False, server_default="string"))
    _add_column_if_missing(conn, _TABLE, sa.Column("required_by_default", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    _add_column_if_missing(conn, _TABLE, sa.Column("optional_by_default", sa.Boolean(), nullable=False, server_default=sa.text("true")))
    _add_column_if_missing(conn, _TABLE, sa.Column("status", sa.String(20), nullable=False, server_default="active"))
    _add_column_if_missing(conn, _TABLE, sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"))
    _add_column_if_missing(conn, _TABLE, sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True))
    _add_column_if_missing(conn, _TABLE, sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    _add_column_if_missing(conn, _TABLE, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_print_template_variables_tenant_id", _TABLE, ["tenant_id"])
    _create_index_if_missing(conn, "ix_print_template_variables_document_type", _TABLE, ["document_type"])
    _create_index_if_missing(conn, "ix_print_template_variables_scope", _TABLE, ["scope"])
    _create_index_if_missing(conn, "ix_print_template_variables_status", _TABLE, ["status"])


def _seed_system_variables(conn: sa.engine.Connection) -> None:
    from wtnapp.data.print_template_variable_seed import default_template_variables

    now = datetime.now(timezone.utc)
    for definition in default_template_variables():
        row_id = conn.execute(
            sa.text(
                f"SELECT id FROM {_TABLE} WHERE tenant_id IS NULL AND scope = 'system' "
                "AND document_type = :document_type AND variable_key = :variable_key"
            ),
            {
                "document_type": definition["document_type"],
                "variable_key": definition["variable_key"],
            },
        ).scalar()
        params = {
            # str(): pysqlite não aceita bind de uuid.UUID em SQL cru (psycopg aceita a string
            # numa coluna uuid). Mantém o `alembic upgrade head` funcional em SQLite e PostgreSQL.
            "id": row_id or str(uuid.uuid5(
                _SEED_NAMESPACE,
                f"{definition['document_type']}:{definition['variable_key']}",
            )),
            "document_type": definition["document_type"],
            "variable_key": definition["variable_key"],
            "label": definition["label"],
            "description": definition.get("description"),
            "value_type": definition.get("value_type", "string"),
            "required_by_default": bool(definition.get("required_by_default", False)),
            "optional_by_default": bool(definition.get("optional_by_default", True)),
            "status": "active",
            "sort_order": int(definition.get("sort_order", 100)),
            "created_at": now,
            "updated_at": now,
        }
        if row_id is None:
            conn.execute(
                sa.text(
                    f"INSERT INTO {_TABLE} "
                    "(id, tenant_id, scope, document_type, variable_key, label, description, value_type, "
                    "required_by_default, optional_by_default, status, sort_order, created_by, created_at, updated_at) "
                    "VALUES (:id, NULL, 'system', :document_type, :variable_key, :label, :description, :value_type, "
                    ":required_by_default, :optional_by_default, :status, :sort_order, NULL, :created_at, :updated_at)"
                ),
                params,
            )
        else:
            conn.execute(
                sa.text(
                    f"UPDATE {_TABLE} SET "
                    "label = :label, description = :description, value_type = :value_type, "
                    "required_by_default = :required_by_default, optional_by_default = :optional_by_default, "
                    "status = :status, sort_order = :sort_order, updated_at = :updated_at "
                    "WHERE id = :id"
                ),
                params,
            )


def _create_rls(conn: sa.engine.Connection) -> None:
    if conn.dialect.name != "postgresql":
        return
    conn.execute(sa.text(f"ALTER TABLE {_TABLE} ENABLE ROW LEVEL SECURITY;"))
    conn.execute(sa.text(f"ALTER TABLE {_TABLE} FORCE ROW LEVEL SECURITY;"))
    conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {_TABLE};"))
    conn.execute(sa.text(
        f"CREATE POLICY tenant_isolation ON {_TABLE} "
        "USING (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid) "
        "WITH CHECK (tenant_id IS NULL OR tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
    ))


def upgrade() -> None:
    conn = op.get_bind()
    _create_or_update_table(conn)
    _create_indexes(conn)
    _seed_system_variables(conn)
    _create_rls(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {_TABLE};"))
        conn.execute(sa.text(f"ALTER TABLE {_TABLE} DISABLE ROW LEVEL SECURITY;"))
    if _table_exists(conn, _TABLE):
        op.drop_table(_TABLE)
