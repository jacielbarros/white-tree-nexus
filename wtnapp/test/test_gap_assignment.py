"""Testes de atribuição de análise gap — condutor atribuível (T027, US5).

Cobre: criação de atribuição (membro + externo via token), ciclo de vida
(pending→in_progress→submitted), cancelamento, isolamento de tenant, token hash.
"""

import hashlib
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from wtnapp.main import app
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.settings import DocType, Role


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def login(client):
    def _login(email, password="Sup3rSecret!2345"):
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}
    return _login


@pytest.fixture
def gap_assign_org(factory):
    org = factory.org("gap-assign", "GAP Assign Org")
    admin = factory.user("admin@gap-assign.com", full_name="Admin Assign")
    client_user = factory.user("client@gap-assign.com", full_name="Client Assign")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(client_user, org, Role.client)
    return {"org": org, "admin": admin, "client": client_user}


def headers_for(login_fn, email, org_id):
    h = login_fn(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _setup(client, h):
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=h)


def _canonical_hash(payload):
    content = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def test_create_assignment_to_member(client, login, gap_assign_org, gap_seed):
    """Admin atribui condução a um membro interno — sem token externo."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={
            "scope": "whole",
            "respondent_user_id": str(gap_assign_org["client"].id),
        },
        headers=ha,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["status"] == "pending"
    assert data["respondent_user_id"] == str(gap_assign_org["client"].id)
    assert data["token"] is None  # sem token para membro interno


def test_create_assignment_to_external_generates_token(client, login, gap_assign_org, gap_seed):
    """Atribuição externa gera token (plain) retornado apenas uma vez."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_email": "externo@exemplo.com"},
        headers=ha,
    )
    assert r.status_code == 201
    data = r.json()
    assert data["token"] is not None
    assert len(data["token"]) > 20
    assert data["respondent_email"] == "externo@exemplo.com"

    # Token plain não é retornado na listagem
    r2 = client.get("/gap/assignments", headers=ha)
    for a in r2.json():
        assert a.get("token") is None


def test_lifecycle_pending_to_submitted(client, login, gap_assign_org, gap_seed):
    """Fluxo completo: pending → claim (in_progress) → submit (submitted)."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]

    # Claim
    r = client.post(f"/gap/assignments/{aid}/claim", headers=ha)
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    assert r.json()["claimed_at"] is not None

    # Submit
    r = client.post(f"/gap/assignments/{aid}/submit", headers=ha)
    assert r.status_code == 200
    assert r.json()["status"] == "submitted"
    assert r.json()["submitted_at"] is not None


def test_sign_submitted_assignment_freezes_baseline(client, login, gap_assign_org, gap_seed, db):
    """Assinar uma conducao submetida cria baseline imutavel com selo SHA-256."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    hc = headers_for(login, "client@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    assessment = client.get("/gap/assessment", headers=ha).json()
    first_item_id = assessment["items"][0]["id"]
    client.put(f"/gap/assessment/items/{first_item_id}", json={"status": "meets"}, headers=ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]
    client.post(f"/gap/assignments/{aid}/claim", headers=ha)
    client.post(f"/gap/assignments/{aid}/submit", headers=ha)

    r = client.post(f"/gap/assignments/{aid}/sign", headers=hc)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["assignment"]["status"] == "signed"
    assert data["assignment"]["signed_at"] is not None
    assert data["baseline"]["version_number"] == 1
    assert data["content_hash"]
    assert len(data["content_hash"]) == 64

    r = client.get("/gap/assessment/baselines", headers=ha)
    assert r.status_code == 200
    assert any(b["id"] == data["baseline"]["id"] for b in r.json())

    db.expire_all()
    version = db.get(DocumentVersion, uuid.UUID(data["baseline"]["id"]))
    assert version is not None
    assert version.document_type == DocType.gap_baseline
    snapshot = version.content_snapshot
    assert snapshot["signature"]["signer_email"] == "client@gap-assign.com"
    assert snapshot["signature"]["content_hash"] == data["content_hash"]
    assert _canonical_hash(snapshot["signed_content"]) == data["content_hash"]

    r = client.post(f"/gap/assignments/{aid}/sign", headers=hc)
    assert r.status_code == 409


