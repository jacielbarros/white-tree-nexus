"""Feature 014 / US6 — Relatório de auditoria como Documento Controlado (gate, aprovação, PDF)."""

import uuid

from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import DocType


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _audit_with_content(client, headers, seed):
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "P"}).json()["id"]
    audit_id = client.post("/internal-audit/audits", headers=headers, json={
        "program_id": program_id, "title": "Auditoria A.5", "scope": "Controles A.5",
        "criteria": "ISO 27001", "auditor_member_id": str(seed["admin"].id),
    }).json()["id"]
    client.post(f"/internal-audit/audits/{audit_id}/checklist", headers=headers, json={
        "criterion": "Verificar política", "target_type": "gap_item", "target_id": str(seed["item"].id),
    })
    client.post(f"/internal-audit/audits/{audit_id}/findings", headers=headers, json={
        "finding_type": "nc_menor", "title": "NC", "description": "desvio identificado",
    })
    return audit_id


def _complete_and_resolve(client, headers, audit_id):
    client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "start"})
    client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "complete"})
    for item in client.get(f"/internal-audit/audits/{audit_id}/checklist", headers=headers).json():
        client.put(f"/internal-audit/audits/{audit_id}/checklist/{item['id']}", headers=headers, json={"result": "conforme"})


def test_report_gate_blocks_until_completed_and_no_pending(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "rep-gate")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    audit_id = _audit_with_content(client, headers, seed)

    # planned + pendente → gate bloqueia submit-review
    assert client.post(f"/internal-audit/audits/{audit_id}/report/submit-review", headers=headers).status_code == 409

    client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "start"})
    client.post(f"/internal-audit/audits/{audit_id}/transition", headers=headers, json={"action": "complete"})
    # completed mas com item pendente → ainda bloqueia
    assert client.post(f"/internal-audit/audits/{audit_id}/report/submit-review", headers=headers).status_code == 409

    for item in client.get(f"/internal-audit/audits/{audit_id}/checklist", headers=headers).json():
        client.put(f"/internal-audit/audits/{audit_id}/checklist/{item['id']}", headers=headers, json={"result": "conforme"})
    assert client.post(f"/internal-audit/audits/{audit_id}/report/submit-review", headers=headers).status_code == 200


def test_report_approve_freezes_immutable_version_and_exports_pdf(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "rep-approve")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    audit_id = _audit_with_content(client, headers, seed)
    _complete_and_resolve(client, headers, audit_id)

    # aprovar antes de revisar → 409
    assert client.post(f"/internal-audit/audits/{audit_id}/report/approve", headers=headers, json={}).status_code == 409

    client.post(f"/internal-audit/audits/{audit_id}/report/submit-review", headers=headers)
    approved = client.post(f"/internal-audit/audits/{audit_id}/report/approve", headers=headers, json={"sign": True})
    assert approved.status_code == 201, approved.text
    body = approved.json()
    assert body["version_number"] == 1 and body["signed"] is True
    version_id = body["id"]

    # snapshot imutável reflete escopo/itens/constatações
    version = db.get(DocumentVersion, uuid.UUID(version_id))
    assert version.document_type == DocType.internal_audit_report
    snap = version.content_snapshot
    assert snap["scope"] == "Controles A.5"
    assert snap["findings_by_type"]["nc_menor"] == 1
    assert snap["summary"]["checklist_total"] == 1
    assert "signature" in snap

    # versões e export PDF
    versions = client.get(f"/internal-audit/audits/{audit_id}/report/versions", headers=headers)
    assert versions.status_code == 200 and len(versions.json()) == 1
    pdf = client.get(f"/internal-audit/audits/{audit_id}/report/versions/{version_id}/export", headers=headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content[:4] == b"%PDF"


def test_only_approver_role_can_approve_report(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "rep-rbac")
    admin_h = org_headers(seed["admin"].email, seed["org"].id)
    consultant_h = org_headers(seed["consultant"].email, seed["org"].id)
    audit_id = _audit_with_content(client, admin_h, seed)
    _complete_and_resolve(client, admin_h, audit_id)
    client.post(f"/internal-audit/audits/{audit_id}/report/submit-review", headers=admin_h)

    # consultor tem manage mas não approve_audit_report
    assert client.post(f"/internal-audit/audits/{audit_id}/report/approve", headers=consultant_h, json={}).status_code == 403
    assert client.post(f"/internal-audit/audits/{audit_id}/report/approve", headers=admin_h, json={}).status_code == 201
