"""Feature 014 — Isolamento de tenant do repositório transversal de evidências (obrigatório)."""

import uuid

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _configure_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", 128)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _upload(client, headers, target_id):
    return client.post(
        "/evidence",
        headers=headers,
        data={"classification": "uso_interno", "target_type": "gap_item", "target_id": str(target_id)},
        files={"file": ("a.pdf", b"evidence A", "application/pdf")},
    )


def test_cross_tenant_access_is_denied_and_audited(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    a = _seed(db, gap_seed_factory, "ev-iso-a")
    b = _seed(db, gap_seed_factory, "ev-iso-b")
    a_headers = org_headers(a["admin"].email, a["org"].id)
    b_headers = org_headers(b["admin"].email, b["org"].id)

    eid = _upload(client, a_headers, a["item"].id).json()["id"]

    # Org B não acessa a evidência da Org A — sempre 404 genérico
    assert client.get(f"/evidence/{eid}", headers=b_headers).status_code == 404
    assert client.get(f"/evidence/{eid}/download", headers=b_headers).status_code == 404
    assert client.get(f"/evidence/{eid}/history", headers=b_headers).status_code == 404
    assert client.delete(f"/evidence/{eid}", headers=b_headers).status_code == 404
    assert client.post(f"/evidence/{eid}/versions", headers=b_headers, data={"classification": "uso_interno"}, files={"file": ("x.pdf", b"y", "application/pdf")}).status_code == 404
    assert client.post(f"/evidence/{eid}/links", headers=b_headers, json={"target_type": "gap_item", "target_id": str(b["item"].id)}).status_code == 404

    # Repositório central de B nunca lista evidência de A
    assert eid not in {e["id"] for e in client.get("/evidence", headers=b_headers).json()}

    # Tentativas negadas geram audit
    denied = db.query(AuditLog).filter_by(operation="EVIDENCE_ACCESS_DENIED").all()
    assert any(a_row.tenant_id == b["org"].id for a_row in denied)


def test_cannot_link_evidence_to_other_tenant_target(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    a = _seed(db, gap_seed_factory, "ev-iso-link-a")
    b = _seed(db, gap_seed_factory, "ev-iso-link-b")
    a_headers = org_headers(a["admin"].email, a["org"].id)
    eid = _upload(client, a_headers, a["item"].id).json()["id"]

    # vincular a um item do Gap da Org B → alvo não existe no tenant de A → 404
    resp = client.post(f"/evidence/{eid}/links", headers=a_headers, json={"target_type": "gap_item", "target_id": str(b["item"].id)})
    assert resp.status_code == 404, resp.text
