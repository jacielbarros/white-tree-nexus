"""Feature 014 — Isolamento de tenant da Auditoria Interna (obrigatório)."""

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _make_audit(client, headers, auditor_id):
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "P"}).json()["id"]
    audit = client.post("/internal-audit/audits", headers=headers, json={
        "program_id": program_id, "title": "A", "scope": "s", "criteria": "c", "auditor_member_id": str(auditor_id),
    }).json()
    finding = client.post(f"/internal-audit/audits/{audit['id']}/findings", headers=headers, json={
        "finding_type": "nc_menor", "title": "NC", "description": "d",
    }).json()
    return program_id, audit["id"], finding["id"]


def test_org_b_cannot_access_org_a_audit_resources(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "ia-iso-a")
    b = _seed(db, gap_seed_factory, "ia-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)

    program_id, audit_id, finding_id = _make_audit(client, ha, a["admin"].id)

    # Org B nunca vê os recursos de A
    assert audit_id not in {x["id"] for x in client.get("/internal-audit/audits", headers=hb).json()}
    assert program_id not in {x["id"] for x in client.get("/internal-audit/programs", headers=hb).json()}
    assert client.get(f"/internal-audit/audits/{audit_id}", headers=hb).status_code == 404
    assert client.get(f"/internal-audit/audits/{audit_id}/checklist", headers=hb).status_code == 404
    assert client.get(f"/internal-audit/audits/{audit_id}/findings", headers=hb).status_code == 404
    assert client.post(f"/internal-audit/audits/{audit_id}/transition", headers=hb, json={"action": "start"}).status_code == 404
    assert client.put(f"/internal-audit/findings/{finding_id}", headers=hb, json={"finding_type": "observacao", "title": "x", "description": "y"}).status_code == 404
    assert client.delete(f"/internal-audit/findings/{finding_id}", headers=hb).status_code == 404


def test_cannot_target_finding_to_other_tenant_artifact(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "ia-iso-tgt-a")
    b = _seed(db, gap_seed_factory, "ia-iso-tgt-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    program_id = client.post("/internal-audit/programs", headers=ha, json={"name": "P"}).json()["id"]
    audit_id = client.post("/internal-audit/audits", headers=ha, json={
        "program_id": program_id, "title": "A", "scope": "s", "criteria": "c", "auditor_member_id": str(a["admin"].id),
    }).json()["id"]

    # constatação apontando para item do Gap da Org B → 404
    resp = client.post(f"/internal-audit/audits/{audit_id}/findings", headers=ha, json={
        "finding_type": "nc_menor", "title": "x", "description": "y", "target_type": "gap_item", "target_id": str(b["item"].id),
    })
    assert resp.status_code == 404, resp.text
