"""RLS (defesa em profundidade) e auditoria append-only

Revision ID: b2c3d4e5f601
Revises: 18d01e15da30
Create Date: 2026-06-18

- Auditoria append-only: gatilho que bloqueia UPDATE/DELETE em `audit_logs` (SQLite + PostgreSQL).
- Row-Level Security nas tabelas escopadas (apenas PostgreSQL): `tenant_id` deve casar com
  `current_setting('app.tenant_id')`, setado por requisição em `helpers/tenant_scope.py`.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "b2c3d4e5f601"
down_revision: Union[str, None] = "18d01e15da30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = ("memberships", "invitations")


def upgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs "
            "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;"
        )
        op.execute(
            "CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs "
            "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;"
        )
    elif dialect == "postgresql":
        op.execute(
            "CREATE OR REPLACE FUNCTION wtn_audit_append_only() RETURNS trigger AS $$ "
            "BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql;"
        )
        op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;")
        op.execute(
            "CREATE TRIGGER audit_logs_append_only BEFORE UPDATE OR DELETE ON audit_logs "
            "FOR EACH ROW EXECUTE FUNCTION wtn_audit_append_only();"
        )
        for table in _SCOPED_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} "
                "USING (tenant_id = current_setting('app.tenant_id', true)::uuid);"
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name

    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_update;")
        op.execute("DROP TRIGGER IF EXISTS audit_logs_no_delete;")
    elif dialect == "postgresql":
        for table in _SCOPED_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute("DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;")
        op.execute("DROP FUNCTION IF EXISTS wtn_audit_append_only();")
