"""Teste de isolamento de tenant para o módulo Gap Analysis (T012).

Org A e Org B não devem ver dados uma da outra.
O seed compartilhado é somente leitura para as orgs.
"""

import pytest
from fastapi.testclient import TestClient

from wtnapp.main import app
from wtnapp.settings import Role


@pytest.fixture
def two_orgs(db, factory):
    """Duas orgs independentes com admins."""
    org_a = factory.org("iso-a", "ISO Org A")
    org_b = factory.org("iso-b", "ISO Org B")
    admin_a = factory.user("admin@iso-a.com", full_name="Admin A")
    admin_b = factory.user("admin@iso-b.com", full_name="Admin B")
    factory.membership(admin_a, org_a, Role.org_admin)
    factory.membership(admin_b, org_b, Role.org_admin)
    return {"org_a": org_a, "org_b": org_b, "admin_a": admin_a, "admin_b": admin_b}


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def login(client):
    def _login(email, password="Sup3rSecret!2345"):
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return _login


def headers_for(login_fn, email, org_id):
    h = login_fn(email)
    h["X-Org-Context"] = str(org_id)
    return h


def test_adopt_and_list_catalog_isolated(client, login, two_orgs, gap_seed):
    """Org A adota o catálogo; Org B não vê os itens de A."""
    ha = headers_for(login, "admin@iso-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@iso-b.com", two_orgs["org_b"].id)

    # Org A adota
    r = client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    assert r.status_code == 200

    # Org A vê catálogo
    r = client.get("/gap/catalog", headers=ha)
    assert r.status_code == 200
    assert len(r.json()) == 100  # 7 cláusulas + 93 controles

    # Org B vê catálogo vazio (não adotou)
    r = client.get("/gap/catalog", headers=hb)
    assert r.status_code == 200
    assert r.json() == []


def test_assessment_item_cross_tenant_returns_404(client, login, two_orgs, gap_seed, db):
    """Item de Org A não é acessível via PUT pela Org B."""
    ha = headers_for(login, "admin@iso-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@iso-b.com", two_orgs["org_b"].id)

    # Org A adota e obtém avaliação
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    r = client.get("/gap/assessment", headers=ha)
    assert r.status_code == 200
    item_id = r.json()["items"][0]["id"]

    # Org B tenta atualizar item de Org A
    r = client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "meets"},
        headers=hb,
    )
    assert r.status_code in (404, 403)


def test_catalog_item_cross_tenant_returns_404(client, login, two_orgs, gap_seed):
    """PATCH em item de catálogo de Org A retorna 404 para Org B."""
    ha = headers_for(login, "admin@iso-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@iso-b.com", two_orgs["org_b"].id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    r = client.get("/gap/catalog", headers=ha)
    item_id = r.json()[0]["id"]

    # Org B tenta editar item de Org A
    r = client.patch(
        f"/gap/catalog/items/{item_id}",
        json={"name": "Hackeado"},
        headers=hb,
    )
    assert r.status_code == 404


def test_seed_is_readonly_for_orgs(client, login, two_orgs, gap_seed):
    """Seed compartilhado não tem endpoints de escrita diretos."""
    ha = headers_for(login, "admin@iso-a.com", two_orgs["org_a"].id)
    # Não existe endpoint PUT/DELETE no seed — qualquer verbo destrutivo retorna 404 ou 405
    r = client.delete("/gap/catalog/seed", headers=ha)
    assert r.status_code in (404, 405)


def test_dashboard_isolated(client, login, two_orgs, gap_seed):
    """Dashboard de Org A não vaza para Org B."""
    ha = headers_for(login, "admin@iso-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@iso-b.com", two_orgs["org_b"].id)

    # Org A adota e avalia um item
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    r = client.get("/gap/assessment", headers=ha)
    item_id = r.json()["items"][0]["id"]
    client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "meets"},
        headers=ha,
    )

    # Org A vê aderência
    r = client.get("/gap/assessment/dashboard", headers=ha)
    assert r.status_code == 200
    data = r.json()
    assert data["completeness"] > 0

    # Org B não tem avaliação
    r = client.get("/gap/assessment/dashboard", headers=hb)
    assert r.status_code == 404
