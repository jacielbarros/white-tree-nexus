"""Feature 011 — relacionamentos entre itens."""

import pytest

from wtnapp.settings import Role


@pytest.fixture
def rel_org(factory):
    org = factory.org("rel-acme", "Rel Acme")
    admin = factory.user("admin@rel-acme.com")
    factory.membership(admin, org, Role.org_admin)
    return {"org": org, "admin": admin}


def _two_items(client, h):
    a = client.post("/assets", headers=h, json={"name": "Processo X", "item_type": "business_process", "scope_status": "under_analysis"}).json()
    b = client.post("/assets", headers=h, json={"name": "Sistema Y", "item_type": "system", "scope_status": "under_analysis"}).json()
    return a, b


def test_create_relationship_shows_on_both_sides(client, org_headers, rel_org):
    h = org_headers(rel_org["admin"].email, rel_org["org"].id)
    a, b = _two_items(client, h)
    resp = client.post(f"/assets/{a['id']}/relationships", headers=h, json={
        "relationship_type": "uses", "target_item_id": b["id"], "description": "X usa Y",
    })
    assert resp.status_code == 201, resp.text

    # saída na origem
    da = client.get(f"/assets/{a['id']}", headers=h).json()
    assert len(da["relationships"]) == 1
    assert da["relationships"][0]["direction"] == "outgoing"
    assert da["relationships"][0]["target_code"] == b["code"]
    # entrada no destino
    db_ = client.get(f"/assets/{b['id']}", headers=h).json()
    assert len(db_["relationships"]) == 1
    assert db_["relationships"][0]["direction"] == "incoming"


def test_self_relationship_blocked(client, org_headers, rel_org):
    h = org_headers(rel_org["admin"].email, rel_org["org"].id)
    a, _ = _two_items(client, h)
    resp = client.post(f"/assets/{a['id']}/relationships", headers=h, json={
        "relationship_type": "linked_to", "target_item_id": a["id"],
    })
    assert resp.status_code == 422


def test_duplicate_relationship_blocked(client, org_headers, rel_org):
    h = org_headers(rel_org["admin"].email, rel_org["org"].id)
    a, b = _two_items(client, h)
    client.post(f"/assets/{a['id']}/relationships", headers=h, json={"relationship_type": "uses", "target_item_id": b["id"]})
    dup = client.post(f"/assets/{a['id']}/relationships", headers=h, json={"relationship_type": "uses", "target_item_id": b["id"]})
    assert dup.status_code == 409


def test_remove_relationship(client, org_headers, rel_org):
    h = org_headers(rel_org["admin"].email, rel_org["org"].id)
    a, b = _two_items(client, h)
    rel = client.post(f"/assets/{a['id']}/relationships", headers=h, json={"relationship_type": "uses", "target_item_id": b["id"]}).json()
    resp = client.delete(f"/assets/{a['id']}/relationships/{rel['id']}", headers=h)
    assert resp.status_code == 204
    assert client.get(f"/assets/{a['id']}", headers=h).json()["relationships"] == []
