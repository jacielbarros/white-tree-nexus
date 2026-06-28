"""US4 — Metodologia: default 5x5, edição, validação, recálculo em massa."""

import copy

from wtnapp.settings import DEFAULT_RISK_METHODOLOGY


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def test_default_methodology_when_unconfigured(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    body = client.get("/risk/methodology", headers=h).json()
    assert body["is_configured"] is False
    assert len(body["probability_scale"]) == 5
    assert len(body["risk_matrix"]) == 25


def test_save_and_validation(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    payload = copy.deepcopy(DEFAULT_RISK_METHODOLOGY)
    payload.pop("is_configured", None)

    # válido
    assert client.put("/risk/methodology", headers=h, json=payload).status_code == 200
    assert client.get("/risk/methodology", headers=h).json()["is_configured"] is True

    # inválido: matriz incompleta
    bad = copy.deepcopy(payload)
    bad["risk_matrix"] = {"1x1": "low"}
    assert client.put("/risk/methodology", headers=h, json=bad).status_code == 422


def test_methodology_change_recomputes_levels(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    t, v = _ids(client, h)
    risk = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": t, "vulnerability_id": v,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()
    # prob 3 × impact 4 (derivado) = 12 → high
    client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 3, "owner_user_id": str(seed["admin"].id),
    })
    assert client.get(f"/risk/risks/{risk['id']}", headers=h).json()["inherent_level_key"] == "high"

    # nova metodologia: tudo "low" → recálculo deve reclassificar
    payload = copy.deepcopy(DEFAULT_RISK_METHODOLOGY)
    payload.pop("is_configured", None)
    payload["risk_matrix"] = {f"{p}x{i}": "low" for p in range(1, 6) for i in range(1, 6)}
    assert client.put("/risk/methodology", headers=h, json=payload).status_code == 200

    assert client.get(f"/risk/risks/{risk['id']}", headers=h).json()["inherent_level_key"] == "low"