def test_sign_requires_submitted_assignment(client, login, gap_assign_org, gap_seed):
    """Assinar antes do envio da conducao deve retornar 409."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    hc = headers_for(login, "client@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]

    r = client.post(f"/gap/assignments/{aid}/sign", headers=hc)
    assert r.status_code == 409


def test_cancel_assignment(client, login, gap_assign_org, gap_seed):
    """Cancelamento move para status terminal 'cancelled'."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]

    r = client.post(f"/gap/assignments/{aid}/cancel", headers=ha)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"


def test_double_claim_returns_409(client, login, gap_assign_org, gap_seed):
    """Assumir atribuição já em_progress → 409."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]
    client.post(f"/gap/assignments/{aid}/claim", headers=ha)
    r = client.post(f"/gap/assignments/{aid}/claim", headers=ha)
    assert r.status_code == 409


def test_cancel_submitted_returns_409(client, login, gap_assign_org, gap_seed):
    """Cancelar atribuição já submetida → 409."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_user_id": str(gap_assign_org["client"].id)},
        headers=ha,
    )
    aid = r.json()["id"]
    client.post(f"/gap/assignments/{aid}/claim", headers=ha)
    client.post(f"/gap/assignments/{aid}/submit", headers=ha)
    r = client.post(f"/gap/assignments/{aid}/cancel", headers=ha)
    assert r.status_code == 409


def test_assignment_without_respondent_returns_422(client, login, gap_assign_org, gap_seed):
    """Criar atribuição sem respondente → 422."""
    ha = headers_for(login, "admin@gap-assign.com", gap_assign_org["org"].id)
    _setup(client, ha)

    r = client.post("/gap/assignments", json={"scope": "whole"}, headers=ha)
    assert r.status_code == 422


def test_assignment_cross_tenant_returns_404(client, login, factory, gap_seed):
    """Atribuição de Org A não é visível/atualizável pela Org B."""
    org_a = factory.org("assign-a", "Assign A")
    org_b = factory.org("assign-b", "Assign B")
    admin_a = factory.user("admin@assign-a.com", full_name="Admin A")
    admin_b = factory.user("admin@assign-b.com", full_name="Admin B")
    factory.membership(admin_a, org_a, Role.org_admin)
    factory.membership(admin_b, org_b, Role.org_admin)

    ha = headers_for(login, "admin@assign-a.com", org_a.id)
    hb = headers_for(login, "admin@assign-b.com", org_b.id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=hb)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_email": "x@x.com"},
        headers=ha,
    )
    aid = r.json()["id"]

    # Org B não pode assumir atribuição de Org A
    r = client.post(f"/gap/assignments/{aid}/claim", headers=hb)
    assert r.status_code in (403, 404)

    # Org B lista suas atribuições (vazias)
    r = client.get("/gap/assignments", headers=hb)
    assert r.json() == []


def test_assignment_sign_cross_tenant_returns_404(client, login, factory, gap_seed):
    """Assinatura de conducao de outra org nao pode ser inferida."""
    org_a = factory.org("assign-sign-a", "Assign Sign A")
    org_b = factory.org("assign-sign-b", "Assign Sign B")
    admin_a = factory.user("admin@assign-sign-a.com", full_name="Admin A")
    admin_b = factory.user("admin@assign-sign-b.com", full_name="Admin B")
    factory.membership(admin_a, org_a, Role.org_admin)
    factory.membership(admin_b, org_b, Role.org_admin)

    ha = headers_for(login, "admin@assign-sign-a.com", org_a.id)
    hb = headers_for(login, "admin@assign-sign-b.com", org_b.id)

    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=ha)
    client.post("/gap/catalog/adopt", json={"seed_version": "2022.1"}, headers=hb)

    r = client.post(
        "/gap/assignments",
        json={"scope": "whole", "respondent_email": "x@x.com"},
        headers=ha,
    )
    aid = r.json()["id"]

    r = client.post(f"/gap/assignments/{aid}/sign", headers=hb)
    assert r.status_code in (403, 404)
