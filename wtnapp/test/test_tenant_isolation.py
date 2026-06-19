"""US1 — teste OBRIGATÓRIO de isolamento de tenant (Princípio VI da constitution).

Cobre: contexto de organização cross-tenant negado (404 genérico + audit), `scoped_query`
filtrando por tenant, e o Super Admin precisando de contexto explícito.
Estendido em US2 (FR-005) e US3 (Consultor multi-org / FR-020).
"""

from wtnapp.helpers.tenant_scope import OrgContext, Principal, scoped_query
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.membership_model import Membership
from wtnapp.settings import Role


def test_cross_tenant_context_denied_and_audited(client, factory, db):
    org_a = factory.org(slug="org-a")
    org_b = factory.org(slug="org-b")
    user_a = factory.user(email="ana@org-a.com")
    factory.membership(user_a, org_a, role=Role.org_admin)
    # user_a NÃO é membro de org_b.

    login = client.post("/auth/login", json={"email": "ana@org-a.com", "password": _pwd()})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Contexto da própria org → OK
    own = client.get("/me/context", headers={**headers, "X-Org-Context": str(org_a.id)})
    assert own.status_code == 200
    assert own.json()["tenant_id"] == str(org_a.id)

    # Contexto de org alheia → 404 genérico (não revela existência)
    foreign = client.get("/me/context", headers={**headers, "X-Org-Context": str(org_b.id)})
    assert foreign.status_code == 404

    denied = db.query(AuditLog).filter(AuditLog.operation == "CROSS_TENANT_DENIED").all()
    assert len(denied) == 1
    assert denied[0].actor_user_id == user_a.id


def test_scoped_query_filters_by_tenant(client, factory, db):
    org_a = factory.org(slug="org-a")
    org_b = factory.org(slug="org-b")
    user_a = factory.user(email="ana@org-a.com")
    user_b = factory.user(email="bob@org-b.com")
    m_a = factory.membership(user_a, org_a, role=Role.org_admin)
    factory.membership(user_b, org_b, role=Role.org_admin)

    principal = Principal(user=user_a, jti="x", exp_ts=0, tenant_ids=[org_a.id], is_super_admin=False)
    ctx = OrgContext(
        principal=principal, tenant_id=org_a.id, role=Role.org_admin, is_super_admin=False, membership=m_a
    )
    rows = scoped_query(db, Membership, ctx).all()
    assert {r.tenant_id for r in rows} == {org_a.id}
    assert all(r.tenant_id != org_b.id for r in rows)


def test_super_admin_requires_explicit_context(client, factory):
    factory.user(email="root@plat.com", super_admin=True)
    login = client.post("/auth/login", json={"email": "root@plat.com", "password": _pwd()})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    # Sem X-Org-Context ⇒ 400 (contexto obrigatório p/ Super Admin)
    assert client.get("/me/context", headers=headers).status_code == 400


def test_consultant_operates_in_linked_orgs_only(client, factory):
    """SC-008 / Tenant Isolation #2 — Consultor em A e B; nunca em C."""
    org_a = factory.org(slug="org-a")
    org_b = factory.org(slug="org-b")
    org_c = factory.org(slug="org-c")
    consultant = factory.user(email="con@consult.com")
    factory.membership(consultant, org_a, role=Role.consultant)
    factory.membership(consultant, org_b, role=Role.consultant)

    login = client.post("/auth/login", json={"email": "con@consult.com", "password": _pwd()})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    ctx_a = client.get("/me/context", headers={**headers, "X-Org-Context": str(org_a.id)})
    assert ctx_a.status_code == 200 and ctx_a.json()["role"] == "consultant"
    ctx_b = client.get("/me/context", headers={**headers, "X-Org-Context": str(org_b.id)})
    assert ctx_b.status_code == 200 and ctx_b.json()["tenant_id"] == str(org_b.id)
    # Org não vinculada ⇒ 404
    assert client.get("/me/context", headers={**headers, "X-Org-Context": str(org_c.id)}).status_code == 404


def test_fr020_non_consultant_cannot_have_second_membership(client, factory, outbox):
    """FR-020 — usuário com vínculo não-Consultor não pode aceitar 2º vínculo."""
    org_a = factory.org(slug="org-a")
    org_b = factory.org(slug="org-b")
    admin_b = factory.user(email="admin@org-b.com")
    factory.membership(admin_b, org_b, role=Role.org_admin)

    # bob já é org_admin em A
    bob = factory.user(email="bob@org-a.com")
    factory.membership(bob, org_a, role=Role.org_admin)

    # admin de B convida bob como manager em B
    headers_b = {"Authorization": f"Bearer {client.post('/auth/login', json={'email': 'admin@org-b.com', 'password': _pwd()}).json()['access_token']}"}
    created = client.post("/invitations", json={"email": "bob@org-a.com", "role": "manager"}, headers=headers_b)
    assert created.status_code == 201
    token = outbox[-1]["token"]

    # aceite viola FR-020 (não-Consultor = 1 vínculo) ⇒ 409
    accepted = client.post(
        "/invitations/accept", json={"token": token, "full_name": "Bob", "password": "N0vaSenhaForte!99"}
    )
    assert accepted.status_code == 409


def _pwd() -> str:
    from wtnapp.test.conftest import DEFAULT_PASSWORD

    return DEFAULT_PASSWORD
