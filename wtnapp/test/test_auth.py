"""US1 — autenticação: happy path, expiração de sessão e logout (revogação de jti)."""

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.services import token_service
from wtnapp.settings import Role
from wtnapp.test.conftest import DEFAULT_PASSWORD


def test_login_success_returns_token_and_audits(client, factory, db):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org, role=Role.org_admin)

    resp = client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0

    logins = db.query(AuditLog).filter(AuditLog.operation == "LOGIN", AuditLog.outcome == "success").all()
    assert len(logins) == 1
    assert logins[0].actor_user_id == user.id


def test_me_requires_authentication(client):
    assert client.get("/me").status_code == 401


def test_me_returns_memberships(client, factory, login):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org, role=Role.manager)

    headers = login("ana@acme.com")
    resp = client.get("/me", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "ana@acme.com"
    assert len(body["memberships"]) == 1
    assert body["memberships"][0]["role"] == "manager"


def test_logout_revokes_token(client, factory, login):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org)

    headers = login("ana@acme.com")
    # token válido antes do logout
    assert client.get("/me", headers=headers).status_code == 200
    # logout encerra a sessão
    assert client.post("/auth/logout", headers=headers).status_code == 204
    # reuso do mesmo token é negado
    assert client.get("/me", headers=headers).status_code == 401


def test_expired_token_is_rejected(client, factory, monkeypatch):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org)

    # Emite um token já expirado (TOKEN_EXPIRY_MINUTES negativo).
    monkeypatch.setattr(token_service.settings, "TOKEN_EXPIRY_MINUTES", -1)
    token, _jti, _exp = token_service.create_access_token(
        user_id=user.id, tenant_ids=[org.id], super_admin=False
    )
    resp = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
