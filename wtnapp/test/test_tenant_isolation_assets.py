"""Feature 011 — isolamento de tenant (obrigatório)."""

import pytest

from wtnapp.settings import Role


@pytest.fixture
def two_orgs(factory):
    a = factory.org("iso-a", "ISO A")
    b = factory.org("iso-b", "ISO B")
    admin_a = factory.user("admin@iso-a.com")
    admin_b = factory.user("admin@iso-b.com")
    factory.membership(admin_a, a, Role.org_admin)
    factory.membership(admin_b, b, Role.org_admin)
    return {"a": a, "b": b, "admin_a": admin_a, "admin_b": admin_b}


def test_cannot_read_item_of_other_tenant(client, org_headers, two_orgs):
    ha = org_headers(two_orgs["admin_a"].email, two_orgs["a"].id)
    hb = org_headers(two_orgs["admin_b"].email, two_orgs["b"].id)
    item = client.post("/assets", headers=ha, json={"name": "Secreto A", "item_type": "system", "scope_status": "under_analysis"}).json()

    # B tenta ler item de A => 404 genérico
    assert client.get(f"/assets/{item['id']}", headers=hb).status_code == 404
    # B não vê item de A na listagem
    assert client.get("/assets", headers=hb).json() == []


def test_cannot_update_or_archive_other_tenant(client, org_headers, two_orgs):
    ha = org_headers(two_orgs["admin_a"].email, two_orgs["a"].id)
    hb = org_headers(two_orgs["admin_b"].email, two_orgs["b"].id)
    item = client.post("/assets", headers=ha, json={"name": "A", "item_type": "system", "scope_status": "under_analysis"}).json()

    assert client.put(f"/assets/{item['id']}", headers=hb, json={
        "name": "Hack", "item_type": "system", "scope_status": "under_analysis",
    }).status_code == 404
    assert client.post(f"/assets/{item['id']}/archive", headers=hb, json={"reason": "x"}).status_code == 404
    assert client.get(f"/assets/{item['id']}/history", headers=hb).status_code == 404


def test_cannot_relate_across_tenants(client, org_headers, two_orgs):
    ha = org_headers(two_orgs["admin_a"].email, two_orgs["a"].id)
    hb = org_headers(two_orgs["admin_b"].email, two_orgs["b"].id)
    item_a = client.post("/assets", headers=ha, json={"name": "A", "item_type": "system", "scope_status": "under_analysis"}).json()
    item_b = client.post("/assets", headers=hb, json={"name": "B", "item_type": "system", "scope_status": "under_analysis"}).json()

    # A tenta relacionar item de A com item de B (de outro tenant) => 404 (target não encontrado no tenant)
    resp = client.post(f"/assets/{item_a['id']}/relationships", headers=ha, json={
        "relationship_type": "uses", "target_item_id": item_b["id"],
    })
    assert resp.status_code == 404
