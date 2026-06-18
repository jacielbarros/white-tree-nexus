"""US2 — bootstrap do 1º Super Admin (FR-001/SC-007): único, guardado por BOOTSTRAP_TOKEN."""

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.user_model import User

BOOTSTRAP_TOKEN = "test-bootstrap-token"  # casado com conftest


def _payload(**over):
    base = {
        "bootstrap_token": BOOTSTRAP_TOKEN,
        "email": "root@plataforma.com",
        "full_name": "Root",
        "password": "Sup3rSecret!2345",
    }
    base.update(over)
    return base


def test_bootstrap_creates_first_super_admin(client, db):
    resp = client.post("/bootstrap/super-admin", json=_payload())
    assert resp.status_code == 201
    body = resp.json()
    assert body["is_super_admin"] is True
    assert body["email"] == "root@plataforma.com"

    assert db.query(User).filter(User.is_platform_super_admin.is_(True)).count() == 1
    audits = db.query(AuditLog).filter(
        AuditLog.operation == "BOOTSTRAP", AuditLog.outcome == "success"
    ).all()
    assert len(audits) == 1


def test_bootstrap_rejected_when_super_admin_exists(client):
    assert client.post("/bootstrap/super-admin", json=_payload()).status_code == 201
    # Segunda chamada ⇒ 409 (SC-007)
    second = client.post("/bootstrap/super-admin", json=_payload(email="other@plataforma.com"))
    assert second.status_code == 409


def test_bootstrap_rejected_with_bad_token(client, db):
    resp = client.post("/bootstrap/super-admin", json=_payload(bootstrap_token="wrong"))
    assert resp.status_code == 401
    assert db.query(User).filter(User.is_platform_super_admin.is_(True)).count() == 0
