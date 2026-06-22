"""RBAC/isolamento da Orientação (Feature 007) — edição só pelo Super Admin da plataforma."""


def _seed_item_id(client, headers, ref_code="A.8.24"):
    items = client.get("/gap/guidance", headers=headers).json()["items"]
    return next(i["seed_item_id"] for i in items if i["ref_code"] == ref_code)


def test_org_admin_cannot_edit_guidance(client, soa_seed, org_headers):
    s = soa_seed("rbac-a")
    ha = org_headers(s["admin"].email, s["org"].id)  # Admin da ORG (não é Super Admin da plataforma)
    sid = _seed_item_id(client, ha)
    resp = client.put(f"/gap/guidance/items/{sid}", headers=ha, json={"objetivo": "tentativa"})
    assert resp.status_code == 403


def test_org_admin_cannot_edit_legend_or_list_events(client, soa_seed, org_headers):
    s = soa_seed("rbac-b")
    ha = org_headers(s["admin"].email, s["org"].id)
    legend = client.get("/gap/guidance", headers=ha).json()["legend"]
    entry_id = legend["priority"][0]["id"]
    assert client.put(f"/gap/guidance/legend/{entry_id}", headers=ha, json={"label": "x"}).status_code == 403
    assert client.get("/gap/guidance/events", headers=ha).status_code == 403


def test_consultant_cannot_edit_guidance(client, soa_seed, org_headers):
    s = soa_seed("rbac-c")
    hc = org_headers(s["consultant"].email, s["org"].id)
    sid = _seed_item_id(client, hc)
    # Consultor tem view_gap (lê), mas não é Super Admin da plataforma → não edita
    assert client.get("/gap/guidance", headers=hc).status_code == 200
    assert client.put(f"/gap/guidance/items/{sid}", headers=hc, json={"objetivo": "x"}).status_code == 403
