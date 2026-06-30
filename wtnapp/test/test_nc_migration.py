"""Feature 015 — sanidade do schema do domínio NC/PDCA (tabelas/colunas/triggers append-only)."""

from sqlalchemy import inspect, text


def test_nc_tables_columns_and_append_only_triggers(db):
    inspector = inspect(db.bind)
    for table in ("nonconformity", "corrective_action", "nonconformity_verification",
                  "nonconformity_event", "management_review", "improvement", "improvement_event"):
        assert table in inspector.get_table_names()
        assert "tenant_id" in {c["name"] for c in inspector.get_columns(table)}

    # ponteiro do Documento Controlado na análise crítica
    assert "current_version_id" in {c["name"] for c in inspector.get_columns("management_review")}
    # vínculo da NC à constatação de origem (5a)
    assert "source_finding_id" in {c["name"] for c in inspector.get_columns("nonconformity")}

    triggers = db.execute(text("SELECT name FROM sqlite_master WHERE type='trigger'")).scalars().all()
    assert "nonconformity_event_no_update" in triggers
    assert "improvement_event_no_delete" in triggers
