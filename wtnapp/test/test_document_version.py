import pytest
from sqlalchemy import text

from wtnapp.models.document_version_model import DocumentVersion


def test_document_lifecycle_approval_requires_permission_and_versions_are_append_only(
    client, context_seed, org_headers, db
):
    consultant_headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    admin_headers = org_headers("admin@ctx-acme.com", context_seed["org"].id)

    submit = client.post("/context/analysis/submit-review", headers=consultant_headers)
    assert submit.status_code == 200, submit.text

    denied = client.post("/context/analysis/approve", headers=consultant_headers, json={})
    assert denied.status_code == 403

    approved = client.post(
        "/context/analysis/approve",
        headers=admin_headers,
        json={"classification": "uso_interno", "change_nature": "Emissao inicial"},
    )
    assert approved.status_code == 201, approved.text
    assert approved.json()["id"]

    # Append-only: UPDATE/DELETE em document_versions são bloqueados pelo gatilho.
    # UPDATE incondicional garante >=1 linha afetada (id do SQLite é CHAR(32) sem hífens).
    with pytest.raises(Exception):
        db.execute(text("UPDATE document_versions SET change_nature='x'"))
        db.commit()
    db.rollback()

    with pytest.raises(Exception):
        db.execute(text("DELETE FROM document_versions"))
        db.commit()
    db.rollback()

    assert db.query(DocumentVersion).count() == 1


def test_second_approval_keeps_single_in_force_via_pointer(client, context_seed, org_headers):
    """FR-012a / T027 — 2ª aprovação cria nova versão; o artefato aponta para exatamente uma vigente."""
    consultant = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    admin = org_headers("admin@ctx-acme.com", context_seed["org"].id)

    client.post("/context/analysis/submit-review", headers=consultant)
    client.post("/context/analysis/approve", headers=admin, json={"classification": "uso_interno"})

    client.put("/context/analysis", headers=consultant, json={"intended_outcomes": "rev2"})
    client.post("/context/analysis/submit-review", headers=consultant)
    v2 = client.post("/context/analysis/approve", headers=admin, json={"classification": "uso_interno"}).json()

    versions = client.get("/context/analysis/versions", headers=consultant).json()
    assert len(versions) == 2
    assert {v["version_number"] for v in versions} == {1, 2}

    analysis = client.get("/context/analysis", headers=consultant).json()
    assert analysis["current_version_id"] == v2["id"]  # exatamente uma "em vigor" (ponteiro)
    assert v2["version_number"] == 2


def test_review_overdue_is_flagged(client, context_seed, org_headers):
    """FR-014 / T028 — artefato com próxima análise crítica vencida é destacado."""
    consultant = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    admin = org_headers("admin@ctx-acme.com", context_seed["org"].id)

    client.post("/context/analysis/submit-review", headers=consultant)
    client.post(
        "/context/analysis/approve",
        headers=admin,
        json={"classification": "uso_interno", "next_review_at": "2020-01-01T00:00:00Z"},
    )
    assert client.get("/context/analysis", headers=consultant).json()["review_overdue"] is True
