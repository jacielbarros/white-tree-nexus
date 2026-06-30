"""Feature 014 — Regressão da migração de dados do 008 para o store unificado (T008).

Cria o schema legado `gap_evidence*` num SQLite isolado, popula amostras de dois tenants, roda a
função de migração da revisão `f6a7b8c9d014` e verifica que histórico/hash/autoria foram
preservados, que os vínculos `gap_item` foram criados e que não há vazamento cross-tenant.
"""

import importlib.util
import uuid
from datetime import datetime, timezone
from pathlib import Path

import sqlalchemy as sa

from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink, EvidenceVersion


def _load_migration():
    path = Path("wtnapp/alembic/versions/f6a7b8c9d014_cross_evidence_repository.py")
    spec = importlib.util.spec_from_file_location("mig_f6a7b8c9d014", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _now():
    return datetime.now(timezone.utc)


def _legacy_schema(conn):
    conn.exec_driver_sql("CREATE TABLE organizations (id CHAR(32) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE users (id CHAR(32) PRIMARY KEY)")
    conn.exec_driver_sql("CREATE TABLE gap_assessment_item (id CHAR(32) PRIMARY KEY)")
    conn.exec_driver_sql(
        "CREATE TABLE gap_evidence (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), "
        "assessment_item_id CHAR(32), title VARCHAR(255), description TEXT, classification VARCHAR(30), "
        "status VARCHAR(20), current_version_id CHAR(32), created_by CHAR(32), created_at DATETIME, "
        "updated_at DATETIME, inactivated_by CHAR(32), inactivated_at DATETIME, inactivation_reason VARCHAR(300))"
    )
    conn.exec_driver_sql(
        "CREATE TABLE gap_evidence_version (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), evidence_id CHAR(32), "
        "version_number INTEGER, classification VARCHAR(30), original_filename VARCHAR(255), storage_key VARCHAR(500), "
        "content_hash VARCHAR(64), hash_algorithm VARCHAR(20), encrypted BOOLEAN, encryption_scheme VARCHAR(40), "
        "size_bytes INTEGER, mime_type VARCHAR(120), extension VARCHAR(20), uploaded_by CHAR(32), uploaded_at DATETIME)"
    )
    conn.exec_driver_sql(
        "CREATE TABLE gap_evidence_event (id CHAR(32) PRIMARY KEY, tenant_id CHAR(32), evidence_id CHAR(32), "
        "version_id CHAR(32), assessment_item_id CHAR(32), event_type VARCHAR(40), outcome VARCHAR(20), "
        "actor_id CHAR(32), occurred_at DATETIME, details JSON)"
    )


def test_migration_copies_gap_evidence_into_unified_store_preserving_custody(tmp_path):
    mig = _load_migration()
    engine = sa.create_engine(f"sqlite+pysqlite:///{tmp_path / 'legacy.db'}")
    hexid = lambda: uuid.uuid4().hex

    org_a, org_b = hexid(), hexid()
    user, item_a, item_b = hexid(), hexid(), hexid()
    ev_a, ver_a, evt_a = hexid(), hexid(), hexid()
    ev_b, ver_b = hexid(), hexid()
    hash_a = "a" * 64

    with engine.begin() as conn:
        _legacy_schema(conn)
        # cria as tabelas unificadas via os modelos ORM (tabelas + índices + triggers append-only).
        # `op.create_table` da migração exige o runtime do Alembic, indisponível em teste isolado;
        # o passo testado aqui é a função de migração de dados `_migrate_008_data` (standalone).
        for model in (Evidence, EvidenceVersion, EvidenceLink, EvidenceEvent):
            model.__table__.create(conn)
        for oid in (org_a, org_b):
            conn.exec_driver_sql("INSERT INTO organizations (id) VALUES (?)", (oid,))
        conn.exec_driver_sql("INSERT INTO users (id) VALUES (?)", (user,))
        for iid in (item_a, item_b):
            conn.exec_driver_sql("INSERT INTO gap_assessment_item (id) VALUES (?)", (iid,))
        now = _now().isoformat()
        for eid, tid, iid, cur in ((ev_a, org_a, item_a, ver_a), (ev_b, org_b, item_b, ver_b)):
            conn.exec_driver_sql(
                "INSERT INTO gap_evidence VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (eid, tid, iid, "Policy", None, "uso_interno", "active", cur, user, now, now, None, None, None),
            )
        conn.exec_driver_sql(
            "INSERT INTO gap_evidence_version VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ver_a, org_a, ev_a, 1, "uso_interno", "p.pdf", "key/a.fernet", hash_a, "sha256", 1, "fernet", 10, "application/pdf", ".pdf", user, now),
        )
        conn.exec_driver_sql(
            "INSERT INTO gap_evidence_version VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (ver_b, org_b, ev_b, 1, "uso_interno", "q.pdf", "key/b.fernet", "b" * 64, "sha256", 1, "fernet", 10, None, ".pdf", user, now),
        )
        conn.exec_driver_sql(
            "INSERT INTO gap_evidence_event VALUES (?,?,?,?,?,?,?,?,?,?)",
            (evt_a, org_a, ev_a, ver_a, item_a, "uploaded", "success", user, now, "{}"),
        )
        # executa a migração de dados (standalone) + drop das tabelas legadas (raw, sem op)
        mig._migrate_008_data(conn)
        for legacy in ("gap_evidence_event", "gap_evidence_version", "gap_evidence"):
            conn.exec_driver_sql(f"DROP TABLE {legacy}")

    with engine.connect() as conn:
        # tabelas legadas removidas
        names = sa.inspect(conn).get_table_names()
        assert "gap_evidence" not in names and "gap_evidence_version" not in names

        # evidências preservadas (hash/autoria)
        ev = conn.execute(sa.text("SELECT id, tenant_id, created_by, current_version_id FROM evidence ORDER BY tenant_id")).mappings().all()
        assert {r["id"] for r in ev} == {ev_a, ev_b}
        ver = conn.execute(sa.text("SELECT content_hash, uploaded_by FROM evidence_version WHERE evidence_id=:e"), {"e": ev_a}).mappings().one()
        assert ver["content_hash"] == hash_a and ver["uploaded_by"] == user

        # ponteiro da versão corrente preservado (resolve a FK circular evidence↔version no PG)
        cur = {r["id"]: r["current_version_id"] for r in ev}
        assert cur[ev_a] == ver_a and cur[ev_b] == ver_b

        # vínculos gap_item criados, apontando ao item correto
        links = conn.execute(sa.text("SELECT evidence_id, target_type, target_id FROM evidence_link")).mappings().all()
        assert {(l["evidence_id"], l["target_type"], l["target_id"]) for l in links} == {
            (ev_a, "gap_item", item_a), (ev_b, "gap_item", item_b),
        }

        # evento migrado com target_type=gap_item
        evt = conn.execute(sa.text("SELECT target_type, target_id FROM evidence_event WHERE id=:i"), {"i": evt_a}).mappings().one()
        assert evt["target_type"] == "gap_item" and evt["target_id"] == item_a

        # sem mistura de tenant: cada evidência mantém seu tenant
        for eid, tid in ((ev_a, org_a), (ev_b, org_b)):
            row = conn.execute(sa.text("SELECT tenant_id FROM evidence WHERE id=:i"), {"i": eid}).mappings().one()
            assert row["tenant_id"] == tid
