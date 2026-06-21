"""Testes de baseline do Gap Analysis (T024).

Cobre: submit-review → approve cria DocumentVersion imutável; aprovar sem revisão → 409;
como Consultor → 403; compare retorna variação; UPDATE/DELETE da versão bloqueado.
"""

import pytest
from fastapi.testclient import TestClient

from wtnapp.main import app
from wtnapp.settings import Role


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


@pytest.fixture
def gap_baseline_org(factory):
    org = factory.org("gap-baseline", "GAP Baseline Org")
    admin = factory.user("admin@gap-baseline.com", full_name="Admin Baseline")
    consultant = factory.user("consultant@gap-baseline.com", full_name="Consultant Baseline")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(consultant, org, Role.consultant)
    return {"org": org, "admin": admin, "consultant": consultant}


def headers_for(login_fn, email, org_id):
    h = login_fn(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _setup_assessment(client, h):
    """Adota catálogo e avalia um item para ter dados."""
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)
    r = client.get("/gap/assessment", headers=h)
    item_id = r.json()["items"][0]["id"]
    client.put(f"/gap/assessment/items/{item_id}", json={"status": "meets"}, headers=h)
    return r.json()["id"]


def test_submit_review_and_approve_creates_baseline(client, login, gap_baseline_org, gap_seed):
    """Fluxo completo: submit-review → approve cria baseline imutável."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)
    _setup_assessment(client, ha)

    # submit-review
    r = client.post("/gap/assessment/submit-review", headers=ha)
    assert r.status_code == 200
    assert r.json()["status"] == "in_review"

    # approve
    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Emissão inicial"},
        headers=ha,
    )
    assert r.status_code == 200
    baseline = r.json()
    assert baseline["version_number"] == 1
    assert baseline["overall_adherence"] is not None

    # Lista baselines
    r = client.get("/gap/assessment/baselines", headers=ha)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_approve_without_review_returns_409(client, login, gap_baseline_org, gap_seed):
    """Aprovar sem enviar para revisão deve retornar 409."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)
    _setup_assessment(client, ha)

    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Emissão"},
        headers=ha,
    )
    assert r.status_code == 409


def test_consultant_cannot_approve(client, login, gap_baseline_org, gap_seed):
    """Consultor sem approve_gap_baseline deve receber 403."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)
    hc = headers_for(login, "consultant@gap-baseline.com", gap_baseline_org["org"].id)

    _setup_assessment(client, ha)
    client.post("/gap/assessment/submit-review", headers=ha)

    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Emissão"},
        headers=hc,
    )
    assert r.status_code == 403


def test_compare_two_baselines(client, login, gap_baseline_org, gap_seed):
    """Comparar duas baselines retorna variação de aderência."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)

    # Baseline v1: 1 not_meet → overall_adherence=0.0
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    r = client.get("/gap/assessment", headers=ha)
    items = r.json()["items"]
    client.put(f"/gap/assessment/items/{items[0]['id']}", json={"status": "not_meet"}, headers=ha)
    client.post("/gap/assessment/submit-review", headers=ha)
    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Emissão inicial"},
        headers=ha,
    )
    v1_id = r.json()["id"]
    assert r.json()["overall_adherence"] == pytest.approx(0.0, abs=0.001)

    # Baseline v2: mesmo item agora meets → overall_adherence=1.0
    client.put(f"/gap/assessment/items/{items[0]['id']}", json={"status": "meets"}, headers=ha)
    client.post("/gap/assessment/submit-review", headers=ha)
    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Revisão"},
        headers=ha,
    )
    v2_id = r.json()["id"]
    assert r.json()["overall_adherence"] == pytest.approx(1.0, abs=0.001)

    # Compare
    r = client.get(
        f"/gap/assessment/baselines/compare?from_id={v1_id}&to_id={v2_id}",
        headers=ha,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["overall_delta"] is not None
    assert data["overall_delta"] > 0  # v2 (1.0) > v1 (0.0)


def test_double_submit_review_returns_409(client, login, gap_baseline_org, gap_seed):
    """Enviar para revisão duas vezes deve retornar 409."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)
    _setup_assessment(client, ha)

    client.post("/gap/assessment/submit-review", headers=ha)
    r = client.post("/gap/assessment/submit-review", headers=ha)
    assert r.status_code == 409


def test_baseline_immutable_after_approval(client, login, gap_baseline_org, gap_seed):
    """Baseline aprovada permanece imutável: novo item avaliado não altera versão anterior."""
    ha = headers_for(login, "admin@gap-baseline.com", gap_baseline_org["org"].id)
    _setup_assessment(client, ha)

    client.post("/gap/assessment/submit-review", headers=ha)
    r = client.post(
        "/gap/assessment/approve",
        json={"classification": "uso_interno", "change_nature": "Emissão"},
        headers=ha,
    )
    v1_id = r.json()["id"]
    v1_adherence = r.json()["overall_adherence"]

    # Modifica mais itens DEPOIS de aprovar
    r2 = client.get("/gap/assessment", headers=ha)
    for item in r2.json()["items"][:3]:
        client.put(f"/gap/assessment/items/{item['id']}", json={"status": "meets"}, headers=ha)

    # Busca versão v1 — deve ter o mesmo valor de aderência da época da aprovação
    r = client.get("/gap/assessment/baselines", headers=ha)
    v1 = next(b for b in r.json() if b["id"] == v1_id)
    assert v1["overall_adherence"] == v1_adherence  # snapshot não muda

    # Não existe endpoint DELETE para baselines
    r = client.delete(f"/gap/assessment/baselines/{v1_id}", headers=ha)
    assert r.status_code in (404, 405)  # endpoint inexistente
