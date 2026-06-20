"""US3 — convites: criar/aceitar, duplicados, expirado/revogado, e fluxo do admin inicial (FR-002a)."""

import uuid
from datetime import datetime, timedelta, timezone

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.invitation_model import Invitation
from wtnapp.settings import InviteStatus, Role
from wtnapp.test.conftest import DEFAULT_PASSWORD

NEW_PASSWORD = "N0vaSenhaForte!99"


def _admin(client, factory, slug="acme"):
    org = factory.org(slug=slug)
    admin = factory.user(email=f"admin@{slug}.com")
    factory.membership(admin, org, role=Role.org_admin)
    resp = client.post("/auth/login", json={"email": f"admin@{slug}.com", "password": DEFAULT_PASSWORD})
    return org, admin, {"Authorization": f"Bearer {resp.json()['access_token']}"}


def test_create_and_accept_invitation(client, factory, db, outbox):
    org, _admin_user, headers = _admin(client, factory)

    created = client.post(
        "/invitations", json={"email": "bob@acme.com", "role": "manager"}, headers=headers
    )
    assert created.status_code == 201
    assert created.json()["status"] == "pending"
    token = outbox[-1]["token"]

    accepted = client.post(
        "/invitations/accept",
        json={"token": token, "full_name": "Bob", "password": NEW_PASSWORD},
    )
    assert accepted.status_code == 200
    assert accepted.json()["access_token"]

    # Novo usuário consegue autenticar
    assert client.post("/auth/login", json={"email": "bob@acme.com", "password": NEW_PASSWORD}).status_code == 200

    ops = {a.operation for a in db.query(AuditLog).all()}
    assert {"USER_INVITE", "INVITE_ACCEPT"} <= ops


def test_existing_user_accepts_without_password(client, factory, db, outbox):
    """Usuário que JÁ tem conta é convidado: aceita sem redefinir a senha atual."""
    _org, _admin_user, headers = _admin(client, factory)
    # Conta já existente, sem vínculo nesta org (ex.: Super Admin ou Consultor de outra org).
    factory.user(email="carol@elsewhere.com", full_name="Carol")

    invited = client.post(
        "/invitations", json={"email": "carol@elsewhere.com", "role": "manager"}, headers=headers
    )
    assert invited.status_code == 201
    assert outbox[-1]["existing_user"] is True  # e-mail usa o template de usuário existente
    token = outbox[-1]["token"]

    # Aceita SEM enviar senha.
    accepted = client.post("/invitations/accept", json={"token": token})
    assert accepted.status_code == 200
    assert accepted.json()["access_token"]

    # A senha original continua válida (não foi sobrescrita).
    assert (
        client.post(
            "/auth/login", json={"email": "carol@elsewhere.com", "password": DEFAULT_PASSWORD}
        ).status_code
        == 200
    )


def test_lookup_distinguishes_new_vs_existing(client, factory, outbox):
    org, _admin_user, headers = _admin(client, factory)

    # Novo e-mail (sem conta) → requires_password True
    client.post("/invitations", json={"email": "dave@acme.com", "role": "manager"}, headers=headers)
    look_new = client.get("/invitations/lookup", params={"token": outbox[-1]["token"]})
    assert look_new.status_code == 200
    assert look_new.json()["requires_password"] is True
    assert look_new.json()["org_name"] == org.name

    # E-mail já cadastrado → requires_password False
    factory.user(email="erin@elsewhere.com", full_name="Erin")
    client.post("/invitations", json={"email": "erin@elsewhere.com", "role": "manager"}, headers=headers)
    look_existing = client.get("/invitations/lookup", params={"token": outbox[-1]["token"]})
    assert look_existing.status_code == 200
    assert look_existing.json()["requires_password"] is False


def test_lookup_invalid_token_rejected(client):
    assert client.get("/invitations/lookup", params={"token": "token-inexistente"}).status_code == 400


def test_duplicate_pending_invite_conflicts(client, factory, outbox):
    _org, _admin_user, headers = _admin(client, factory)
    first = client.post("/invitations", json={"email": "bob@acme.com", "role": "manager"}, headers=headers)
    assert first.status_code == 201
    dup = client.post("/invitations", json={"email": "bob@acme.com", "role": "manager"}, headers=headers)
    assert dup.status_code == 409


def test_invite_existing_member_conflicts(client, factory, outbox):
    org, _admin_user, headers = _admin(client, factory)
    member = factory.user(email="bob@acme.com")
    factory.membership(member, org, role=Role.manager)
    resp = client.post("/invitations", json={"email": "bob@acme.com", "role": "client"}, headers=headers)
    assert resp.status_code == 409


def test_accept_revoked_invite_rejected(client, factory, db, outbox):
    _org, _admin_user, headers = _admin(client, factory)
    created = client.post("/invitations", json={"email": "bob@acme.com", "role": "manager"}, headers=headers)
    token = outbox[-1]["token"]
    invite_id = created.json()["id"]

    assert client.post(f"/invitations/{invite_id}/revoke", headers=headers).status_code == 204
    accepted = client.post(
        "/invitations/accept", json={"token": token, "full_name": "Bob", "password": NEW_PASSWORD}
    )
    assert accepted.status_code == 400


def test_accept_expired_invite_rejected(client, factory, db, outbox):
    _org, _admin_user, headers = _admin(client, factory)
    created = client.post("/invitations", json={"email": "bob@acme.com", "role": "manager"}, headers=headers)
    token = outbox[-1]["token"]

    invite = db.get(Invitation, uuid.UUID(created.json()["id"]))
    invite.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.commit()

    accepted = client.post(
        "/invitations/accept", json={"token": token, "full_name": "Bob", "password": NEW_PASSWORD}
    )
    assert accepted.status_code == 400


def test_initial_admin_via_invitation_flow(client, factory, db, outbox):
    """FR-002a / US2-cenário 7 — Super Admin convida o admin inicial de uma org nova."""
    factory.user(email="root@plat.com", super_admin=True)
    sa = client.post("/auth/login", json={"email": "root@plat.com", "password": DEFAULT_PASSWORD})
    sa_headers = {"Authorization": f"Bearer {sa.json()['access_token']}"}

    org_id = client.post("/organizations", json={"name": "Nova", "slug": "nova"}, headers=sa_headers).json()["id"]

    invited = client.post(
        "/invitations",
        json={"email": "admin@nova.com", "role": "org_admin"},
        headers={**sa_headers, "X-Org-Context": org_id},
    )
    assert invited.status_code == 201
    token = outbox[-1]["token"]

    accepted = client.post(
        "/invitations/accept",
        json={"token": token, "full_name": "Admin Nova", "password": NEW_PASSWORD},
    )
    assert accepted.status_code == 200

    # O admin inicial agora consegue convidar os demais (sem criação direta de conta).
    admin_login = client.post("/auth/login", json={"email": "admin@nova.com", "password": NEW_PASSWORD})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    second = client.post(
        "/invitations", json={"email": "colab@nova.com", "role": "manager"}, headers=admin_headers
    )
    assert second.status_code == 201
