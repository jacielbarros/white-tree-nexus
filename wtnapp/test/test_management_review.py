"""Feature 015 / US5 — Análise Crítica pela Direção como Documento Controlado (coleção)."""

import uuid

from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import DocType


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    return seed


def _body(**over):
    body = {"title": "Reunião Q2", "review_date": "2026-06-30", "inputs": {}, "outputs": {}}
    body.update(over)
    return body


def _full(**over):
    return _body(inputs={"auditoria": "1 NC maior"}, outputs={"decisoes": "alocar recursos"}, **over)


def test_review_lifecycle_gate_version_and_pdf(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "mr-life")
    h = org_headers(seed["admin"].email, seed["org"].id)

    rid = client.post("/management-reviews", headers=h, json=_body()).json()["id"]
    # incompleta → submit bloqueado
    assert client.post(f"/management-reviews/{rid}/submit-review", headers=h).status_code == 409
    # aprovar antes de revisar → 409
    assert client.post(f"/management-reviews/{rid}/approve", headers=h, json={}).status_code == 409

    # preenche entradas/saídas → submit ok
    client.put(f"/management-reviews/{rid}", headers=h, json=_full())
    assert client.post(f"/management-reviews/{rid}/submit-review", headers=h).status_code == 200

    approved = client.post(f"/management-reviews/{rid}/approve", headers=h, json={"sign": True})
    assert approved.status_code == 201, approved.text
    body = approved.json()
    assert body["version_number"] == 1 and body["signed"] is True
    version_id = body["id"]

    version = db.get(DocumentVersion, uuid.UUID(version_id))
    assert version.document_type == DocType.management_review
    assert version.content_snapshot["inputs"]["auditoria"] == "1 NC maior"
    assert "signature" in version.content_snapshot

    versions = client.get(f"/management-reviews/{rid}/versions", headers=h)
    assert versions.status_code == 200 and len(versions.json()) == 1
    pdf = client.get(f"/management-reviews/{rid}/versions/{version_id}/export", headers=h)
    assert pdf.status_code == 200 and pdf.headers["content-type"] == "application/pdf" and pdf.content[:4] == b"%PDF"


def test_collection_lists_multiple_meetings(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "mr-collection")
    h = org_headers(seed["admin"].email, seed["org"].id)
    client.post("/management-reviews", headers=h, json=_full(title="Q1", review_date="2026-03-31"))
    client.post("/management-reviews", headers=h, json=_full(title="Q2", review_date="2026-06-30"))

    rows = client.get("/management-reviews", headers=h).json()
    assert {r["title"] for r in rows} == {"Q1", "Q2"}  # coleção (uma por reunião)


def test_only_approver_role_can_approve(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "mr-rbac")
    admin_h = org_headers(seed["admin"].email, seed["org"].id)
    consultant_h = org_headers(seed["consultant"].email, seed["org"].id)
    rid = client.post("/management-reviews", headers=admin_h, json=_full()).json()["id"]
    client.post(f"/management-reviews/{rid}/submit-review", headers=admin_h)

    # consultor gere mas não aprova
    assert client.post(f"/management-reviews/{rid}/approve", headers=consultant_h, json={}).status_code == 403
    assert client.post(f"/management-reviews/{rid}/approve", headers=admin_h, json={}).status_code == 201
