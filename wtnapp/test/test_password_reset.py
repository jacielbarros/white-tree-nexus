"""US4 — definição/redefinição de senha (FR-013/FR-014/FR-009a)."""

import time
import uuid
from datetime import datetime, timedelta, timezone

from wtnapp.models.password_reset_model import PasswordResetToken
from wtnapp.models.user_model import User
from wtnapp.settings import Role
from wtnapp.test.conftest import DEFAULT_PASSWORD

NEW_PASSWORD = "OutraSenhaForte!77"


def _seeded(factory, email="ana@acme.com"):
    org = factory.org(slug="acme")
    user = factory.user(email=email)
    factory.membership(user, org, role=Role.org_admin)
    return org, user


def test_forgot_is_generic_for_existing_and_unknown(client, factory, outbox):
    _seeded(factory)
    r1 = client.post("/auth/password/forgot", json={"email": "ana@acme.com"})
    r2 = client.post("/auth/password/forgot", json={"email": "ghost@nowhere.com"})
    assert r1.status_code == 202 and r2.status_code == 202
    assert r1.json() == r2.json()  # resposta idêntica — sem enumeração


def test_reset_changes_password_single_use(client, factory, outbox):
    _seeded(factory)
    client.post("/auth/password/forgot", json={"email": "ana@acme.com"})
    token = outbox[-1]["token"]

    assert client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}).status_code == 204
    # nova senha funciona; antiga não
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": NEW_PASSWORD}).status_code == 200
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD}).status_code == 401
    # token de uso único: reuso ⇒ 400
    assert client.post("/auth/password/reset", json={"token": token, "password": "MaisUma!Senha9"}).status_code == 400


def test_reset_invalidates_prior_sessions(client, factory, login, outbox):
    """FR-014 — sessões emitidas antes da troca deixam de valer."""
    _seeded(factory)
    headers = login("ana@acme.com")
    assert client.get("/me", headers=headers).status_code == 200

    time.sleep(1.1)  # cruza o limite de segundo (granularidade de iat vs password_changed_at)
    client.post("/auth/password/forgot", json={"email": "ana@acme.com"})
    token = outbox[-1]["token"]
    assert client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}).status_code == 204

    assert client.get("/me", headers=headers).status_code == 401


def test_reset_clears_lockout(client, factory, db, outbox):
    """FR-009a — redefinição de senha limpa o bloqueio."""
    _org, user = _seeded(factory)
    locked = db.get(User, user.id)
    locked.failed_login_count = 5
    locked.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()

    client.post("/auth/password/forgot", json={"email": "ana@acme.com"})
    token = outbox[-1]["token"]
    assert client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}).status_code == 204

    db.expire_all()
    refreshed = db.get(User, user.id)
    assert refreshed.failed_login_count == 0 and refreshed.locked_until is None
    assert client.post("/auth/login", json={"email": "ana@acme.com", "password": NEW_PASSWORD}).status_code == 200


def test_expired_reset_token_rejected(client, factory, db, outbox):
    _org, user = _seeded(factory)
    client.post("/auth/password/forgot", json={"email": "ana@acme.com"})
    token = outbox[-1]["token"]

    record = db.query(PasswordResetToken).filter(PasswordResetToken.user_id == user.id).first()
    record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert client.post("/auth/password/reset", json={"token": token, "password": NEW_PASSWORD}).status_code == 400
