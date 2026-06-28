"""US1 — Avaliação de riscos: cenário, código, impacto da CIA/override, nível, critério, filtros."""


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def test_create_scenario_generates_code_and_event(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)

    resp = client.post("/risk/risks", headers=h, json={
        "title": "Vazamento da base de clientes", "description": "Acesso indevido à base.",
        "threat_id": threat_id, "vulnerability_id": vuln_id,
        "asset_item_ids": [str(seed["asset"].id)],
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "RSK-0001"
    assert body["status"] == "identified"
    assert str(seed["asset"].id) in body["asset_item_ids"]

    hist = client.get(f"/risk/risks/{body['id']}/history", headers=h).json()
    assert any(e["event_type"] == "CREATE" for e in hist)


def test_impact_derived_from_cia_max(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    # asset CIA: C=alta(4)→impact 4, I=media(3), A=media(3). max → alta → impact 4 (default map).
    risk = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": threat_id, "vulnerability_id": vuln_id,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()

    resp = client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 3, "owner_user_id": str(seed["admin"].id),
    })
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["impact_derived_level"] == 4
    assert body["impact_level"] == 4          # derivado, sem override
    assert body["impact_is_override"] is False
    assert body["status"] == "assessed"       # prob + impacto + dono
    # prob 3 × impacto 4 = 12 → "high"; critério default aceita ≤ médio ⇒ acima do critério
    assert body["inherent_level_key"] == "high"
    assert body["above_acceptance"] is True


def test_impact_override_requires_justification(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    risk = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": threat_id, "vulnerability_id": vuln_id,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()

    # derivado = 4; tentar impacto 2 sem justificativa → 422
    resp = client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 2, "impact_level": 2,
    })
    assert resp.status_code == 422

    # com justificativa → ok + flag de override
    resp = client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 2, "impact_level": 2, "impact_override_reason": "Mitigação compensatória.",
        "owner_user_id": str(seed["admin"].id),
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["impact_is_override"] is True
    assert resp.json()["impact_level"] == 2


def test_scenario_without_assets_needs_manual_impact(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    risk = client.post("/risk/risks", headers=h, json={
        "title": "Risco organizacional", "description": "Sem ativo.",
        "threat_id": threat_id, "vulnerability_id": vuln_id, "asset_item_ids": [],
    }).json()

    body = client.put(f"/risk/risks/{risk['id']}", headers=h, json={
        "probability_level": 4, "impact_level": 5, "owner_user_id": str(seed["admin"].id),
    }).json()
    assert body["impact_derived_level"] is None    # sem CIA p/ derivar
    assert body["impact_level"] == 5               # manual
    assert body["inherent_level_key"] == "critical"


def test_required_fields_validation(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    resp = client.post("/risk/risks", headers=h, json={
        "title": "", "description": "d", "threat_id": threat_id, "vulnerability_id": vuln_id,
    })
    assert resp.status_code == 422


def test_list_filters_and_search(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    for i in range(3):
        r = client.post("/risk/risks", headers=h, json={
            "title": f"Risco {i}", "description": "alvo busca" if i == 0 else "outro",
            "threat_id": threat_id, "vulnerability_id": vuln_id,
            "asset_item_ids": [str(seed["asset"].id)],
        }).json()
        client.put(f"/risk/risks/{r['id']}", headers=h, json={
            "probability_level": 1 + i, "owner_user_id": str(seed["admin"].id),
        })

    assert len(client.get("/risk/risks", headers=h).json()) == 3
    assert len(client.get("/risk/risks?q=alvo busca", headers=h).json()) == 1
    assert len(client.get("/risk/risks?status_filter=assessed", headers=h).json()) == 3
    by_owner = client.get(f"/risk/risks?owner_user_id={seed['admin'].id}", headers=h).json()
    assert len(by_owner) == 3


def test_matrix_heatmap(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat_id, vuln_id = _ids(client, h)
    r = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": threat_id, "vulnerability_id": vuln_id,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()
    client.put(f"/risk/risks/{r['id']}", headers=h, json={
        "probability_level": 3, "owner_user_id": str(seed["admin"].id),
    })
    cells = client.get("/risk/matrix", headers=h).json()
    assert len(cells) == 25
    cell = next(c for c in cells if c["probability"] == 3 and c["impact"] == 4)
    assert cell["count"] == 1
    assert cell["level_key"] == "high"


def test_view_only_role_cannot_create(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("client@risk-acme.com", seed["org"].id)  # client tem só view_risk
    threat_id, vuln_id = _ids(client, h)
    resp = client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": threat_id, "vulnerability_id": vuln_id,
    })
    assert resp.status_code == 403
