"""Feature 015 / US6 — Melhorias (10.1) + visão de ciclo PDCA (read-only) fechando o loop."""

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.internal_audit_model import InternalAudit, InternalAuditFinding, InternalAuditProgram
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import AuditFindingType, DocStatus, InternalAuditStatus, SgsiArtifactType


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _finding_on(db, org, user, item):
    program = InternalAuditProgram(tenant_id=org.id, name="P", created_by=user.id)
    db.add(program); db.flush()
    audit = InternalAudit(tenant_id=org.id, program_id=program.id, code="AUD-0001", title="A", scope="s", criteria="c", auditor_member_id=user.id, status=InternalAuditStatus.in_progress, draft_status=DocStatus.draft, created_by=user.id)
    db.add(audit); db.flush()
    f = InternalAuditFinding(tenant_id=org.id, audit_id=audit.id, finding_type=AuditFindingType.nc_menor, title="Constatação", description="d", promotable=True, target_type=SgsiArtifactType.gap_item, target_id=item.id, created_by=user.id)
    db.add(f); db.commit()
    return f


def _improvement(client, h, **over):
    body = {"title": "Melhoria", "description": "d", "origin": "audit"}
    body.update(over)
    return client.post("/improvements", headers=h, json=body)


def test_create_and_filter_improvements(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "imp-create")
    h = org_headers(seed["admin"].email, seed["org"].id)
    r = _improvement(client, h, origin="nonconformity", target_type="gap_item", target_id=str(seed["item"].id))
    assert r.status_code == 201 and r.json()["code"] == "IMP-0001"
    _improvement(client, h, origin="suggestion")

    by_origin = client.get("/improvements", headers=h, params={"origin": "nonconformity"}).json()
    assert {i["origin"] for i in by_origin} == {"nonconformity"}


def test_pdca_cycle_aggregates_findings_ncs_improvements_readonly(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "imp-pdca")
    h = org_headers(seed["admin"].email, seed["org"].id)
    item = seed["item"]
    _finding_on(db, seed["org"], seed["admin"], item)
    client.post("/nonconformities", headers=h, json={"origin": "audit_finding", "title": "NC", "description": "d", "severity": "menor", "target_type": "gap_item", "target_id": str(item.id)})
    _improvement(client, h, origin="audit", target_type="gap_item", target_id=str(item.id))

    resp = client.get("/improvements/pdca", headers=h, params={"target_type": "gap_item", "target_id": str(item.id)})
    assert resp.status_code == 200, resp.text
    kinds = {e["kind"] for e in resp.json()}
    assert {"finding", "nonconformity", "improvement"} <= kinds
    phases = {e["phase"] for e in resp.json()}
    assert "check" in phases and "act" in phases
    # ordem cronológica
    times = [e["occurred_at"] for e in resp.json()]
    assert times == sorted(times)


def test_pdca_tenant_isolation(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "imp-iso-a")
    b = _seed(db, gap_seed_factory, "imp-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)
    _improvement(client, ha, target_type="gap_item", target_id=str(a["item"].id))

    # Org B nunca vê melhorias/PDCA da Org A
    assert client.get("/improvements", headers=hb).json() == []
    assert client.get("/improvements/pdca", headers=hb, params={"target_type": "gap_item", "target_id": str(a["item"].id)}).json() == []
