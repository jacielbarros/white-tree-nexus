"""Testes do gap_metrics_service (T018).

Cobre: pesos 1.0/0.5/0.0, N/A e not_filled fora do denominador,
denominador zero → null, consistência entre recortes, lacunas.
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
    org = factory.org("gap-metrics", "GAP Metrics Org")
    admin = factory.user("admin@gap-metrics.com", full_name="Admin Metrics")
    factory.membership(admin, org, Role.org_admin)
    return {"org": org, "admin": admin}


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


def test_dashboard_empty_after_adoption(client, login, gap_org, gap_seed):
    """Com todos itens not_filled, overall_adherence deve ser null e completeness=0."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)

    r = client.get("/gap/assessment/dashboard", headers=h)
    assert r.status_code == 200
    data = r.json()
    assert data["overall_adherence"] is None
    assert data["completeness"] == 0.0
    assert data["status_distribution"].get("not_filled", 0) == 100


def test_adherence_weights(client, login, gap_org, gap_seed):
    """Atende=1.0, Parcial=0.5, Não atende=0.0."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    items = r.json()["items"]

    # Avalia 3 itens: meets, partial, not_meet
    ids = [items[0]["id"], items[1]["id"], items[2]["id"]]
    client.put(f"/gap/assessment/items/{ids[0]}", json={"status": "meets"}, headers=h)
    client.put(f"/gap/assessment/items/{ids[1]}", json={"status": "partial"}, headers=h)
    client.put(f"/gap/assessment/items/{ids[2]}", json={"status": "not_meet"}, headers=h)

    r = client.get("/gap/assessment/dashboard", headers=h)
    data = r.json()
    # 3 aplicáveis: 1.0 + 0.5 + 0.0 = 1.5 / 3 = 0.5
    assert data["overall_adherence"] == pytest.approx(0.5, abs=0.001)
    assert data["completeness"] == pytest.approx(3 / 100, abs=0.001)


def test_not_applicable_excluded_from_denominator(client, login, gap_org, gap_seed):
    """N/A não conta no denominador da aderência."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    items = r.json()["items"]

    # 1 meets + 1 N/A
    client.put(f"/gap/assessment/items/{items[0]['id']}", json={"status": "meets"}, headers=h)
    client.put(
        f"/gap/assessment/items/{items[1]['id']}",
        json={"status": "not_applicable", "exclusion_justification": "Fora do escopo."},
        headers=h,
    )

    r = client.get("/gap/assessment/dashboard", headers=h)
    data = r.json()
    # Apenas 1 item aplicável (meets): 1.0/1 = 1.0
    assert data["overall_adherence"] == pytest.approx(1.0, abs=0.001)


def test_denominator_zero_returns_null(client, login, gap_org, gap_seed):
    """Se todos N/A, overall_adherence deve ser null."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    items = r.json()["items"]

    # Marca apenas 1 item como N/A (os demais ficam not_filled)
    # Com todos not_filled + 1 N/A, ainda é null pois nenhum é aplicável com peso
    client.put(
        f"/gap/assessment/items/{items[0]['id']}",
        json={"status": "not_applicable", "exclusion_justification": "Justificativa."},
        headers=h,
    )

    r = client.get("/gap/assessment/dashboard", headers=h)
    data = r.json()
    # Ainda null pois restam 99 not_filled (também excluídos)
    assert data["overall_adherence"] is None


def test_gaps_list_contains_partial_and_not_meet(client, login, gap_org, gap_seed):
    """GET /gap/assessment/gaps retorna só partial + not_meet, ordenado por prioridade."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    items = r.json()["items"]

    client.put(f"/gap/assessment/items/{items[0]['id']}", json={"status": "meets"}, headers=h)
    client.put(
        f"/gap/assessment/items/{items[1]['id']}",
        json={"status": "partial", "priority": "high"},
        headers=h,
    )
    client.put(
        f"/gap/assessment/items/{items[2]['id']}",
        json={"status": "not_meet", "priority": "critical"},
        headers=h,
    )

    r = client.get("/gap/assessment/gaps", headers=h)
    assert r.status_code == 200
    gaps = r.json()
    assert len(gaps) == 2
    statuses = {g["status"] for g in gaps}
    assert statuses == {"partial", "not_meet"}
    # Ordenado: critical antes de high
    assert gaps[0]["priority"] == "critical"
    assert gaps[1]["priority"] == "high"


def test_gaps_excludes_meets_and_na(client, login, gap_org, gap_seed):
    """meets e not_applicable não aparecem na lista de lacunas."""
    h = headers_for(login, "admin@gap-metrics.com", gap_org["org"].id)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    items = r.json()["items"]

    client.put(f"/gap/assessment/items/{items[0]['id']}", json={"status": "meets"}, headers=h)
    client.put(
        f"/gap/assessment/items/{items[1]['id']}",
        json={"status": "not_applicable", "exclusion_justification": "N/A."},
        headers=h,
    )

    r = client.get("/gap/assessment/gaps", headers=h)
    assert r.json() == []
