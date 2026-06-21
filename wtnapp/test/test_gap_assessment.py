"""Testes de avaliação Gap Analysis (T013).

Cobre: adotar seed, obter matriz, atualizar item, N/A sem justificativa → 422.
"""

import pytest
from fastapi.testclient import TestClient

from wtnapp.main import app
from wtnapp.settings import Role


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def gap_org(factory):
    org = factory.org("gap-test", "GAP Test Org")
    admin = factory.user("admin@gap-test.com", full_name="Admin GAP")
    consultant = factory.user("consultant@gap-test.com", full_name="Consultant GAP")
    client_user = factory.user("client@gap-test.com", full_name="Client GAP")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(consultant, org, Role.consultant)
    factory.membership(client_user, org, Role.client)
    return {"org": org, "admin": admin, "consultant": consultant, "client": client_user}


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


def test_adopt_seed_materializes_catalog(client, login, gap_org, gap_seed):
    """POST /gap/catalog/adopt cria 100 itens no catálogo da org."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    r = client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["added"] == 100  # 7 + 93

    r2 = client.get("/gap/catalog", headers=h)
    assert r2.status_code == 200
    assert len(r2.json()) == 100


def test_adopt_seed_idempotent(client, login, gap_org, gap_seed):
    """Adotar duas vezes não duplica itens."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["added"] == 0
    assert data["unchanged"] == 100

    r2 = client.get("/gap/catalog", headers=h)
    assert len(r2.json()) == 100


def test_get_assessment_returns_not_filled_items(client, login, gap_org, gap_seed):
    """Após adotar, GET /gap/assessment retorna matriz com todos os itens not_filled."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)

    r = client.get("/gap/assessment", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert len(data["items"]) == 100
    statuses = {i["status"] for i in data["items"]}
    assert statuses == {"not_filled"}


def test_update_item_persists(client, login, gap_org, gap_seed):
    """PUT /gap/assessment/items/{id} persiste o status e retorna o item atualizado."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)

    r = client.get("/gap/assessment", headers=h)
    item_id = r.json()["items"][0]["id"]

    r2 = client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "partial", "findings": "Parcialmente implementado.", "priority": "high"},
        headers=h,
    )
    assert r2.status_code == 200
    updated = r2.json()
    assert updated["status"] == "partial"
    assert updated["findings"] == "Parcialmente implementado."
    assert updated["priority"] == "high"

    # Confirma persistência
    r3 = client.get("/gap/assessment", headers=h)
    item = next(i for i in r3.json()["items"] if i["id"] == item_id)
    assert item["status"] == "partial"


def test_not_applicable_without_justification_returns_422(client, login, gap_org, gap_seed):
    """N/A sem exclusion_justification deve retornar 422."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)

    r = client.get("/gap/assessment", headers=h)
    item_id = r.json()["items"][0]["id"]

    r2 = client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "not_applicable"},
        headers=h,
    )
    assert r2.status_code == 422


def test_not_applicable_with_justification_accepted(client, login, gap_org, gap_seed):
    """N/A com justificativa deve ser aceito (200)."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)

    r = client.get("/gap/assessment", headers=h)
    item_id = r.json()["items"][0]["id"]

    r2 = client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "not_applicable", "exclusion_justification": "Controle não se aplica ao escopo."},
        headers=h,
    )
    assert r2.status_code == 200
    assert r2.json()["status"] == "not_applicable"


def test_invalid_seed_version_returns_409(client, login, gap_org, gap_seed):
    """Versão de seed inexistente deve retornar 409."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    r = client.post("/gap/catalog/adopt", json={"seed_version": "9999.0"}, headers=h)
    assert r.status_code == 409


def test_client_can_view_but_not_manage(client, login, gap_org, gap_seed):
    """Cliente pode ver catálogo e avaliação mas não editar itens (403)."""
    ha = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    hc = headers_for(login, "client@gap-test.com", gap_org["org"].id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)

    # Cliente vê catálogo
    r = client.get("/gap/catalog", headers=hc)
    assert r.status_code == 200

    # Cliente vê avaliação
    r = client.get("/gap/assessment", headers=hc)
    assert r.status_code == 200
    item_id = r.json()["items"][0]["id"]

    # Cliente não pode atualizar item
    r = client.put(
        f"/gap/assessment/items/{item_id}",
        json={"status": "meets"},
        headers=hc,
    )
    assert r.status_code == 403


def test_assessment_not_found_without_adoption(client, login, gap_org, gap_seed):
    """Sem adoção prévia, GET /gap/assessment retorna 404."""
    h = headers_for(login, "admin@gap-test.com", gap_org["org"].id)
    r = client.get("/gap/assessment", headers=h)
    assert r.status_code == 404
