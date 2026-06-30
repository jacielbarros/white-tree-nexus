"""Feature 015 / US1 — Promoção de constatação de auditoria (5a) a NC formal (idempotente)."""

import uuid

from wtnapp.models.internal_audit_model import InternalAudit, InternalAuditFinding, InternalAuditProgram
from wtnapp.settings import AuditFindingType, DocStatus, InternalAuditStatus


def _seed_org(gap_seed_factory, slug):
    return gap_seed_factory(slug)


def _make_finding(db, org, user, *, finding_type=AuditFindingType.nc_menor, promotable=True):
    program = InternalAuditProgram(tenant_id=org.id, name="Prog", created_by=user.id)
    db.add(program)
    db.flush()
    audit = InternalAudit(
        tenant_id=org.id, program_id=program.id, code="AUD-0001", title="A", scope="s", criteria="c",
        auditor_member_id=user.id, status=InternalAuditStatus.in_progress, draft_status=DocStatus.draft, created_by=user.id,
    )
    db.add(audit)
    db.flush()
    finding = InternalAuditFinding(
        tenant_id=org.id, audit_id=audit.id, finding_type=finding_type, title="NC achada",
        description="desvio do controle", promotable=promotable, created_by=user.id,
    )
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding


def test_promote_finding_creates_nc_and_is_idempotent(client, db, gap_seed_factory, org_headers):
    seed = _seed_org(gap_seed_factory, "nc-promote")
    h = org_headers(seed["admin"].email, seed["org"].id)
    finding = _make_finding(db, seed["org"], seed["admin"], finding_type=AuditFindingType.nc_maior)

    resp = client.post("/nonconformities/promote", headers=h, json={"finding_id": str(finding.id)})
    assert resp.status_code == 201, resp.text
    nc = resp.json()
    assert nc["origin"] == "audit_finding"
    assert nc["severity"] == "maior"  # nc_maior → maior
    assert nc["source_finding_id"] == str(finding.id)
    nc_id = nc["id"]

    # a constatação passa a referenciar a NC (nonconformity_ref preenchido)
    db.expire_all()
    assert db.get(InternalAuditFinding, finding.id).nonconformity_ref == uuid.UUID(nc_id)

    # idempotente: promover de novo retorna a MESMA NC (200, sem duplicar)
    again = client.post("/nonconformities/promote", headers=h, json={"finding_id": str(finding.id)})
    assert again.status_code == 200
    assert again.json()["id"] == nc_id
    assert db.query(InternalAuditFinding).count() == 1


def test_non_promotable_finding_is_rejected(client, db, gap_seed_factory, org_headers):
    seed = _seed_org(gap_seed_factory, "nc-promote-bad")
    h = org_headers(seed["admin"].email, seed["org"].id)
    finding = _make_finding(db, seed["org"], seed["admin"], finding_type=AuditFindingType.observacao, promotable=False)

    resp = client.post("/nonconformities/promote", headers=h, json={"finding_id": str(finding.id)})
    assert resp.status_code == 422, resp.text
