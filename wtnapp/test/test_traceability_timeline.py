"""Feature 014 / US7 — Timeline de rastreabilidade (read-only) por artefato."""

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import MembershipStatus, Role


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
    items = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).limit(2).all()
    seed["item"], seed["empty_item"] = items[0], items[1]
    return seed


def _attach_evidence_and_finding(client, headers, seed):
    client.post("/evidence", headers=headers, data={"classification": "uso_interno", "target_type": "gap_item", "target_id": str(seed["item"].id)}, files={"file": ("e.pdf", b"prova", "application/pdf")})
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "P"}).json()["id"]
    audit_id = client.post("/internal-audit/audits", headers=headers, json={"program_id": program_id, "title": "A", "scope": "s", "criteria": "c", "auditor_member_id": str(seed["admin"].id)}).json()["id"]
    client.post(f"/internal-audit/audits/{audit_id}/findings", headers=headers, json={"finding_type": "nc_menor", "title": "NC item", "description": "d", "target_type": "gap_item", "target_id": str(seed["item"].id)})


def test_timeline_aggregates_evidence_events_and_findings_chronologically(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed(db, gap_seed_factory, "tl-main")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    _attach_evidence_and_finding(client, headers, seed)

    resp = client.get("/traceability/timeline", headers=headers, params={"target_type": "gap_item", "target_id": str(seed["item"].id)})
    assert resp.status_code == 200, resp.text
    entries = resp.json()
    kinds = {e["kind"] for e in entries}
    assert {"evidence", "event", "finding"} <= kinds
    # ordem cronológica decrescente
    times = [e["occurred_at"] for e in entries]
    assert times == sorted(times, reverse=True)
    # só metadados — nenhum storage_key/conteúdo
    import json as _json
    blob = _json.dumps(entries)
    assert "storage_key" not in blob and "prova" not in blob


def test_timeline_empty_state(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "tl-empty")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    resp = client.get("/traceability/timeline", headers=headers, params={"target_type": "gap_item", "target_id": str(seed["empty_item"].id)})
    assert resp.status_code == 200 and resp.json() == []


def test_timeline_tenant_isolation(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    a = _seed(db, gap_seed_factory, "tl-iso-a")
    b = _seed(db, gap_seed_factory, "tl-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)
    _attach_evidence_and_finding(client, ha, a)
    # Org B consultando o alvo da Org A → 404 genérico
    resp = client.get("/traceability/timeline", headers=hb, params={"target_type": "gap_item", "target_id": str(a["item"].id)})
    assert resp.status_code == 404, resp.text


def test_timeline_requires_module_and_evidence_permissions(client, db, gap_seed, gap_seed_factory, org_headers, factory):
    seed = _seed(db, gap_seed_factory, "tl-rbac")
    guest = factory.user("guest@tl-rbac.com", full_name="Guest")
    factory.membership(guest, seed["org"], Role.guest_collaborator, MembershipStatus.active)
    headers = org_headers(guest.email, seed["org"].id)
    # convidado não tem view_gap/view_evidence → 403
    resp = client.get("/traceability/timeline", headers=headers, params={"target_type": "gap_item", "target_id": str(seed["item"].id)})
    assert resp.status_code == 403, resp.text
