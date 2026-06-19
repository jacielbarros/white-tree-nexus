"""US3 — RBAC e gestão de vínculos: permissão negada, mudança de papel, salvaguardas, desbloqueio."""

from datetime import datetime, timedelta, timezone

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.user_model import User
from wtnapp.settings import Role
from wtnapp.test.conftest import DEFAULT_PASSWORD


def _headers(client, email):
    resp = client.post("/auth/login", json={"email": email, "password": DEFAULT_PASSWORD})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_invite_without_permission_denied_and_audited(client, factory, db):
    org = factory.org(slug="acme")
    member = factory.user(email="cli@acme.com")
    factory.membership(member, org, role=Role.client)  # client não tem invite_users

    resp = client.post(
        "/invitations", json={"email": "x@acme.com", "role": "manager"}, headers=_headers(client, "cli@acme.com")
    )
    assert resp.status_code == 403
    denied = db.query(AuditLog).filter(AuditLog.operation == "PERMISSION_DENIED").count()
    assert denied >= 1


def test_role_change_is_audited(client, factory, db):
    org = factory.org(slug="acme")
    admin = factory.user(email="admin@acme.com")
    factory.membership(admin, org, role=Role.org_admin)
    member = factory.user(email="bob@acme.com")
    m = factory.membership(member, org, role=Role.manager)

    resp = client.patch(
        f"/memberships/{m.id}/role", json={"role": "control_owner"}, headers=_headers(client, "admin@acme.com")
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "control_owner"
    assert db.query(AuditLog).filter(AuditLog.operation == "ROLE_CHANGE").count() == 1


def test_last_admin_safeguard(client, factory):
    org = factory.org(slug="acme")
    admin = factory.user(email="admin@acme.com")
    m = factory.membership(admin, org, role=Role.org_admin)  # único admin

    resp = client.patch(
        f"/memberships/{m.id}/role", json={"role": "manager"}, headers=_headers(client, "admin@acme.com")
    )
    assert resp.status_code == 409  # FR-022


def test_manual_unlock_clears_lock(client, factory, db):
    """FR-009a/SC-003 — desbloqueio manual por admin autorizado, auditado."""
    org = factory.org(slug="acme")
    admin = factory.user(email="admin@acme.com")
    factory.membership(admin, org, role=Role.org_admin)
    member = factory.user(email="bob@acme.com")
    factory.membership(member, org, role=Role.manager)

    locked = db.get(User, member.id)
    locked.failed_login_count = 5
    locked.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    # bloqueado: não consegue logar
    assert client.post("/auth/login", json={"email": "bob@acme.com", "password": DEFAULT_PASSWORD}).status_code == 401

    unlocked = client.post(f"/users/{member.id}/unlock", headers=_headers(client, "admin@acme.com"))
    assert unlocked.status_code == 204
    assert client.post("/auth/login", json={"email": "bob@acme.com", "password": DEFAULT_PASSWORD}).status_code == 200
    assert db.query(AuditLog).filter(AuditLog.operation == "ACCOUNT_UNLOCKED").count() == 1


def test_unlock_without_permission_denied(client, factory):
    org = factory.org(slug="acme")
    cli = factory.user(email="cli@acme.com")
    factory.membership(cli, org, role=Role.client)
    target = factory.user(email="bob@acme.com")
    factory.membership(target, org, role=Role.manager)

    resp = client.post(f"/users/{target.id}/unlock", headers=_headers(client, "cli@acme.com"))
    assert resp.status_code == 403
