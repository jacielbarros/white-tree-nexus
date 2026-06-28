"""US5 — Dashboard do módulo: distribuições, top riscos, inerente×residual + card na esteira."""


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def _risk(client, h, seed, prob):
    t, v = _ids(client, h)
    r = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": t, "vulnerability_id": v,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()
    client.put(f"/risk/risks/{r['id']}", headers=h, json={
        "probability_level": prob, "owner_user_id": str(seed["admin"].id),
    })
    return r


def test_dashboard_distributions(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _risk(client, h, seed, 1)   # 1×4=4 → low
    high = _risk(client, h, seed, 4)  # 4×4=16 → critical (acima)

    dash = client.get("/risk/dashboard", headers=h).json()
    assert len(dash["heatmap"]) == 25
    assert dash["by_level"].get("low", 0) == 1
    assert dash["by_level"].get("critical", 0) == 1
    assert high["id"] in dash["top_risks"]
    assert dash["without_treatment"] == 2
    assert dash["inherent_vs_residual"]["inherent_above"] == 1


def test_dashboard_inherent_vs_residual(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    r = _risk(client, h, seed, 4)  # critical (acima)
    client.put(f"/risk/risks/{r['id']}/treatment", headers=h, json={
        "treatment_option": "mitigate", "residual_probability_level": 1, "residual_impact_level": 1,
    })
    dash = client.get("/risk/dashboard", headers=h).json()
    assert dash["inherent_vs_residual"]["inherent_above"] == 1
    assert dash["inherent_vs_residual"]["residual_above"] == 0


def test_risk_card_on_conformance_dashboard(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _risk(client, h, seed, 3)
    home = client.get("/dashboard", headers=h).json()
    ids = {c["id"] for c in home["cards"]}
    assert "risk" in ids
