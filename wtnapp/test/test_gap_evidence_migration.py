from pathlib import Path

from sqlalchemy import inspect, text


def test_unified_evidence_tables_include_tenant_columns_indexes_and_sqlite_triggers(db):
    # Feature 014: as evidências do Gap foram unificadas no store transversal `evidence*`.
    inspector = inspect(db.bind)
    for table in ("evidence", "evidence_version", "evidence_link", "evidence_event"):
        assert table in inspector.get_table_names()
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert "tenant_id" in columns
    # As tabelas legadas do 008 deixam de existir (migradas + droppadas).
    for legacy in ("gap_evidence", "gap_evidence_version", "gap_evidence_event"):
        assert legacy not in inspector.get_table_names()

    version_indexes = {index["name"] for index in inspector.get_indexes("evidence_version")}
    link_indexes = {index["name"] for index in inspector.get_indexes("evidence_link")}
    assert "ix_evidence_version_evidence_id" in version_indexes
    assert "ix_evidence_link_target" in link_indexes

    triggers = db.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalars().all()
    assert "evidence_version_no_update" in triggers
    assert "evidence_event_no_delete" in triggers


def test_evidence_migration_documents_postgresql_rls_and_append_only_triggers():
    migration = Path("wtnapp/alembic/versions/c1d2e3f4a509_gap_evidence_attachments.py").read_text()

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "current_setting('app.tenant_id'" in migration
    assert "gap_evidence_version_append_only" in migration
    assert "gap_evidence_event_append_only" in migration
    assert 'server_default=sa.text("1")' not in migration
    assert "server_default=sa.true()" in migration
