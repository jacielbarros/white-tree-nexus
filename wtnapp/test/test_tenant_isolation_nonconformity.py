"""Feature 015 — Isolamento de tenant do domínio de NC (obrigatório)."""

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.internal_audit_model import InternalAudit, InternalAuditFinding, InternalAuditProgram
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import AuditFindingType, DocStatus, InternalAuditStatus


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    return seed


def _finding(db, org, user):
    program = InternalAuditProgram(tenant_id=org.id, name="P", created_by=user.id)
    db.add(program); db.flush()
    audit = InternalAudit(tenant_id=org.id, program_id=program.id, code="AUD-0001", title="A", scope="s", criteria="c", auditor_member_id=user.id, status=InternalAuditStatus.in_progress, draft_status=DocStatus.draft, created_by=user.id)
    db.add(audit); db.flush()
    f = InternalAuditFinding(tenant_id=org.id, audit_id=audit.id, finding_type=AuditFindingType.nc_menor, title="NC", description="d", promotable=True, created_by=user.id)
    db.add(f); db.commit(); db.refresh(f)
    return f


def test_org_b_cannot_access_org_a_nc(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "nc-iso-a")
    b = _seed(db, gap_seed_factory, "nc-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)

    nc_id = client.post("/nonconformities", headers=ha, json={"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}).json()["id"]

    assert nc_id not in {n["id"] for n in client.get("/nonconformities", headers=hb).json()}
    assert client.get(f"/nonconformities/{nc_id}", headers=hb).status_code == 404
    assert client.put(f"/nonconformities/{nc_id}", headers=hb, json={"origin": "incident", "title": "x", "description": "y", "severity": "menor"}).status_code == 404
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=hb, json={"action": "start"}).status_code == 404
    assert client.get(f"/nonconformities/{nc_id}/actions", headers=hb).status_code == 404


def test_cannot_promote_other_tenant_finding(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "nc-iso-pa")
    b = _seed(db, gap_seed_factory, "nc-iso-pb")
    ha = org_headers(a["admin"].email, a["org"].id)
    finding_b = _finding(db, b["org"], b["admin"])

    # Org A tenta promover constatação da Org B → 404 (não existe no tenant de A)
    resp = client.post("/nonconformities/promote", headers=ha, json={"finding_id": str(finding_b.id)})
    assert resp.status_code == 404, resp.text
