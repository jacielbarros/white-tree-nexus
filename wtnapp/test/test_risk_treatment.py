"""US3 — Tratamento: opção, controles (mitigar exige resp+prazo), residual, aceitação, SoA-feed."""

from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.services.gap_seed_service import adopt_seed, load_seed


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


def _adopt_gap(db, org_id):
    load_seed(db)
    adopt_seed(db, org_id, "2022.1")
    return db.query(GapCatalogItem).filter_by(tenant_id=org_id).first()


def test_mitigate_requires_control_with_responsible_and_due(client, db, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)
    gap = _adopt_gap(db, seed["org"].id)

    client.put(f"/risk/risks/{risk['id']}/treatment", headers=h, json={
        "treatment_option": "mitigate", "residual_probability_level": 2, "residual_impact_level": 2,
        "reason": "Reduzir exposição",
    })
    # controle sem responsável/prazo → 422
    resp = client.post(f"/risk/risks/{risk['id']}/controls", headers=h, json={
        "gap_catalog_item_id": str(gap.id),
    })
    assert resp.status_code == 422

    # com responsável + prazo → 201
    resp = client.post(f"/risk/risks/{risk['id']}/controls", headers=h, json={
        "gap_catalog_item_id": str(gap.id), "responsible_user_id": str(seed["admin"].id),
        "due_date": "2026-12-31",
    })
    assert resp.status_code == 201, resp.text


def test_control_xor_gap_or_custom(client, db, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)
    client.put(f"/risk/risks/{risk['id']}/treatment", headers=h, json={"treatment_option": "transfer"})
    # nenhum dos dois → 422
    assert client.post(f"/risk/risks/{risk['id']}/controls", headers=h, json={}).status_code == 422


def test_residual_recompute_and_signal(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)  # prob 4 × impact 4 = 16 → critical (acima)

    body = client.put(f"/risk/risks/{risk['id']}/treatment", headers=h, json={
        "treatment_option": "mitigate", "residual_probability_level": 1, "residual_impact_level": 2,
        "reason": "x",
    }).json()
    assert body["residual_level_key"] == "low"          # 1×2=2 → low
    assert body["residual_above_acceptance"] is False   # low aceito ⇒ atende ao critério
    assert body["status"] == "in_treatment"


def test_accept_requires_justification_and_owner(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)

    assert client.post(f"/risk/risks/{risk['id']}/accept", headers=h,
                       json={"acceptance_reason": "", "accepted_owner_user_id": str(seed["admin"].id)}
                       ).status_code == 422
    resp = client.post(f"/risk/risks/{risk['id']}/accept", headers=h, json={
        "acceptance_reason": "Risco tolerável.", "accepted_owner_user_id": str(seed["admin"].id),
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "accepted"


def test_soa_feed_exposes_control_risk_link(client, db, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    risk = _evaluated_risk(client, h, seed)
    gap = _adopt_gap(db, seed["org"].id)
    client.put(f"/risk/risks/{risk['id']}/treatment", headers=h, json={"treatment_option": "mitigate"})
    client.post(f"/risk/risks/{risk['id']}/controls", headers=h, json={
        "gap_catalog_item_id": str(gap.id), "responsible_user_id": str(seed["admin"].id),
        "due_date": "2026-12-31",
    })

    feed = client.get("/risk/soa-feed", headers=h).json()
    assert len(feed) == 1
    assert feed[0]["gap_catalog_item_id"] == str(gap.id)
    assert feed[0]["inclusion_reason"] == "risk_treatment"
    assert risk["code"] in feed[0]["risk_codes"]

    # SoA NÃO foi escrita por este módulo
    from wtnapp.models.soa_model import Soa
    assert db.query(Soa).filter_by(tenant_id=seed["org"].id).first() is None
