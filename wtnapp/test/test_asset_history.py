"""Feature 011 — histórico append-only, justificativa e situação de revisão derivada."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from wtnapp.settings import Role


@pytest.fixture
def hist_org(factory):
    org = factory.org("hist-acme", "Hist Acme")
    admin = factory.user("admin@hist-acme.com")
    factory.membership(admin, org, Role.org_admin)
    return {"org": org, "admin": admin}


def _create(client, h, **over):
    payload = {"name": "Item H", "item_type": "system", "scope_status": "under_analysis"}
    payload.update(over)
    return client.post("/assets", headers=h, json=payload).json()


def test_create_logs_event(client, org_headers, hist_org):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    item = _create(client, h)
    events = client.get(f"/assets/{item['id']}/history", headers=h).json()
    assert len(events) == 1
    assert events[0]["event_type"] == "CREATE"


def test_scope_exclusion_requires_reason(client, org_headers, hist_org):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    item = _create(client, h)
    # mudar para out_of_scope sem reason => 422 (precisa justificativa de exclusão + justificativa de mudança)
    resp = client.put(f"/assets/{item['id']}", headers=h, json={
        "name": "Item H", "item_type": "system", "scope_status": "out_of_scope",
        "scope_justification": "Não pertence ao SGSI",
    })
    assert resp.status_code == 422  # falta reason da mudança crítica
    ok = client.put(f"/assets/{item['id']}", headers=h, json={
        "name": "Item H", "item_type": "system", "scope_status": "out_of_scope",
        "scope_justification": "Não pertence ao SGSI", "reason": "Revisão de escopo 2026",
    })
    assert ok.status_code == 200, ok.text
    events = client.get(f"/assets/{item['id']}/history", headers=h).json()
    types = [e["event_type"] for e in events]
    assert "SCOPE_EXCLUSION" in types


def test_criticality_change_requires_reason(client, org_headers, hist_org):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    item = _create(client, h, confidentiality="baixa", integrity="baixa", availability="baixa")
    # subir CIA muda criticidade => exige reason
    no_reason = client.put(f"/assets/{item['id']}", headers=h, json={
        "name": "Item H", "item_type": "system", "scope_status": "under_analysis",
        "confidentiality": "critica", "integrity": "baixa", "availability": "baixa",
    })
    assert no_reason.status_code == 422
    ok = client.put(f"/assets/{item['id']}", headers=h, json={
        "name": "Item H", "item_type": "system", "scope_status": "under_analysis",
        "confidentiality": "critica", "integrity": "baixa", "availability": "baixa",
        "reason": "Reclassificação",
    })
    assert ok.status_code == 200
    assert ok.json()["criticality"] == "critica"


def test_archive_logs_event(client, org_headers, hist_org):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    item = _create(client, h)
    client.post(f"/assets/{item['id']}/archive", headers=h, json={"reason": "fim"})
    types = [e["event_type"] for e in client.get(f"/assets/{item['id']}/history", headers=h).json()]
    assert "ARCHIVE" in types


def test_history_is_append_only(client, org_headers, hist_org, db):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    item = _create(client, h)
    # UPDATE direto na trilha deve abortar (trigger append-only)
    with pytest.raises(Exception):
        db.execute(text("UPDATE asset_item_events SET event_type = 'HACK'"))
        db.commit()
    db.rollback()
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM asset_item_events"))
        db.commit()
    db.rollback()


def test_review_status_derivation_and_filter(client, org_headers, hist_org):
    h = org_headers(hist_org["admin"].email, hist_org["org"].id)
    past = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    overdue = _create(client, h, name="Vencido", next_review_at=past)
    _create(client, h, name="Em dia", next_review_at=future)
    _create(client, h, name="Indefinido")

    assert overdue["review_status"] == "overdue"
    r = client.get("/assets", headers=h, params={"review_status": "overdue"})
    assert {i["name"] for i in r.json()} == {"Vencido"}
    r2 = client.get("/assets", headers=h, params={"review_status": "undefined"})
    assert {i["name"] for i in r2.json()} == {"Indefinido"}
