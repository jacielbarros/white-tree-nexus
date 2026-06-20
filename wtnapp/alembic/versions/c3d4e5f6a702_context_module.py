"""context module

Revision ID: c3d4e5f6a702
Revises: b2c3d4e5f601
Create Date: 2026-06-19
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3d4e5f6a702"
down_revision: Union[str, None] = "b2c3d4e5f601"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = (
    "diagnostics",
    "context_analyses",
    "context_issues",
    "stakeholder_maps",
    "stakeholders",
    "stakeholder_requirements",
    "scope_statements",
    "scope_items",
    "document_versions",
    "classification_access_policies",
)


def _enum(*values: str, name: str, length: int = 40):
    return sa.Enum(*values, name=name, native_enum=False, length=length)


def upgrade() -> None:
    op.create_table(
        "diagnostics",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("status", _enum("draft", "completed", name="diagnosticstatus", length=20), nullable=False),
        sa.Column("sections", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_diagnostics_tenant_id"), "diagnostics", ["tenant_id"], unique=True)

    op.create_table(
        "context_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("intended_outcomes", sa.Text(), nullable=False),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("draft_status", _enum("draft", "in_review", "in_force", "obsolete", name="docstatus", length=20), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_context_analyses_tenant_id"), "context_analyses", ["tenant_id"], unique=True)

    op.create_table(
        "context_issues",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("analysis_id", sa.Uuid(), nullable=False),
        sa.Column("origin", _enum("internal", "external", name="issueorigin", length=20), nullable=False),
        sa.Column("framework", _enum("pestel", "swot", name="issueframework", length=20), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("impact", _enum("alto", "medio", "baixo", name="level", length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["context_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_context_issues_tenant_id"), "context_issues", ["tenant_id"])
    op.create_index(op.f("ix_context_issues_analysis_id"), "context_issues", ["analysis_id"])

    op.create_table(
        "stakeholder_maps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("draft_status", _enum("draft", "in_review", "in_force", "obsolete", name="docstatus", length=20), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stakeholder_maps_tenant_id"), "stakeholder_maps", ["tenant_id"], unique=True)

    op.create_table(
        "stakeholders",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("map_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("power", _enum("alto", "medio", "baixo", name="level", length=20), nullable=False),
        sa.Column("interest", _enum("alto", "medio", "baixo", name="level", length=20), nullable=False),
        sa.Column("strategy", _enum("manage_closely", "keep_satisfied", "keep_informed", "monitor", name="engagementstrategy"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["map_id"], ["stakeholder_maps.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stakeholders_tenant_id"), "stakeholders", ["tenant_id"])
    op.create_index(op.f("ix_stakeholders_map_id"), "stakeholders", ["map_id"])

    op.create_table(
        "stakeholder_requirements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("stakeholder_id", sa.Uuid(), nullable=False),
        sa.Column("type", _enum("legal", "regulatory", "contractual", "expectation", name="requirementtype", length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("how_addressed", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["stakeholder_id"], ["stakeholders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stakeholder_requirements_tenant_id"), "stakeholder_requirements", ["tenant_id"])
    op.create_index(op.f("ix_stakeholder_requirements_stakeholder_id"), "stakeholder_requirements", ["stakeholder_id"])

    op.create_table(
        "scope_statements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("interfaces_dependencies", sa.Text(), nullable=False),
        sa.Column("draft_status", _enum("draft", "in_review", "in_force", "obsolete", name="docstatus", length=20), nullable=False),
        sa.Column("current_version_id", sa.Uuid(), nullable=True),
        sa.Column("context_version_ref", sa.Uuid(), nullable=True),
        sa.Column("stakeholder_version_ref", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scope_statements_tenant_id"), "scope_statements", ["tenant_id"], unique=True)

    op.create_table(
        "scope_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("scope_id", sa.Uuid(), nullable=False),
        sa.Column("kind", _enum("inclusion", "exclusion", name="scopeitemkind", length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["scope_id"], ["scope_statements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scope_items_tenant_id"), "scope_items", ["tenant_id"])
    op.create_index(op.f("ix_scope_items_scope_id"), "scope_items", ["scope_id"])

    op.create_table(
        "document_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("document_type", _enum("context_analysis", "stakeholder_map", "scope_statement", name="doctype"), nullable=False),
        sa.Column("document_id", sa.Uuid(), nullable=False),
        sa.Column("identifier", sa.String(length=40), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", _enum("draft", "in_review", "in_force", "obsolete", name="docstatus", length=20), nullable=False),
        sa.Column("classification", _enum("publico", "uso_interno", "confidencial", "restrito", name="classification", length=30), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("elaborated_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("change_nature", sa.String(length=300), nullable=False),
        sa.Column("content_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_document_versions_tenant_id"), "document_versions", ["tenant_id"])
    op.create_index(op.f("ix_document_versions_document_type"), "document_versions", ["document_type"])
    op.create_index(op.f("ix_document_versions_document_id"), "document_versions", ["document_id"])

    op.create_table(
        "classification_access_policies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_classification_access_policies_tenant_id"), "classification_access_policies", ["tenant_id"], unique=True)

    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute(
            "CREATE TRIGGER IF NOT EXISTS document_versions_no_update BEFORE UPDATE ON document_versions "
            "BEGIN SELECT RAISE(ABORT, 'document_versions is append-only'); END;"
        )
        op.execute(
            "CREATE TRIGGER IF NOT EXISTS document_versions_no_delete BEFORE DELETE ON document_versions "
            "BEGIN SELECT RAISE(ABORT, 'document_versions is append-only'); END;"
        )
    elif dialect == "postgresql":
        op.execute(
            "CREATE OR REPLACE FUNCTION wtn_document_versions_append_only() RETURNS trigger AS $$ "
            "BEGIN RAISE EXCEPTION 'document_versions is append-only'; END; $$ LANGUAGE plpgsql;"
        )
        op.execute("DROP TRIGGER IF EXISTS document_versions_append_only ON document_versions;")
        op.execute(
            "CREATE TRIGGER document_versions_append_only BEFORE UPDATE OR DELETE ON document_versions "
            "FOR EACH ROW EXECUTE FUNCTION wtn_document_versions_append_only();"
        )
        for table in _SCOPED_TABLES:
            op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
            op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
            op.execute(
                f"CREATE POLICY tenant_isolation ON {table} "
                "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
            )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS document_versions_no_update;")
        op.execute("DROP TRIGGER IF EXISTS document_versions_no_delete;")
    elif dialect == "postgresql":
        for table in _SCOPED_TABLES:
            op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
            op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
        op.execute("DROP TRIGGER IF EXISTS document_versions_append_only ON document_versions;")
        op.execute("DROP FUNCTION IF EXISTS wtn_document_versions_append_only();")

    for table in reversed(_SCOPED_TABLES):
        op.drop_table(table)
