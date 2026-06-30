"""Repositório transversal de evidências (Feature 014 / 5a) — tabelas evidence_*.

Cria `evidence`, `evidence_version`, `evidence_link`, `evidence_event` (vínculo polimórfico 1..N),
com RLS + triggers append-only em `evidence_version`/`evidence_event`. Idempotente (o `create_all()`
do startup pode tê-las criado antes).

Resolve os dois heads atuais como **merge**: Feature 007 (gap_guidance) + Feature 013
(soa_risk_normative). A migração de dados da Feature 008 e o domínio de auditoria interna entram em
revisões subsequentes desta feature.

Revision ID: f6a7b8c9d014
Revises: a9b0c1d2e308, d3e4f5a6b217
Create Date: 2026-06-30
"""

from __future__ import annotations

import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f6a7b8c9d014"
down_revision: Union[str, Sequence[str], None] = ("a9b0c1d2e308", "d3e4f5a6b217")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_SCOPED_TABLES = ("evidence", "evidence_version", "evidence_link", "evidence_event")


def _table_exists(conn: sa.engine.Connection, name: str) -> bool:
    return sa.inspect(conn).has_table(name)


def _index_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {idx["name"] for idx in sa.inspect(conn).get_indexes(table)}


def _fk_exists(conn: sa.engine.Connection, table: str, name: str) -> bool:
    return name in {fk.get("name") for fk in sa.inspect(conn).get_foreign_keys(table)}


def _create_index_if_missing(conn, name: str, table: str, columns: list[str]) -> None:
    if _table_exists(conn, table) and not _index_exists(conn, table, name):
        op.create_index(name, table, columns)


def _create_tables(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "evidence"):
        op.create_table(
            "evidence",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
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
    if not _table_exists(conn, "evidence_version"):
        op.create_table(
            "evidence_version",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence.id"), nullable=False),
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
            sa.UniqueConstraint("tenant_id", "evidence_id", "version_number", name="uq_evidence_version_number"),
        )
    if not _table_exists(conn, "evidence_link"):
        op.create_table(
            "evidence_link",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence.id"), nullable=False),
            sa.Column("target_type", sa.String(30), nullable=False),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=False),
            sa.Column("created_by", sa.Uuid(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.UniqueConstraint("tenant_id", "evidence_id", "target_type", "target_id", name="uq_evidence_link_target"),
        )
    if not _table_exists(conn, "evidence_event"):
        op.create_table(
            "evidence_event",
            sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
            sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
            sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence.id"), nullable=True),
            sa.Column("version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_version.id"), nullable=True),
            sa.Column("link_id", sa.Uuid(as_uuid=True), sa.ForeignKey("evidence_link.id"), nullable=True),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("event_type", sa.String(40), nullable=False),
            sa.Column("outcome", sa.String(20), nullable=False),
            sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("details", sa.JSON(), nullable=True),
        )


def _create_indexes(conn: sa.engine.Connection) -> None:
    _create_index_if_missing(conn, "ix_evidence_tenant_id", "evidence", ["tenant_id"])
    _create_index_if_missing(conn, "ix_evidence_status", "evidence", ["status"])
    _create_index_if_missing(conn, "ix_evidence_current_version_id", "evidence", ["current_version_id"])
    _create_index_if_missing(conn, "ix_evidence_created_at", "evidence", ["created_at"])
    _create_index_if_missing(conn, "ix_evidence_version_tenant_id", "evidence_version", ["tenant_id"])
    _create_index_if_missing(conn, "ix_evidence_version_evidence_id", "evidence_version", ["evidence_id"])
    _create_index_if_missing(conn, "ix_evidence_version_hash", "evidence_version", ["content_hash"])
    _create_index_if_missing(conn, "ix_evidence_link_tenant_id", "evidence_link", ["tenant_id"])
    _create_index_if_missing(conn, "ix_evidence_link_evidence_id", "evidence_link", ["evidence_id"])
    _create_index_if_missing(conn, "ix_evidence_link_target", "evidence_link", ["tenant_id", "target_type", "target_id"])
    _create_index_if_missing(conn, "ix_evidence_event_tenant_id", "evidence_event", ["tenant_id"])
    _create_index_if_missing(conn, "ix_evidence_event_evidence_id", "evidence_event", ["evidence_id"])
    _create_index_if_missing(conn, "ix_evidence_event_target", "evidence_event", ["target_type", "target_id"])
    _create_index_if_missing(conn, "ix_evidence_event_type", "evidence_event", ["event_type"])


def _append_only(conn: sa.engine.Connection, table: str) -> None:
    if conn.dialect.name == "postgresql":
        fn = f"wtn_{table}_append_only"
        conn.execute(sa.text(
            f"CREATE OR REPLACE FUNCTION {fn}() RETURNS trigger LANGUAGE plpgsql AS $$ "
            f"BEGIN IF TG_OP IN ('UPDATE','DELETE') THEN RAISE EXCEPTION '{table} is append-only'; "
            f"END IF; RETURN NEW; END; $$;"
        ))
        conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
        conn.execute(sa.text(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {table} "
            f"FOR EACH ROW EXECUTE FUNCTION {fn}();"
        ))
    if conn.dialect.name == "sqlite":
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
            "USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);"
        ))
    if not _fk_exists(conn, "evidence", "fk_evidence_current_version"):
        conn.execute(sa.text(
            "ALTER TABLE evidence ADD CONSTRAINT fk_evidence_current_version "
            "FOREIGN KEY (current_version_id) REFERENCES evidence_version(id)"
        ))


