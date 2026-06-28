"""Isolamento de tenant do módulo de Riscos (OBRIGATÓRIO)."""


def _ids(client, headers):
    threats = client.get("/risk/threats", headers=headers).json()
    vulns = client.get("/risk/vulnerabilities", headers=headers).json()
    return threats[0]["id"], vulns[0]["id"]


def _make_risk(client, h, seed):
    t, v = _ids(client, h)
    return client.post("/risk/risks", headers=h, json={
        "title": "R", "description": "d", "threat_id": t, "vulnerability_id": v,
        "asset_item_ids": [str(seed["asset"].id)],
    }).json()


def test_cross_tenant_risk_is_404(client, risk_seed, org_headers):
    a = risk_seed("org-a")
    b = risk_seed("org-b")
    ha = org_headers("admin@org-a.com", a["org"].id)
    hb = org_headers("admin@org-b.com", b["org"].id)

    risk_a = _make_risk(client, ha, a)
    # B não vê o risco de A
    assert client.get(f"/risk/risks/{risk_a['id']}", headers=hb).status_code == 404
    assert client.put(f"/risk/risks/{risk_a['id']}", headers=hb,
                      json={"probability_level": 2}).status_code == 404
    assert client.get(f"/risk/risks/{risk_a['id']}/history", headers=hb).status_code == 404


def test_cross_tenant_catalog_isolated(client, risk_seed, org_headers):
    a = risk_seed("org-a")
    b = risk_seed("org-b")
    ha = org_headers("admin@org-a.com", a["org"].id)
    hb = org_headers("admin@org-b.com", b["org"].id)

    threat_a = client.get("/risk/threats", headers=ha).json()[0]
    # Arquivar a ameaça de A pelo contexto de B → 404
    assert client.post(f"/risk/threats/{threat_a['id']}/archive", headers=hb,
                       json={"reason": "x"}).status_code == 404

    # Cada org tem sua própria cópia (mesmos códigos, ids distintos)
    threats_a = {t["code"] for t in client.get("/risk/threats", headers=ha).json()}
    threats_b = {t["code"] for t in client.get("/risk/threats", headers=hb).json()}
    assert threats_a == threats_b  # mesma semente
    ids_a = {t["id"] for t in client.get("/risk/threats", headers=ha).json()}
    ids_b = {t["id"] for t in client.get("/risk/threats", headers=hb).json()}
    assert ids_a.isdisjoint(ids_b)  # cópias distintas por tenant


def test_cross_tenant_scenario_cannot_reference_other_tenant_catalog(client, risk_seed, org_headers):
    a = risk_seed("org-a")
    b = risk_seed("org-b")
    ha = org_headers("admin@org-a.com", a["org"].id)
    hb = org_headers("admin@org-b.com", b["org"].id)

    threat_b, vuln_b = _ids(client, hb)
    # A tenta criar risco referenciando ameaça/vuln de B → 404
    resp = client.post("/risk/risks", headers=ha, json={
        "title": "R", "description": "d", "threat_id": threat_b, "vulnerability_id": vuln_b,
    })
    assert resp.status_code == 404


def test_cross_tenant_control_cannot_reference_other_tenant_asset(client, risk_seed, org_headers):
    a = risk_seed("org-a")
    b = risk_seed("org-b")
    ha = org_headers("admin@org-a.com", a["org"].id)
    # A tenta vincular ameaça ao ativo de B → 404
    threat_a = client.get("/risk/threats", headers=ha).json()[0]
    resp = client.post(f"/risk/threats/{threat_a['id']}/assets", headers=ha,
                       json={"asset_item_id": str(b["asset"].id)})
    assert resp.status_code == 404


def test_list_only_shows_own_tenant(client, risk_seed, org_headers):
    a = risk_seed("org-a")
    b = risk_seed("org-b")
    ha = org_headers("admin@org-a.com", a["org"].id)
    hb = org_headers("admin@org-b.com", b["org"].id)
    _make_risk(client, ha, a)
    assert len(client.get("/risk/risks", headers=ha).json()) == 1
    assert len(client.get("/risk/risks", headers=hb).json()) == 0
