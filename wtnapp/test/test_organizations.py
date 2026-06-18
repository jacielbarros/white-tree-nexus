"""US2 — ciclo de vida de organizações (FR-002..005) + listagem escopada (FR-005 / SC-008)."""

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.settings import OrgStatus, Role
from wtnapp.test.conftest import DEFAULT_PASSWORD


def _super_admin_headers(client, factory):
    factory.user(email="root@plat.com", super_admin=True)
    resp = client.post("/auth/login", json={"email": "root@plat.com", "password": DEFAULT_PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_super_admin_creates_organization(client, factory, db):
    headers = _super_admin_headers(client, factory)
    resp = client.post("/organizations", json={"name": "ACME S/A", "slug": "acme"}, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["slug"] == "acme"
    assert resp.json()["status"] == "active"

    created = db.query(AuditLog).filter(AuditLog.operation == "ORG_CREATE").all()
    assert len(created) == 1


def test_duplicate_slug_conflicts(client, factory):
    headers = _super_admin_headers(client, factory)
    client.post("/organizations", json={"name": "ACME", "slug": "acme"}, headers=headers)
    dup = client.post("/organizations", json={"name": "Outra", "slug": "acme"}, headers=headers)
    assert dup.status_code == 409


def test_non_super_admin_cannot_create_org(client, factory):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org, role=Role.org_admin)
    resp = client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD})
    headers = {"Authorization": f"Bearer {resp.json()['access_token']}"}

    created = client.post(
        "/organizations", json={"name": "Nova", "slug": "nova"},
        headers={**headers, "X-Org-Context": str(org.id)},
    )
    assert created.status_code == 403


def test_suspend_blocks_users_then_reactivate_restores(client, factory, db):
    headers = _super_admin_headers(client, factory)
    org = factory.org(slug="acme")
    member = factory.user(email="ana@acme.com")
    factory.membership(member, org, role=Role.org_admin)

    # membro consegue logar com org ativa
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD}).status_code == 200

    # suspende → fail-closed (FR-004)
    suspend = client.patch(f"/organizations/{org.id}/status", json={"action": "suspend"}, headers=headers)
    assert suspend.status_code == 200 and suspend.json()["status"] == "suspended"
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD}).status_code == 401

    # reativa → restaura acesso
    react = client.patch(f"/organizations/{org.id}/status", json={"action": "reactivate"}, headers=headers)
    assert react.status_code == 200 and react.json()["status"] == "active"
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD}).status_code == 200

    changes = db.query(AuditLog).filter(AuditLog.operation == "ORG_STATUS_CHANGE").count()
    assert changes == 2


def test_organization_listing_is_scoped(client, factory):
    """FR-005/SC-008 — Super Admin vê todas; membro vê só a(s) sua(s)."""
    sa_headers = _super_admin_headers(client, factory)
    org_a = factory.org(slug="org-a")
    org_b = factory.org(slug="org-b")
    user_a = factory.user(email="ana@org-a.com")
    factory.membership(user_a, org_a, role=Role.manager)

    # Super Admin vê as duas
    sa_list = client.get("/organizations", headers=sa_headers)
    assert sa_list.status_code == 200
    assert {o["slug"] for o in sa_list.json()} >= {"org-a", "org-b"}

    # Membro de A vê apenas A
    login_a = client.post("/auth/login", json={"email": "ana@org-a.com", "password": DEFAULT_PASSWORD})
    a_headers = {"Authorization": f"Bearer {login_a.json()['access_token']}"}
    a_list = client.get("/organizations", headers=a_headers)
    assert a_list.status_code == 200
    slugs = {o["slug"] for o in a_list.json()}
    assert slugs == {"org-a"}

    # Acesso direto a org alheia por id ⇒ 404 (não revela existência)
    assert client.get(f"/organizations/{org_b.id}", headers=a_headers).status_code == 404
