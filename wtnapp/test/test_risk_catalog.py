"""US2 — Catálogo: adoção idempotente, custom, arquivar, vínculos a ativos/gaps."""


def test_adopt_is_idempotent(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    # já adotado no fixture; re-adotar não duplica
    before = len(client.get("/risk/threats", headers=h).json())
    result = client.post("/risk/threats/adopt", headers=h).json()
    assert result["added"] == 0
    assert result["unchanged"] == before
    assert len(client.get("/risk/threats", headers=h).json()) == before


def test_create_custom_threat(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    resp = client.post("/risk/threats", headers=h, json={
        "name": "Ameaça interna específica", "category": "human", "origin": "deliberate",
        "description": "x",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["is_custom"] is True
    assert body["code"].startswith("AME-C")


def test_archive_requires_reason_and_hides(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat = client.get("/risk/threats", headers=h).json()[0]

    assert client.post(f"/risk/threats/{threat['id']}/archive", headers=h,
                       json={"reason": ""}).status_code == 422
    assert client.post(f"/risk/threats/{threat['id']}/archive", headers=h,
                       json={"reason": "Não aplicável"}).status_code == 200

    active = {t["id"] for t in client.get("/risk/threats", headers=h).json()}
    assert threat["id"] not in active
    archived = {t["id"] for t in client.get("/risk/threats?include_archived=true", headers=h).json()}
    assert threat["id"] in archived


def test_link_threat_to_asset_appears_in_asset_links(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    threat = client.get("/risk/threats", headers=h).json()[0]
    vuln = client.get("/risk/vulnerabilities", headers=h).json()[0]

    assert client.post(f"/risk/threats/{threat['id']}/assets", headers=h,
                       json={"asset_item_id": str(seed["asset"].id)}).status_code == 201
    assert client.post(f"/risk/vulnerabilities/{vuln['id']}/assets", headers=h,
                       json={"asset_item_id": str(seed["asset"].id)}).status_code == 201

    links = client.get(f"/risk/assets/{seed['asset'].id}/links", headers=h).json()
    assert threat["id"] in {t["id"] for t in links["threats"]}
    assert vuln["id"] in {v["id"] for v in links["vulnerabilities"]}


def test_create_custom_vulnerability(client, risk_seed, org_headers):
    seed = risk_seed()
    h = org_headers("admin@risk-acme.com", seed["org"].id)
    resp = client.post("/risk/vulnerabilities", headers=h, json={
        "name": "Vuln própria", "category": "technical", "description": "x",
    })
    assert resp.status_code == 201, resp.text
    assert resp.json()["code"].startswith("VUL-C")
