"""workflow module — Feature 003: Motor de Workflow de Preenchimento

Revision ID: d6e7f8a9b005
Revises: c3d4e5f6a702
Create Date: 2026-06-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d6e7f8a9b005"
down_revision: Union[str, None] = "c3d4e5f6a702"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_NEW_TABLES = (
    "form_templates",
    "form_assignments",
    "form_assignment_events",
    "form_signatures",
    "form_signature_otps",
    "form_signature_policies",
)

_PG_APPEND_ONLY_EVENTS = """
CREATE OR REPLACE FUNCTION wtn_form_assignment_events_append_only() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'form_assignment_events is append-only'; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS form_assignment_events_append_only ON form_assignment_events;
CREATE TRIGGER form_assignment_events_append_only
BEFORE UPDATE OR DELETE ON form_assignment_events
FOR EACH ROW EXECUTE FUNCTION wtn_form_assignment_events_append_only();
"""

_PG_APPEND_ONLY_SIGS = """
CREATE OR REPLACE FUNCTION wtn_form_signatures_append_only() RETURNS trigger AS $$
BEGIN RAISE EXCEPTION 'form_signatures is append-only'; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS form_signatures_append_only ON form_signatures;
CREATE TRIGGER form_signatures_append_only
BEFORE UPDATE OR DELETE ON form_signatures
FOR EACH ROW EXECUTE FUNCTION wtn_form_signatures_append_only();
"""

_PG_RLS_ENABLE = "\n".join(
    f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY;" for t in _NEW_TABLES
)

_PG_RLS_POLICIES = "\n".join(
    f"""
DROP POLICY IF EXISTS tenant_isolation ON {t};
CREATE POLICY tenant_isolation ON {t}
  USING (tenant_id::text = current_setting('app.tenant_id', true));
""".strip()
    for t in ("form_templates", "form_assignments", "form_assignment_events",
              "form_signatures", "form_signature_policies")
)


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def upgrade() -> None:
    conn = op.get_bind()

    # --- form_templates ---
    if not _table_exists(conn, "form_templates"):
        op.create_table(
            "form_templates",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("schema", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
            sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_form_templates_tenant_id", "form_templates", ["tenant_id"])
        op.create_index("ix_form_templates_kind", "form_templates", ["kind"])

    # --- form_assignments ---
    if not _table_exists(conn, "form_assignments"):
        op.create_table(
            "form_assignments",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("template_id", sa.Uuid(as_uuid=True), sa.ForeignKey("form_templates.id"), nullable=False),
            sa.Column("kind", sa.String(20), nullable=False),
            sa.Column("title", sa.String(200), nullable=False),
            sa.Column("fields_snapshot", sa.JSON(), nullable=False),
            sa.Column("instructions", sa.Text(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("respondent_user_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("respondent_email", sa.String(320), nullable=True),
            sa.Column("respondent_name", sa.String(200), nullable=True),
            sa.Column("respondent_token_hash", sa.String(64), unique=True, nullable=True),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("answers", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=True),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("assigned_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "(respondent_user_id IS NOT NULL AND respondent_token_hash IS NULL) OR "
                "(respondent_user_id IS NULL AND respondent_token_hash IS NOT NULL)",
                name="ck_form_assignments_respondent",
            ),
        )
        op.create_index("ix_form_assignments_tenant_id", "form_assignments", ["tenant_id"])
        op.create_index("ix_form_assignments_status", "form_assignments", ["status"])
        op.create_index("ix_form_assignments_template_id", "form_assignments", ["template_id"])
        op.create_index("ix_form_assignments_respondent_user_id", "form_assignments", ["respondent_user_id"])
        op.create_index("ix_form_assignments_token_hash", "form_assignments", ["respondent_token_hash"])

    # --- form_assignment_events (append-only) ---
    if not _table_exists(conn, "form_assignment_events"):
        op.create_table(
            "form_assignment_events",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("assignment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("form_assignments.id"), nullable=False),
            sa.Column("event", sa.String(30), nullable=False),
            sa.Column("actor_user_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("actor_label", sa.String(200), nullable=True),
            sa.Column("at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("note", sa.String(500), nullable=True),
        )
        op.create_index("ix_form_assignment_events_assignment_id", "form_assignment_events", ["assignment_id"])
        op.create_index("ix_form_assignment_events_tenant_id", "form_assignment_events", ["tenant_id"])

    # --- form_signatures (append-only) ---
    if not _table_exists(conn, "form_signatures"):
        op.create_table(
            "form_signatures",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("assignment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("form_assignments.id"), nullable=False),
            sa.Column("signer_user_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("signer_role", sa.String(20), nullable=False),
            sa.Column("signer_name", sa.String(200), nullable=False),
            sa.Column("signer_email", sa.String(320), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("algorithm", sa.String(20), nullable=False, server_default="sha256"),
            sa.Column("level", sa.String(20), nullable=False, server_default="advanced"),
            sa.Column("otp_verified", sa.Boolean(), nullable=False, server_default="false"),
            sa.Column("ip", sa.String(45), nullable=True),
            sa.Column("user_agent", sa.String(500), nullable=True),
        )
        op.create_index("ix_form_signatures_tenant_id", "form_signatures", ["tenant_id"])
        op.create_index("ix_form_signatures_assignment_id", "form_signatures", ["assignment_id"])

    # --- form_signature_otps (transiente) ---
    if not _table_exists(conn, "form_signature_otps"):
        op.create_table(
            "form_signature_otps",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("assignment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("form_assignments.id"), nullable=False, unique=True),
            sa.Column("code_hash", sa.String(64), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        )
        op.create_index("ix_form_signature_otps_assignment_id", "form_signature_otps", ["assignment_id"])

    # --- form_signature_policies (1 por org) ---
    if not _table_exists(conn, "form_signature_policies"):
        op.create_table(
            "form_signature_policies",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False, unique=True),
            sa.Column("require_assigner_countersignature", sa.Boolean(), nullable=False, server_default="false"),
        )

    # --- Triggers append-only + RLS (PostgreSQL only; idempotentes) ---
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        op.execute(sa.text(_PG_APPEND_ONLY_EVENTS))
        op.execute(sa.text(_PG_APPEND_ONLY_SIGS))
        op.execute(sa.text(_PG_RLS_ENABLE))
        op.execute(sa.text(_PG_RLS_POLICIES))


def downgrade() -> None:
    dialect = op.get_context().dialect.name
    if dialect == "postgresql":
        for t in ("form_templates", "form_assignments", "form_assignment_events",
                  "form_signatures", "form_signature_policies"):
            op.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {t}"))
        for fn in ("wtn_form_assignment_events_append_only", "wtn_form_signatures_append_only"):
            op.execute(sa.text(f"DROP FUNCTION IF EXISTS {fn}() CASCADE"))

    op.drop_table("form_signature_policies")
    op.drop_table("form_signature_otps")
    op.drop_table("form_signatures")
    op.drop_table("form_assignment_events")
    op.drop_table("form_assignments")
    op.drop_table("form_templates")
