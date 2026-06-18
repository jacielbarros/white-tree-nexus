"""US1 — falhas de auth: credencial inválida genérica, bloqueio, org suspensa, auto-expiração."""

from datetime import datetime, timedelta, timezone

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.user_model import User
from wtnapp.settings import OrgStatus, Role
from wtnapp.test.conftest import DEFAULT_PASSWORD


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


def test_invalid_password_and_unknown_email_share_generic_error(client, factory):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org)

    wrong = _login(client, "ana@acme.com", "wrong-password-xx")
    unknown = _login(client, "ghost@nowhere.com", "whatever-xx-123")

    assert wrong.status_code == 401
    assert unknown.status_code == 401
    # Mesma mensagem genérica — não revela se o e-mail existe (FR-011)
    assert wrong.json()["detail"] == unknown.json()["detail"]


def test_account_locks_after_max_attempts(client, factory, db):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org)

    for _ in range(5):  # MAX_LOGIN_ATTEMPTS=5
        assert _login(client, "ana@acme.com", "bad-bad-bad-1").status_code == 401

    # Mesmo com a senha correta, a conta está bloqueada.
    assert _login(client, "ana@acme.com", DEFAULT_PASSWORD).status_code == 401

    db.expire_all()  # recarrega: a API mutou via outra sessão
    refreshed = db.get(User, user.id)
    assert refreshed.locked_until is not None
    locked_events = db.query(AuditLog).filter(AuditLog.operation == "ACCOUNT_LOCKED").all()
    assert len(locked_events) == 1


def test_lock_auto_expires(client, factory, db):
    """FR-009a/SC-003 — auto-expiração: com locked_until no passado, o login volta a funcionar."""
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org)

    # Simula bloqueio cuja janela já expirou.
    locked = db.get(User, user.id)
    locked.failed_login_count = 5
    locked.locked_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    resp = _login(client, "ana@acme.com", DEFAULT_PASSWORD)
    assert resp.status_code == 200
    db.expire_all()  # recarrega: a API mutou via outra sessão
    assert db.get(User, user.id).failed_login_count == 0


def test_user_of_suspended_org_cannot_login(client, factory):
    """FR-004 — suspensão é fail-closed."""
    org = factory.org(slug="acme", status=OrgStatus.suspended)
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org, role=Role.org_admin)

    assert _login(client, "ana@acme.com", DEFAULT_PASSWORD).status_code == 401
