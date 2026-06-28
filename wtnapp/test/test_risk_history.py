"""US6 — Histórico append-only + auditoria das decisões de risco."""

import pytest
from sqlalchemy.exc import DatabaseError

from wtnapp.models.risk_model import RiskEvent


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def _evaluated_risk(client, h, seed):
    t, v = _ids(client, h)
    risk = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": t, "vulnerability_id": v,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()
    client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 4, "owner_user_id": str(seed["admin"].id),
    })
    return risk


def test_history_records_decisions_in_order(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)
    client.post(f"/risk/risks/{risk['id']}/accept", headers=h, json={
        "acceptance_reason": "Tolerável.", "accepted_owner_user_id": str(seed["admin"].id),
    })

    hist = client.get(f"/risk/risks/{risk['id']}/history", headers=h).json()
    types = [e["event_type"] for e in hist]
    assert "CREATE" in types
    assert "PROBABILITY_CHANGE" in types
    assert "LEVEL_CHANGE" in types
    assert "ACCEPTED" in types
    # ordem cronológica crescente
    stamps = [e["occurred_at"] for e in hist]
    assert stamps == sorted(stamps)
    # justificativa registrada na aceitação
    accepted = next(e for e in hist if e["event_type"] == "ACCEPTED")
    assert accepted["reason"] == "Tolerável."


def test_risk_events_are_append_only(client, db, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)

    event = db.query(RiskEvent).filter_by(tenant_id=seed["org"].id).first()
    assert event is not None
    # UPDATE bloqueado pelo gatilho append-only
    with pytest.raises(DatabaseError):
        event.reason = "tampered"
        db.commit()
    db.rollback()


def test_audit_log_on_create(client, db, risk_seed, org_headers):
    from wtnapp.models.audit_log_model import AuditLog
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _evaluated_risk(client, h, seed)
    logs = db.query(AuditLog).filter(
        AuditLog.tenant_id == seed["org"].id, AuditLog.entity_type == "risk"
    ).all()
    assert any(log.operation == "CREATE" for log in logs)
    # nunca grava conteúdo sensível: details não contém a descrição do risco
    for log in logs:
        assert "description" not in (log.details or {})
