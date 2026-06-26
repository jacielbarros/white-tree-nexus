"""Feature 011 — CRUD, código interno, classificação CIA/criticidade, validações, arquivamento."""

import pytest

from wtnapp.settings import Role


@pytest.fixture
def asset_org(factory):
    org = factory.org("asset-acme", "Asset Acme")
    admin = factory.user("admin@asset-acme.com", full_name="Admin Asset")
    consultant = factory.user("consultant@asset-acme.com", full_name="Consultant Asset")
    client_user = factory.user("client@asset-acme.com", full_name="Client Asset")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(consultant, org, Role.consultant)
    factory.membership(client_user, org, Role.client)
    return {"org": org, "admin": admin, "consultant": consultant, "client": client_user}


def _headers(org_headers, asset_org, who="admin"):
    user = asset_org[who]
    return org_headers(user.email, asset_org["org"].id)


def test_create_minimal_item_generates_code(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Servidor de arquivos", "item_type": "information_asset", "scope_status": "under_analysis",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "ATV-0001"
    assert body["review_status"] == "undefined"
    assert "responsible" in body["pending_fields"]


def test_code_sequence_per_type(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    c1 = client.post("/assets", headers=h, json={"name": "A1", "item_type": "information_asset", "scope_status": "under_analysis"})
    c2 = client.post("/assets", headers=h, json={"name": "A2", "item_type": "information_asset", "scope_status": "under_analysis"})
    p1 = client.post("/assets", headers=h, json={"name": "P1", "item_type": "business_process", "scope_status": "under_analysis"})
    assert c1.json()["code"] == "ATV-0001"
    assert c2.json()["code"] == "ATV-0002"
    assert p1.json()["code"] == "PROC-0001"


def test_code_is_immutable_when_type_changes(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    created = client.post("/assets", headers=h, json={"name": "X", "item_type": "system", "scope_status": "under_analysis"}).json()
    assert created["code"] == "SIS-0001"
    upd = client.put(f"/assets/{created['id']}", headers=h, json={
        "name": "X", "item_type": "database", "scope_status": "under_analysis",
    })
    assert upd.status_code == 200, upd.text
    assert upd.json()["code"] == "SIS-0001"  # imutável
    assert upd.json()["item_type"] == "database"


def test_in_scope_requires_responsible_and_cia(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Sem responsável", "item_type": "information_asset", "scope_status": "in_scope",
    })
    assert resp.status_code == 422
    assert "responsável" in resp.json()["detail"].lower() or "cia" in resp.json()["detail"].lower()


def test_in_scope_ok_with_responsible_and_cia(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Completo", "item_type": "information_asset", "scope_status": "in_scope",
        "responsible_user_id": str(asset_org["admin"].id),
        "confidentiality": "alta", "integrity": "media", "availability": "baixa",
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["criticality"] == "alta"  # max(alta, media, baixa)
    assert body["cia_complete"] is True
    assert body["pending_fields"] == []


def test_out_of_scope_requires_justification(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Fora", "item_type": "service", "scope_status": "out_of_scope",
    })
    assert resp.status_code == 422
    assert "justificativa" in resp.json()["detail"].lower()


def test_criticality_manual_override_and_divergence(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Override", "item_type": "system", "scope_status": "under_analysis",
        "confidentiality": "baixa", "integrity": "baixa", "availability": "baixa",
        "criticality": "critica", "criticality_is_manual": True,
    })
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["criticality"] == "critica"
    assert body["criticality_is_manual"] is True
    assert body["criticality_computed"] == "baixa"
    assert body["criticality_divergent"] is True


def test_duplicate_name_same_type_blocked(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    client.post("/assets", headers=h, json={"name": "Dup", "item_type": "service", "scope_status": "under_analysis"})
    resp = client.post("/assets", headers=h, json={"name": "Dup", "item_type": "service", "scope_status": "under_analysis"})
    assert resp.status_code == 409
    # mesmo nome em outro tipo é permitido
    ok = client.post("/assets", headers=h, json={"name": "Dup", "item_type": "document", "scope_status": "under_analysis"})
    assert ok.status_code == 201
    # duplicidade permitida com justificativa
    ok2 = client.post("/assets", headers=h, json={
        "name": "Dup", "item_type": "service", "scope_status": "under_analysis",
        "allow_duplicate": True, "reason": "Instância distinta",
    })
    assert ok2.status_code == 201


def test_archive_requires_justification_and_is_logical(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    created = client.post("/assets", headers=h, json={"name": "Arq", "item_type": "other", "scope_status": "under_analysis"}).json()
    no_reason = client.post(f"/assets/{created['id']}/archive", headers=h, json={"reason": "  "})
    assert no_reason.status_code == 422
    ok = client.post(f"/assets/{created['id']}/archive", headers=h, json={"reason": "Descontinuado"})
    assert ok.status_code == 200
    assert ok.json()["record_status"] == "archived"
    # ainda existe (arquivamento lógico)
    got = client.get(f"/assets/{created['id']}", headers=h)
    assert got.status_code == 200


def test_related_item_cross_tenant_rejected(client, org_headers, asset_org, factory):
    other = factory.org("other-asset", "Other Asset")
    admin_other = factory.user("admin@other-asset.com")
    factory.membership(admin_other, other, Role.org_admin)
    h_other = org_headers(admin_other.email, other.id)
    foreign = client.post("/assets", headers=h_other, json={"name": "Foreign", "item_type": "system", "scope_status": "under_analysis"}).json()

    h = _headers(org_headers, asset_org)
    resp = client.post("/assets", headers=h, json={
        "name": "Tem relacionado", "item_type": "business_process", "scope_status": "under_analysis",
        "related_system_id": foreign["id"],
    })
    assert resp.status_code == 404


def test_member_only_responsible(client, org_headers, asset_org, factory):
    h = _headers(org_headers, asset_org)
    outsider = factory.user("outsider@nowhere.com")  # não é membro
    resp = client.post("/assets", headers=h, json={
        "name": "Resp inválido", "item_type": "system", "scope_status": "in_scope",
        "responsible_user_id": str(outsider.id),
        "confidentiality": "alta", "integrity": "alta", "availability": "alta",
    })
    assert resp.status_code == 422


def test_view_role_cannot_create(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org, who="client")  # client tem só view_asset
    resp = client.post("/assets", headers=h, json={"name": "Nope", "item_type": "system", "scope_status": "under_analysis"})
    assert resp.status_code == 403


def test_list_filters_and_search(client, org_headers, asset_org):
    h = _headers(org_headers, asset_org)
    client.post("/assets", headers=h, json={"name": "Firewall", "item_type": "infrastructure", "scope_status": "under_analysis", "description": "borda da rede"})
    client.post("/assets", headers=h, json={"name": "ERP", "item_type": "system", "scope_status": "in_scope",
                                            "responsible_user_id": str(asset_org["admin"].id),
                                            "confidentiality": "alta", "integrity": "alta", "availability": "alta"})
    # filtro por tipo
    r = client.get("/assets", headers=h, params={"item_type": "system"})
    assert len(r.json()) == 1 and r.json()[0]["name"] == "ERP"
    # filtro sem responsável
    r2 = client.get("/assets", headers=h, params={"without_responsible": "true"})
    assert {i["name"] for i in r2.json()} == {"Firewall"}
    # busca textual
    r3 = client.get("/assets", headers=h, params={"q": "borda"})
    assert len(r3.json()) == 1 and r3.json()[0]["name"] == "Firewall"