_LEGACY = ("gap_evidence", "gap_evidence_version", "gap_evidence_event")

_EVIDENCE_COLS = (
    "id", "tenant_id", "title", "description", "classification", "status",
    "current_version_id", "created_by", "created_at", "updated_at",
    "inactivated_by", "inactivated_at", "inactivation_reason",
)
_VERSION_COLS = (
    "id", "tenant_id", "evidence_id", "version_number", "classification",
    "original_filename", "storage_key", "content_hash", "hash_algorithm",
    "encrypted", "encryption_scheme", "size_bytes", "mime_type", "extension",
    "uploaded_by", "uploaded_at",
)
_EVENT_COLS = (
    "id", "tenant_id", "evidence_id", "version_id", "event_type", "outcome",
    "actor_id", "occurred_at", "details",
)


def _migrate_008_data(conn: sa.engine.Connection) -> None:
    """Copia evidências do Gap (Feature 008) para o store unificado. Portável e idempotente."""
    if not _table_exists(conn, "gap_evidence") or not _table_exists(conn, "evidence"):
        return
    meta = sa.MetaData()
    evidence_t = sa.Table("evidence", meta, autoload_with=conn)
    version_t = sa.Table("evidence_version", meta, autoload_with=conn)
    event_t = sa.Table("evidence_event", meta, autoload_with=conn)
    link_t = sa.Table("evidence_link", meta, autoload_with=conn)
    # Reflete as tabelas legadas para que tipos (DateTime/JSON/UUID) façam round-trip corretamente
    # em qualquer dialeto (SELECT * via text() perde tipos no SQLite).
    g_evidence = sa.Table("gap_evidence", meta, autoload_with=conn)
    g_version = sa.Table("gap_evidence_version", meta, autoload_with=conn)
    g_event = sa.Table("gap_evidence_event", meta, autoload_with=conn)

    existing = {r[0] for r in conn.execute(sa.text("SELECT id FROM evidence"))}

    ev_src = list(conn.execute(sa.select(g_evidence)).mappings())
    ev_rows, link_rows = [], []
    current_version_map: dict = {}  # evidence_id -> current_version_id (aplicado após inserir versões)
    for r in ev_src:
        if r["id"] in existing:
            continue
        row = {c: r[c] for c in _EVIDENCE_COLS}
        # FK circular evidence.current_version_id ↔ evidence_version.evidence_id (PG): insere com
        # NULL e aponta depois que as versões existirem.
        current_version_map[r["id"]] = row["current_version_id"]
        row["current_version_id"] = None
        ev_rows.append(row)
        link_rows.append({
            "id": str(uuid.uuid4()), "tenant_id": r["tenant_id"], "evidence_id": r["id"],
            "target_type": "gap_item", "target_id": r["assessment_item_id"],
            "created_by": r["created_by"], "created_at": r["created_at"], "active": True,
        })
    if ev_rows:
        conn.execute(evidence_t.insert(), ev_rows)
        conn.execute(link_t.insert(), link_rows)

    ver_src = list(conn.execute(sa.select(g_version)).mappings())
    ver_rows = [{c: r[c] for c in _VERSION_COLS} for r in ver_src if r["evidence_id"] not in existing]
    if ver_rows:
        conn.execute(version_t.insert(), ver_rows)

    evt_src = list(conn.execute(sa.select(g_event)).mappings())
    evt_rows = []
    for r in evt_src:
        if r["evidence_id"] in existing:
            continue
        row = {c: r[c] for c in _EVENT_COLS}
        row["link_id"] = None
        row["target_type"] = "gap_item" if r["assessment_item_id"] is not None else None
        row["target_id"] = r["assessment_item_id"]
        evt_rows.append(row)
    if evt_rows:
        conn.execute(event_t.insert(), evt_rows)

    # Agora que as versões existem, aponta a versão corrente de cada evidência (resolve a FK).
    for eid, vid in current_version_map.items():
        if vid is not None:
            conn.execute(evidence_t.update().where(evidence_t.c.id == eid).values(current_version_id=vid))


