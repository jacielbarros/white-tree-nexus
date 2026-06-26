"""Feature 011 — vínculo item ↔ gap do catálogo da org."""

import pytest

from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.settings import GapDimension, Role


@pytest.fixture
def gap_link_org(factory, db):
    org = factory.org("gaplink-acme", "GapLink Acme")
    admin = factory.user("admin@gaplink-acme.com")
    factory.membership(admin, org, Role.org_admin)
    gap = GapCatalogItem(
        tenant_id=org.id, dimension=GapDimension.annex_a, ref_code="A.5.1",
        name="Políticas de segurança da informação", objective="", order=1,
    )
    db.add(gap)
    db.commit()
    db.refresh(gap)
    return {"org": org, "admin": admin, "gap": gap}


def _item(client, h):
    return client.post("/assets", headers=h, json={"name": "Inventário", "item_type": "document", "scope_status": "under_analysis"}).json()


def test_link_and_show_on_detail(client, org_headers, gap_link_org):
    h = org_headers(gap_link_org["admin"].email, gap_link_org["org"].id)
    item = _item(client, h)
    resp = client.post(f"/assets/{item['id']}/gap-links", headers=h, json={
        "gap_catalog_item_id": str(gap_link_org["gap"].id), "note": "Endereça o gap",
    })
    assert resp.status_code == 201, resp.text
    detail = client.get(f"/assets/{item['id']}", headers=h).json()
    assert len(detail["gap_links"]) == 1
    assert detail["gap_links"][0]["gap_ref_code"] == "A.5.1"


def test_duplicate_link_blocked(client, org_headers, gap_link_org):
    h = org_headers(gap_link_org["admin"].email, gap_link_org["org"].id)
    item = _item(client, h)
    payload = {"gap_catalog_item_id": str(gap_link_org["gap"].id)}
    client.post(f"/assets/{item['id']}/gap-links", headers=h, json=payload)
    dup = client.post(f"/assets/{item['id']}/gap-links", headers=h, json=payload)
    assert dup.status_code == 409


def test_link_gap_of_other_tenant_denied(client, org_headers, gap_link_org, factory, db):
    other = factory.org("gaplink-other", "Other")
    admin_other = factory.user("admin@gaplink-other.com")
    factory.membership(admin_other, other, Role.org_admin)
    h = org_headers(gap_link_org["admin"].email, gap_link_org["org"].id)
    item = _item(client, h)
    # gap pertence ao gap_link_org; tenta vincular a partir de outro tenant
    h_other = org_headers(admin_other.email, other.id)
    item_other = _item(client, h_other)
    resp = client.post(f"/assets/{item_other['id']}/gap-links", headers=h_other, json={
        "gap_catalog_item_id": str(gap_link_org["gap"].id),
    })
    assert resp.status_code == 404


def test_unlink_gap(client, org_headers, gap_link_org):
    h = org_headers(gap_link_org["admin"].email, gap_link_org["org"].id)
    item = _item(client, h)
    link = client.post(f"/assets/{item['id']}/gap-links", headers=h, json={
        "gap_catalog_item_id": str(gap_link_org["gap"].id),
    }).json()
    resp = client.delete(f"/assets/{item['id']}/gap-links/{link['id']}", headers=h)
    assert resp.status_code == 204
    assert client.get(f"/assets/{item['id']}", headers=h).json()["gap_links"] == []
