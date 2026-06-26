"""Feature 011 (US5) — fontes de contexto para 'criar item a partir do contexto'."""

import pytest

from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap
from wtnapp.settings import EngagementStrategy, Level, Role


@pytest.fixture
def ctx_org(factory, db):
    org = factory.org("ctxsrc-acme", "CtxSrc Acme")
    admin = factory.user("admin@ctxsrc-acme.com")
    factory.membership(admin, org, Role.org_admin)
    smap = StakeholderMap(tenant_id=org.id)
    db.add(smap)
    db.commit()
    db.refresh(smap)
    db.add(Stakeholder(
        tenant_id=org.id, map_id=smap.id, name="Fornecedor Cloud", type="external",
        power=Level.alto, interest=Level.alto, strategy=EngagementStrategy.manage_closely,
    ))
    db.commit()
    return {"org": org, "admin": admin}


def test_context_sources_lists_tenant_elements(client, org_headers, ctx_org):
    h = org_headers(ctx_org["admin"].email, ctx_org["org"].id)
    resp = client.get("/assets/context-sources", headers=h)
    assert resp.status_code == 200, resp.text
    sources = resp.json()
    assert any(s["origin_type"] == "stakeholder" and s["label"] == "Fornecedor Cloud" for s in sources)
    # parte externa sugere fornecedor
    stk = next(s for s in sources if s["label"] == "Fornecedor Cloud")
    assert stk["suggested_item_type"] == "supplier"


def test_context_sources_isolated_by_tenant(client, org_headers, ctx_org, factory):
    other = factory.org("ctxsrc-other", "Other")
    admin_other = factory.user("admin@ctxsrc-other.com")
    factory.membership(admin_other, other, Role.org_admin)
    h_other = org_headers(admin_other.email, other.id)
    resp = client.get("/assets/context-sources", headers=h_other)
    assert resp.status_code == 200
    assert resp.json() == []  # nenhum elemento de contexto do outro tenant
