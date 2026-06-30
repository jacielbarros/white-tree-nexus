"""Feature 014 / US8 — Dashboard do módulo (contagens) + readiness na esteira."""

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _configure_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", 256)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _audit_with_findings(client, headers, seed):
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "P"}).json()["id"]
    audit_id = client.post("/internal-audit/audits", headers=headers, json={"program_id": program_id, "title": "A", "scope": "s", "criteria": "c", "auditor_member_id": str(seed["admin"].id)}).json()["id"]
    for ftype in ("nc_maior", "conforme"):
        client.post(f"/internal-audit/audits/{audit_id}/findings", headers=headers, json={"finding_type": ftype, "title": ftype, "description": "d"})
    return audit_id


def test_module_dashboard_counts(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed(db, gap_seed_factory, "am-counts")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    client.post("/evidence", headers=headers, data={"classification": "confidencial", "target_type": "gap_item", "target_id": str(seed["item"].id)}, files={"file": ("e.pdf", b"x", "application/pdf")})
    audit_id = _audit_with_findings(client, headers, seed)

    dash = client.get("/internal-audit/dashboard", headers=headers)
    assert dash.status_code == 200, dash.text
    body = dash.json()
    assert body["evidence_by_status"].get("active") == 1
    assert body["evidence_by_classification"].get("confidencial") == 1
    assert body["audits_by_status"].get("planned") == 1
    assert body["findings_by_type"].get("nc_maior") == 1
    assert body["findings_by_type"].get("conforme") == 1


def test_module_dashboard_isolation(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    a = _seed(db, gap_seed_factory, "am-iso-a")
    b = _seed(db, gap_seed_factory, "am-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)
    _audit_with_findings(client, ha, a)

    body_b = client.get("/internal-audit/dashboard", headers=hb).json()
    assert body_b["audits_by_status"] == {}  # tenant B não vê auditorias de A
    assert body_b["findings_by_type"] == {}


def test_readiness_card_reflects_audit_state(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "am-readiness")
    headers = org_headers(seed["admin"].email, seed["org"].id)

    # sem auditorias → card not_started
    card = next(c for c in client.get("/dashboard", headers=headers).json()["cards"] if c["id"] == "internal_audit")
    assert card["not_started"] is True

    # cria + conduz uma auditoria → card deixa de ser not_started
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "P"}).json()["id"]
    audit_id = client.post("/internal-audit/audits", headers=headers, json={"program_id": program_id, "title": "A", "scope": "s", "criteria": "c", "auditor_member_id": str(seed["admin"].id)}).json()["id"]
    client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "start"})

    card = next(c for c in client.get("/dashboard", headers=headers).json()["cards"] if c["id"] == "internal_audit")
    assert card["not_started"] is False
    assert card["next_action"]["label"] == "Conduzir auditoria"
