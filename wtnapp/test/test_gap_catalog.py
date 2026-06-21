"""Testes do catálogo editável por organização (T021).

Cobre: item próprio isolado por org, PATCH renomeia, adoção aditiva, completude do seed.
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
def two_orgs(factory):
    org_a = factory.org("cat-a", "CAT Org A")
    org_b = factory.org("cat-b", "CAT Org B")
    admin_a = factory.user("admin@cat-a.com", full_name="Admin Cat A")
    admin_b = factory.user("admin@cat-b.com", full_name="Admin Cat B")
    factory.membership(admin_a, org_a, Role.org_admin)
    factory.membership(admin_b, org_b, Role.org_admin)
    return {"org_a": org_a, "org_b": org_b, "admin_a": admin_a, "admin_b": admin_b}


def headers_for(login_fn, email, org_id):
    h = login_fn(email)
    h["X-Org-Context"] = str(org_id)
    return h


def test_custom_item_isolated_by_org(client, login, two_orgs, gap_seed):
    """Item próprio criado na Org A não aparece na Org B."""
    ha = headers_for(login, "admin@cat-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@cat-b.com", two_orgs["org_b"].id)

    r = client.post(
        "/gap/catalog/items",
        json={"dimension": "clause", "ref_code": "CUSTOM.1", "name": "Item Próprio A"},
        headers=ha,
    )
    assert r.status_code == 201
    assert r.json()["is_custom"] is True

    # Org A vê item próprio
    r = client.get("/gap/catalog", headers=ha)
    refs = [i["ref_code"] for i in r.json()]
    assert "CUSTOM.1" in refs

    # Org B não vê item da Org A
    r = client.get("/gap/catalog", headers=hb)
    refs_b = [i["ref_code"] for i in r.json()]
    assert "CUSTOM.1" not in refs_b


def test_patch_catalog_item_renames(client, login, two_orgs, gap_seed):
    """PATCH renomeia item do catálogo da Org A sem afetar Org B."""
    ha = headers_for(login, "admin@cat-a.com", two_orgs["org_a"].id)
    hb = headers_for(login, "admin@cat-b.com", two_orgs["org_b"].id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=hb)

    # Obtém item da Org A
    r = client.get("/gap/catalog", headers=ha)
    item = next(i for i in r.json() if i["ref_code"] == "4")
    item_id = item["id"]

    r = client.patch(
        f"/gap/catalog/items/{item_id}",
        json={"name": "Contexto Personalizado"},
        headers=ha,
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Contexto Personalizado"

    # Org B ainda tem o nome original
    r = client.get("/gap/catalog", headers=hb)
    item_b = next(i for i in r.json() if i["ref_code"] == "4")
    assert item_b["name"] != "Contexto Personalizado"


def test_adoption_preserves_assessments(client, login, two_orgs, gap_seed):
    """Re-adoção preserva avaliações existentes (adoção aditiva/idempotente)."""
    ha = headers_for(login, "admin@cat-a.com", two_orgs["org_a"].id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    r = client.get("/gap/assessment", headers=ha)
    item_id = r.json()["items"][0]["id"]

    # Avalia um item
    client.put(f"/gap/assessment/items/{item_id}", json={"status": "meets"}, headers=ha)

    # Re-adota (mesmo seed) — avaliação deve ser preservada
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)

    r = client.get("/gap/assessment", headers=ha)
    item = next(i for i in r.json()["items"] if i["id"] == item_id)
    assert item["status"] == "meets"


def test_seed_completeness_7_clauses_93_controls(gap_seed, db):
    """Seed 2022.1 deve ter exatamente 7 cláusulas + 93 controles do Anexo A."""
    from wtnapp.models.gap_seed_model import GapSeedItem
    from wtnapp.settings import GapDimension

    clauses = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.dimension == GapDimension.clause,
    ).count()
    assert clauses == 7, f"Esperado 7 cláusulas, encontrado {clauses}"

    annexa = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.dimension == GapDimension.annex_a,
    ).count()
    assert annexa == 93, f"Esperado 93 controles, encontrado {annexa}"

    # Conferir por tema
    from wtnapp.settings import GapTheme
    a5 = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.theme == GapTheme.organizational,
    ).count()
    a6 = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.theme == GapTheme.people,
    ).count()
    a7 = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.theme == GapTheme.physical,
    ).count()
    a8 = db.query(GapSeedItem).filter(
        GapSeedItem.seed_version_id == gap_seed.id,
        GapSeedItem.theme == GapTheme.technological,
    ).count()
    assert a5 == 37, f"A.5 esperado 37, encontrado {a5}"
    assert a6 == 8, f"A.6 esperado 8, encontrado {a6}"
    assert a7 == 14, f"A.7 esperado 14, encontrado {a7}"
    assert a8 == 34, f"A.8 esperado 34, encontrado {a8}"
