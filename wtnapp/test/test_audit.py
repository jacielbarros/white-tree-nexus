"""US5 — auditoria: completude/ausência de PII (FR-030/FR-032) e imutabilidade (FR-031)."""

import pytest
from sqlalchemy import text

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.settings import Role
from wtnapp.test.conftest import DEFAULT_PASSWORD


def _seed_and_login(client, factory):
    org = factory.org(slug="acme")
    user = factory.user(email="ana@acme.com")
    factory.membership(user, org, role=Role.org_admin)
    client.post("/auth/login", json={"email": "ana@acme.com", "password": DEFAULT_PASSWORD})
    return org, user


def test_sensitive_action_audited_without_secrets(client, factory, db):
    _org, user = _seed_and_login(client, factory)

    logins = db.query(AuditLog).filter(
        AuditLog.operation == "LOGIN", AuditLog.outcome == "success"
    ).all()
    assert len(logins) == 1
    entry = logins[0]
    assert entry.actor_user_id == user.id
    assert entry.entity_type == "user"

    # Nenhum registro contém a senha em texto claro (FR-032).
    for a in db.query(AuditLog).all():
        assert DEFAULT_PASSWORD not in f"{a.details}"


def test_audit_log_is_append_only(client, factory, db):
    _seed_and_login(client, factory)
    db.expire_all()
    assert db.query(AuditLog).count() >= 1

    # UPDATE bloqueado pelo gatilho (FR-031)
    with pytest.raises(Exception):
        db.execute(text("UPDATE audit_logs SET outcome = 'tampered'"))
        db.commit()
    db.rollback()

    # DELETE bloqueado pelo gatilho
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM audit_logs"))
        db.commit()
    db.rollback()

    assert db.query(AuditLog).count() >= 1