def _drop_legacy(conn: sa.engine.Connection) -> None:
    if not _table_exists(conn, "gap_evidence"):
        return
    if conn.dialect.name == "postgresql":
        for table in ("gap_evidence_version", "gap_evidence_event"):
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS wtn_{table}_append_only()"))
        for table in _LEGACY:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
    if conn.dialect.name == "sqlite":
        for trig in ("gap_evidence_version_no_update", "gap_evidence_version_no_delete",
                     "gap_evidence_event_no_update", "gap_evidence_event_no_delete"):
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {trig};"))
    op.drop_table("gap_evidence_event")
    op.drop_table("gap_evidence_version")
    op.drop_table("gap_evidence")


def upgrade() -> None:
    conn = op.get_bind()
    _create_tables(conn)
    _create_indexes(conn)
    _append_only(conn, "evidence_version")
    _append_only(conn, "evidence_event")
    _create_rls(conn)
    # Feature 008 → unificação (T007): migra dados e remove as tabelas legadas.
    _migrate_008_data(conn)
    _drop_legacy(conn)


def _recreate_legacy(conn: sa.engine.Connection) -> None:
    """Recria as tabelas do 008 e copia de volta as evidências vinculadas a `gap_item`."""
    if _table_exists(conn, "gap_evidence"):
        return
    op.create_table(
        "gap_evidence",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("assessment_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment_item.id"), nullable=False),
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
    op.create_table(
        "gap_evidence_event",
        sa.Column("id", sa.Uuid(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.Uuid(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("evidence_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_evidence.id"), nullable=True),
        sa.Column("version_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_evidence_version.id"), nullable=True),
        sa.Column("assessment_item_id", sa.Uuid(as_uuid=True), sa.ForeignKey("gap_assessment_item.id"), nullable=True),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("actor_id", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
    )
    # Copia de volta apenas evidências vinculadas a gap_item.
    links = {
        r["evidence_id"]: r["target_id"]
        for r in conn.execute(sa.text(
            "SELECT evidence_id, target_id FROM evidence_link WHERE target_type='gap_item' AND active=1"
        )).mappings()
    } if conn.dialect.name == "sqlite" else {
        r["evidence_id"]: r["target_id"]
        for r in conn.execute(sa.text(
            "SELECT evidence_id, target_id FROM evidence_link WHERE target_type='gap_item' AND active=true"
        )).mappings()
    }
    if not links:
        return
    meta = sa.MetaData()
    g_ev = sa.Table("gap_evidence", meta, autoload_with=conn)
    g_ver = sa.Table("gap_evidence_version", meta, autoload_with=conn)
    g_evt = sa.Table("gap_evidence_event", meta, autoload_with=conn)
    ev_rows = []
    for r in conn.execute(sa.text("SELECT * FROM evidence")).mappings():
        if r["id"] not in links:
            continue
        row = {c: r[c] for c in _EVIDENCE_COLS}
        row["assessment_item_id"] = links[r["id"]]
        ev_rows.append(row)
    if ev_rows:
        conn.execute(g_ev.insert(), ev_rows)
        ver_rows = [
            {c: r[c] for c in _VERSION_COLS}
            for r in conn.execute(sa.text("SELECT * FROM evidence_version")).mappings()
            if r["evidence_id"] in links
        ]
        if ver_rows:
            conn.execute(g_ver.insert(), ver_rows)
        evt_rows = []
        for r in conn.execute(sa.text("SELECT * FROM evidence_event")).mappings():
            if r["evidence_id"] not in links:
                continue
            row = {c: r[c] for c in _EVENT_COLS}
            row["assessment_item_id"] = r["target_id"]
            evt_rows.append(row)
        if evt_rows:
            conn.execute(g_evt.insert(), evt_rows)


def downgrade() -> None:
    conn = op.get_bind()
    _recreate_legacy(conn)
    if conn.dialect.name == "postgresql":
        for table in _SCOPED_TABLES:
            conn.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation ON {table};"))
            conn.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;"))
        conn.execute(sa.text("ALTER TABLE evidence DROP CONSTRAINT IF EXISTS fk_evidence_current_version"))
        for table in ("evidence_version", "evidence_event"):
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_append_only ON {table}"))
            conn.execute(sa.text(f"DROP FUNCTION IF EXISTS wtn_{table}_append_only()"))
    if conn.dialect.name == "sqlite":
        for table in ("evidence_version", "evidence_event"):
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_update;"))
            conn.execute(sa.text(f"DROP TRIGGER IF EXISTS {table}_no_delete;"))
    op.drop_table("evidence_event")
    op.drop_table("evidence_link")
    op.drop_table("evidence_version")
    op.drop_table("evidence")
