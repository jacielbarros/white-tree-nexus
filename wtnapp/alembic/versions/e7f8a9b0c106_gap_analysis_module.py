"""Gap Analysis module — tabelas de seed, catálogo, avaliação e atribuição.

Revision ID: e7f8a9b0c106
Revises: d6e7f8a9b005
Create Date: 2026-06-20
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa

revision = "e7f8a9b0c106"
down_revision = "d6e7f8a9b005"
branch_labels = None
depends_on = None


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _seed_base_catalog(conn: sa.engine.Connection) -> None:
    """Carga idempotente do seed 2022.1 — APENAS as colunas existentes nesta revisão.

    NÃO usa o ORM `GapSeedItem` (que já declara os campos de orientação da Feature 007,
    `referencia`/`como_avaliar`/... e a tabela `gap_legend_entry`, inexistentes aqui), pois isso
    fazia o `alembic upgrade head` falhar a partir de um banco zerado com
    "no such column: gap_seed_item.referencia". A orientação e a legenda são preenchidas adiante
    pela migration de backfill `84c5c822d7b1`, depois que `a9b0c1d2e308` adiciona as colunas/tabelas.
    """
    from wtnapp.data.iso27001_seed import SEED_DESCRIPTION, SEED_VERSION, build_seed_items

    version_t = sa.table(
        "gap_seed_version",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("version", sa.String()),
        sa.column("description", sa.String()),
        sa.column("created_at", sa.DateTime(timezone=True)),
    )
    item_t = sa.table(
        "gap_seed_item",
        sa.column("id", sa.Uuid(as_uuid=True)),
        sa.column("seed_version_id", sa.Uuid(as_uuid=True)),
        sa.column("dimension", sa.String()),
        sa.column("ref_code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("theme", sa.String()),
        sa.column("objective", sa.Text()),
        sa.column("order", sa.Integer()),
    )

    existing = conn.execute(
        sa.select(version_t.c.id).where(version_t.c.version == SEED_VERSION)
    ).fetchone()
    if existing is None:
        version_id = uuid.uuid4()
        conn.execute(version_t.insert().values(
            id=version_id, version=SEED_VERSION, description=SEED_DESCRIPTION,
            created_at=datetime.now(timezone.utc),
        ))
    else:
        version_id = existing[0]

    have = {
        row[0]
        for row in conn.execute(
            sa.select(item_t.c.ref_code).where(item_t.c.seed_version_id == version_id)
        ).fetchall()
    }
    rows = [
        {
            "id": uuid.uuid4(),
            "seed_version_id": version_id,
            "dimension": it["dimension"].value,
            "ref_code": it["ref_code"],
            "name": it["name"],
            "theme": it["theme"].value if it["theme"] is not None else None,
            "objective": it["objective"],
            "order": it["order"],
        }
        for it in build_seed_items()
        if it["ref_code"] not in have
    ]
    if rows:
        conn.execute(item_t.insert(), rows)


def upgrade() -> None:
    conn = op.get_bind()

    # -----------------------------------------------------------------
    # Tabelas compartilhadas da plataforma (sem tenant_id, sem RLS)
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_seed_version"):
        op.create_table(
            "gap_seed_version",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("version", sa.String(20), nullable=False, unique=True),
            sa.Column("description", sa.String(300), nullable=False, default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    if not _table_exists(conn, "gap_seed_item"):
        op.create_table(
            "gap_seed_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("seed_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_seed_version.id"), nullable=False),
            sa.Column("dimension", sa.String(20), nullable=False),
            sa.Column("ref_code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("theme", sa.String(20), nullable=True),
            sa.Column("objective", sa.Text, nullable=False, default=""),
            sa.Column("order", sa.Integer, nullable=False, default=0),
            sa.UniqueConstraint("seed_version_id", "ref_code", name="uq_gap_seed_item_version_ref"),
        )
        op.create_index("ix_gap_seed_item_seed_version_id", "gap_seed_item", ["seed_version_id"])
        op.create_index("ix_gap_seed_item_dimension", "gap_seed_item", ["dimension"])
        op.create_index("ix_gap_seed_item_theme", "gap_seed_item", ["theme"])

    # -----------------------------------------------------------------
    # Catálogo editável por organização (com tenant_id + RLS)
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_catalog_item"):
        op.create_table(
            "gap_catalog_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("seed_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_seed_item.id"), nullable=True),
            sa.Column("dimension", sa.String(20), nullable=False),
            sa.Column("ref_code", sa.String(20), nullable=False),
            sa.Column("name", sa.String(300), nullable=False),
            sa.Column("theme", sa.String(20), nullable=True),
            sa.Column("objective", sa.Text, nullable=False, default=""),
            sa.Column("order", sa.Integer, nullable=False, default=0),
            sa.Column("is_custom", sa.Boolean, nullable=False, default=False),
            sa.Column("is_discontinued", sa.Boolean, nullable=False, default=False),
            sa.Column("group_label", sa.String(120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", "ref_code", name="uq_gap_catalog_item_tenant_ref"),
        )
        op.create_index("ix_gap_catalog_item_tenant_id", "gap_catalog_item", ["tenant_id"])
        op.create_index("ix_gap_catalog_item_dimension", "gap_catalog_item", ["dimension"])
        op.create_index("ix_gap_catalog_item_theme", "gap_catalog_item", ["theme"])
        op.create_index("ix_gap_catalog_item_seed_item_id", "gap_catalog_item", ["seed_item_id"])

    # -----------------------------------------------------------------
    # Avaliação (matriz) — artefato único por org
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_assessment"):
        op.create_table(
            "gap_assessment",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("seed_version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_seed_version.id"), nullable=True),
            sa.Column("draft_status", sa.String(20), nullable=False, default="draft"),
            sa.Column("current_version_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("tenant_id", name="uq_gap_assessment_tenant"),
        )
        op.create_index("ix_gap_assessment_tenant_id", "gap_assessment", ["tenant_id"])

    # -----------------------------------------------------------------
    # Itens de avaliação
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_assessment_item"):
        op.create_table(
            "gap_assessment_item",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("assessment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment.id"), nullable=False),
            sa.Column("catalog_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_catalog_item.id"), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, default="not_filled"),
            sa.Column("findings", sa.Text, nullable=True),
            sa.Column("actions", sa.Text, nullable=True),
            sa.Column("priority", sa.String(20), nullable=True),
            sa.Column("responsible", sa.String(200), nullable=True),
            sa.Column("deadline", sa.Date, nullable=True),
            sa.Column("evidence_ref", sa.Text, nullable=True),
            sa.Column("notes", sa.Text, nullable=True),
            sa.Column("exclusion_justification", sa.Text, nullable=True),
            sa.Column("maturity_level", sa.Integer, nullable=True),
            sa.Column("effort_estimate", sa.String(60), nullable=True),
            sa.Column("soa_ref", sa.String(60), nullable=True),
            sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("assessment_id", "catalog_item_id", name="uq_gap_assessment_item_catalog"),
        )
        op.create_index("ix_gap_assessment_item_tenant_id", "gap_assessment_item", ["tenant_id"])
        op.create_index("ix_gap_assessment_item_assessment_id", "gap_assessment_item", ["assessment_id"])
        op.create_index("ix_gap_assessment_item_status", "gap_assessment_item", ["status"])

    # -----------------------------------------------------------------
    # Histórico de item — append-only
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_assessment_item_event"):
        op.create_table(
            "gap_assessment_item_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment_item.id"), nullable=False),
            sa.Column("field", sa.String(40), nullable=False),
            sa.Column("old_value", sa.String(120), nullable=True),
            sa.Column("new_value", sa.String(120), nullable=True),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_gap_assessment_item_event_tenant_id", "gap_assessment_item_event", ["tenant_id"])
        op.create_index("ix_gap_assessment_item_event_item_id", "gap_assessment_item_event", ["item_id"])

    # -----------------------------------------------------------------
    # Condução atribuível (US5) — gap_assignment
    # -----------------------------------------------------------------

    if not _table_exists(conn, "gap_assignment"):
        op.create_table(
            "gap_assignment",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("assessment_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment.id"), nullable=False),
            sa.Column("scope", sa.String(20), nullable=False, default="whole"),
            sa.Column("scope_theme", sa.String(20), nullable=True),
            sa.Column("status", sa.String(20), nullable=False, default="pending"),
            sa.Column("respondent_user_id", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("respondent_email", sa.String(320), nullable=True),
            sa.Column("respondent_token_hash", sa.String(64), nullable=True, unique=True),
            sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("instructions", sa.Text, nullable=True),
            sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "(respondent_user_id IS NOT NULL AND respondent_token_hash IS NULL) OR "
                "(respondent_user_id IS NULL AND respondent_token_hash IS NOT NULL)",
                name="ck_gap_assignment_respondent",
            ),
        )
        op.create_index("ix_gap_assignment_tenant_id", "gap_assignment", ["tenant_id"])
        op.create_index("ix_gap_assignment_assessment_id", "gap_assignment", ["assessment_id"])
        op.create_index("ix_gap_assignment_status", "gap_assignment", ["status"])

    # -----------------------------------------------------------------
    # RLS nas tabelas por-org (PostgreSQL only — idempotente)
    # -----------------------------------------------------------------

    rls_tables = [
        "gap_catalog_item",
        "gap_assessment",
        "gap_assessment_item",
        "gap_assessment_item_event",
        "gap_assignment",
    ]

    if conn.dialect.name == "postgresql":
        for table in rls_tables:
            conn.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            conn.execute(sa.text(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"))
            conn.execute(sa.text(
                f"CREATE POLICY {table}_tenant_isolation ON {table} "
                f"USING (tenant_id::text = current_setting('app.tenant_id', true))"
            ))

        # Gatilho append-only em gap_assessment_item_event (idempotente)
        conn.execute(sa.text("""
            CREATE OR REPLACE FUNCTION gap_item_event_append_only()
            RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF TG_OP IN ('UPDATE', 'DELETE') THEN
                    RAISE EXCEPTION 'gap_assessment_item_event é append-only';
                END IF;
                RETURN NEW;
            END;
            $$;
        """))
        conn.execute(sa.text("""
            DROP TRIGGER IF EXISTS trg_gap_item_event_append_only ON gap_assessment_item_event
        """))
        conn.execute(sa.text("""
            CREATE TRIGGER trg_gap_item_event_append_only
            BEFORE UPDATE OR DELETE ON gap_assessment_item_event
            FOR EACH ROW EXECUTE FUNCTION gap_item_event_append_only();
        """))

    # SQLite: gatilho leve para testes
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS gap_item_event_no_update
            BEFORE UPDATE ON gap_assessment_item_event
            BEGIN
                SELECT RAISE(ABORT, 'gap_assessment_item_event is append-only');
            END;
        """))
        conn.execute(sa.text("""
            CREATE TRIGGER IF NOT EXISTS gap_item_event_no_delete
            BEFORE DELETE ON gap_assessment_item_event
            BEGIN
                SELECT RAISE(ABORT, 'gap_assessment_item_event is append-only');
            END;
        """))

    # -----------------------------------------------------------------
    # Carga idempotente do seed 2022.1 (colunas-base desta revisão; orientação/legenda da
    # Feature 007 são preenchidas pela migration de backfill 84c5c822d7b1).
    # -----------------------------------------------------------------
    _seed_base_catalog(conn)


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        conn.execute(sa.text("DROP TRIGGER IF EXISTS trg_gap_item_event_append_only ON gap_assessment_item_event"))
        conn.execute(sa.text("DROP FUNCTION IF EXISTS gap_item_event_append_only()"))

    op.drop_table("gap_assignment")
    op.drop_table("gap_assessment_item_event")
    op.drop_table("gap_assessment_item")
    op.drop_table("gap_assessment")
    op.drop_table("gap_catalog_item")
    op.drop_table("gap_seed_item")
    op.drop_table("gap_seed_version")
