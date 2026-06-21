"""US3 — SoA como Documento Controlado: revisão, aprovação, imutabilidade, assinatura opcional."""

import uuid

import pytest


def test_approve_without_review_returns_409(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=h)
    complete_soa(s["org"].id)
    resp = client.post("/soa/approve", headers=h, json={})
    assert resp.status_code == 409


def test_approve_incomplete_returns_422(client, soa_seed, org_headers):
    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=h)
    client.post("/soa/submit-review", headers=h)
    resp = client.post("/soa/approve", headers=h, json={})
    assert resp.status_code == 422
    assert resp.json()["detail"]["incomplete"]


def test_approve_as_consultant_forbidden(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    admin_h = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=admin_h)
    complete_soa(s["org"].id)
    client.post("/soa/submit-review", headers=admin_h)

    cons_h = org_headers(s["consultant"].email, s["org"].id)
    resp = client.post("/soa/approve", headers=cons_h, json={})
    assert resp.status_code == 403


def test_submit_and_approve_creates_signed_version(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=h)
    complete_soa(s["org"].id)
    client.post("/soa/submit-review", headers=h)

    resp = client.post("/soa/approve", headers=h, json={"sign": True, "classification": "confidencial"})
    assert resp.status_code == 201, resp.text
    v = resp.json()
    assert v["version_number"] == 1
    assert v["signed"] is True
    assert v["classification"] == "confidencial"

    versions = client.get("/soa/versions", headers=h).json()
    assert len(versions) == 1


def test_version_is_immutable(client, soa_seed, org_headers, complete_soa, db):
    from wtnapp.models.document_version_model import DocumentVersion

    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=h)
    complete_soa(s["org"].id)
    client.post("/soa/submit-review", headers=h)
    client.post("/soa/approve", headers=h, json={})

    db.rollback()
    version = db.query(DocumentVersion).filter_by(tenant_id=s["org"].id).first()
    assert version is not None
    version.change_nature = "adulterado"
    with pytest.raises(Exception):
        db.commit()
    db.rollback()
