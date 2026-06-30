"""Feature 014 / US4 — Planejar e conduzir auditoria interna (programa, auditoria, checklist)."""

import uuid

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _program(client, headers):
    return client.post("/internal-audit/programs", headers=headers, json={"name": "Programa 2026", "objective": "Ciclo anual"})


def _audit(client, headers, program_id, auditor_id, **over):
    body = {"program_id": program_id, "title": "Auditoria A.5", "scope": "Controles A.5", "criteria": "ISO 27001", "auditor_member_id": str(auditor_id)}
    body.update(over)
    return client.post("/internal-audit/audits", headers=headers, json=body)


def test_program_audit_lifecycle_and_code(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "ia-life")
    headers = org_headers(seed["admin"].email, seed["org"].id)

    prog = _program(client, headers)
    assert prog.status_code == 201, prog.text
    program_id = prog.json()["id"]

    audit = _audit(client, headers, program_id, seed["admin"].id)
    assert audit.status_code == 201, audit.text
    assert audit.json()["code"] == "AUD-0001"
    assert audit.json()["status"] == "planned"
    audit_id = audit.json()["id"]

    # 2ª auditoria → AUD-0002
    a2 = _audit(client, headers, program_id, seed["admin"].id)
    assert a2.json()["code"] == "AUD-0002"


def test_auditor_must_be_active_member(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "ia-member")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    program_id = _program(client, headers).json()["id"]
    resp = _audit(client, headers, program_id, uuid.uuid4())  # não é membro
    assert resp.status_code == 422, resp.text


def test_checklist_manual_import_and_transitions(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "ia-checklist")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    program_id = _program(client, headers).json()["id"]
    audit_id = _audit(client, headers, program_id, seed["admin"].id).json()["id"]

    # item manual vinculado a um item do Gap
    manual = client.post(f"/internal-audit/audits/{audit_id}/checklist", headers=headers, json={"criterion": "Verificar política", "target_type": "gap_item", "target_id": str(seed["item"].id)})
    assert manual.status_code == 201, manual.text
    manual_item = manual.json()["id"]

    # importação opcional do escopo do Gap
    imported = client.post(f"/internal-audit/audits/{audit_id}/checklist/import", headers=headers, json={"source": "gap"})
    assert imported.status_code == 201, imported.text
    assert len(imported.json()) > 0

    listing = client.get(f"/internal-audit/audits/{audit_id}/checklist", headers=headers)
    assert listing.status_code == 200 and len(listing.json()) == 1 + len(imported.json())

    # readiness antes de concluir: não pode aprovar (planned + pendentes)
    detail = client.get(f"/internal-audit/audits/{audit_id}", headers=headers).json()
    assert detail["readiness"]["can_approve_report"] is False
    assert detail["readiness"]["pending_items"] >= 1

    # transições: start → in_progress; start de novo → 409
    assert client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "start"}).json()["status"] == "in_progress"
    assert client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "start"}).status_code == 409

    # resolve todos os itens e conclui → gate libera
    for item in client.get(f"/internal-audit/audits/{audit_id}/checklist", headers=headers).json():
        client.put(f"/internal-audit/audits/{audit_id}/checklist/{item['id']}", headers=headers, json={"result": "conforme"})
    assert client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "complete"}).json()["status"] == "completed"

    detail = client.get(f"/internal-audit/audits/{audit_id}", headers=headers).json()
    assert detail["readiness"]["pending_items"] == 0
    assert detail["readiness"]["can_approve_report"] is True
