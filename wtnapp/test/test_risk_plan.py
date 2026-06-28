"""US3 — Plano de Tratamento: gate duro, aprovação + versão imutável, assinatura opcional."""


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def _create_risk(client, h, seed, evaluate=True):
    t, v = _ids(client, h)
    risk = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": t, "vulnerability_id": v,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()
    if evaluate:
        client.put(f"/risk/risks/{risk['id']}", headers=h, json={
            "probability_level": 3, "owner_user_id": str(seed["admin"].id),
        })
    return risk


def test_hard_gate_blocks_approval_with_unevaluated_risk(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _create_risk(client, h, seed, evaluate=False)  # status identified

    client.post("/risk/plan/submit-review", headers=h)
    resp = client.post("/risk/plan/approve", headers=h, json={"change_nature": "v1"})
    assert resp.status_code == 409


def test_approve_creates_immutable_version(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _create_risk(client, h, seed, evaluate=True)

    client.post("/risk/plan/submit-review", headers=h)
    resp = client.post("/risk/plan/approve", headers=h, json={
        "change_nature": "Aprovação inicial", "classification": "uso_interno",
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["version_number"] == 1

    plan = client.get("/risk/plan", headers=h).json()
    assert plan["current_version_id"] is not None
    versions = client.get("/risk/plan/versions", headers=h).json()
    assert len(versions) == 1
    assert versions[0]["status"] == "in_force"


def test_approve_requires_submit_first(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    _create_risk(client, h, seed, evaluate=True)
    # aprovar sem submeter para revisão → 409
    assert client.post("/risk/plan/approve", headers=h, json={"change_nature": "x"}).status_code == 409


def test_consultant_cannot_approve_plan(client, risk_seed, org_headers):
    seed = risk_seed()
    admin_h = org_headers("admin@risk-acme.com", seed["org"].id)
    _create_risk(client, admin_h, seed, evaluate=True)
    client.post("/risk/plan/submit-review", headers=admin_h)

    consultant_h = org_headers("consultant@risk-acme.com", seed["org"].id)
    resp = client.post("/risk/plan/approve", headers=consultant_h, json={"change_nature": "x"})
    assert resp.status_code == 403  # consultor não tem approve_risk_plan
