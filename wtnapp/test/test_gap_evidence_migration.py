from pathlib import Path

from sqlalchemy import inspect, text


def test_evidence_tables_include_tenant_columns_indexes_and_sqlite_triggers(db):
    inspector = inspect(db.bind)
    for table in ("gap_evidence", "gap_evidence_version", "gap_evidence_event"):
        assert table in inspector.get_table_names()
        columns = {column["name"] for column in inspector.get_columns(table)}
        assert "tenant_id" in columns

    evidence_indexes = {index["name"] for index in inspector.get_indexes("gap_evidence")}
    version_indexes = {index["name"] for index in inspector.get_indexes("gap_evidence_version")}
    event_indexes = {index["name"] for index in inspector.get_indexes("gap_evidence_event")}

    assert "ix_gap_evidence_tenant_id" in evidence_indexes
    assert "ix_gap_evidence_assessment_item_id" in evidence_indexes
    assert "ix_gap_evidence_version_tenant_id" in version_indexes
    assert "ix_gap_evidence_version_evidence_id" in version_indexes
    assert "ix_gap_evidence_event_tenant_id" in event_indexes
    assert "ix_gap_evidence_event_item_id" in event_indexes

    triggers = db.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalars().all()
    assert "gap_evidence_version_no_update" in triggers
    assert "gap_evidence_event_no_delete" in triggers


def test_evidence_migration_documents_postgresql_rls_and_append_only_triggers():
    migration = Path("wtnapp/alembic/versions/c1d2e3f4a509_gap_evidence_attachments.py").read_text()

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "current_setting('app.tenant_id'" in migration
    assert "gap_evidence_version_append_only" in migration
    assert "gap_evidence_event_append_only" in migration
    assert 'server_default=sa.text("1")' not in migration
    assert "server_default=sa.true()" in migration
