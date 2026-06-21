"""Isolamento de tenant — SoA, itens e versões de uma org são inacessíveis a outra (404/403)."""

import uuid


def test_cross_tenant_get_denied(client, soa_seed, org_headers):
    a = soa_seed("soa-a")
    b = soa_seed("soa-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    client.post("/soa/consolidate", headers=ha)

    # Usuário da Org B com contexto da Org A → 404 (não revela existência)
    cross = org_headers(b["admin"].email, a["org"].id)
    assert client.get("/soa", headers=cross).status_code == 404


def test_cross_tenant_item_update_denied(client, soa_seed, org_headers):
    a = soa_seed("soa-a")
    b = soa_seed("soa-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    client.post("/soa/consolidate", headers=ha)
    item = next(i for i in client.get("/soa", headers=ha).json()["items"] if i["applicable"])

    hb = org_headers(b["admin"].email, b["org"].id)
    client.post("/soa/consolidate", headers=hb)
    # B (no próprio contexto) tenta editar item de A → 404
    resp = client.put(f"/soa/items/{item['id']}", headers=hb, json={"observations": "x"})
    assert resp.status_code == 404


def test_cross_tenant_export_denied(client, soa_seed, org_headers, complete_soa):
    a = soa_seed("soa-a")
    b = soa_seed("soa-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    client.post("/soa/consolidate", headers=ha)
    complete_soa(a["org"].id)
    client.post("/soa/submit-review", headers=ha)
    version = client.post("/soa/approve", headers=ha, json={}).json()

    hb = org_headers(b["admin"].email, b["org"].id)
    client.post("/soa/consolidate", headers=hb)
    # B tenta exportar a versão de A → 404
    resp = client.get(f"/soa/versions/{version['id']}/export", headers=hb)
    assert resp.status_code == 404
