"""Isolamento de tenant — o dashboard de uma org é inacessível a usuário de outra (404)."""

from wtnapp.settings import Role


def test_cross_tenant_dashboard_denied(client, soa_seed, org_headers):
    a = soa_seed("dash-a")
    b = soa_seed("dash-b")

    ha = org_headers(a["admin"].email, a["org"].id)
    assert client.get("/dashboard", headers=ha).status_code == 200

    # Usuário da Org B com contexto da Org A → 404 genérico, sem vazar nada de A.
    cross = org_headers(b["admin"].email, a["org"].id)
    resp = client.get("/dashboard", headers=cross)
    assert resp.status_code == 404
    assert a["org"].name not in resp.text
    assert str(a["org"].id) not in resp.text


def test_multi_org_scoped_to_active_context(client, soa_seed, org_headers, factory):
    a = soa_seed("dash-a")
    b = soa_seed("dash-b")
    # admin de A também é consultor em B (usuário multi-org).
    factory.membership(a["admin"], b["org"], Role.consultant)

    ra = client.get("/dashboard", headers=org_headers(a["admin"].email, a["org"].id)).json()
    rb = client.get("/dashboard", headers=org_headers(a["admin"].email, b["org"].id)).json()

    assert ra["organization_id"] == str(a["org"].id)
    assert ra["organization_name"] == a["org"].name
    assert rb["organization_id"] == str(b["org"].id)
    assert rb["organization_name"] == b["org"].name
