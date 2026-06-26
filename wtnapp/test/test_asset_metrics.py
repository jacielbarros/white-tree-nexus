"""Feature 011 — cards de resumo e dashboard."""

import pytest

from wtnapp.settings import Role


@pytest.fixture
def metrics_org(factory):
    org = factory.org("metrics-acme", "Metrics Acme")
    admin = factory.user("admin@metrics-acme.com")
    factory.membership(admin, org, Role.org_admin)
    return {"org": org, "admin": admin}


def _seed(client, h, admin_id):
    # 1 ativo crítico in_scope completo
    client.post("/assets", headers=h, json={
        "name": "Crit", "item_type": "information_asset", "scope_status": "in_scope",
        "responsible_user_id": admin_id, "confidentiality": "critica", "integrity": "alta",
        "availability": "media", "has_personal_data": True,
    })
    # 1 processo sem responsável e sem CIA
    client.post("/assets", headers=h, json={"name": "Proc", "item_type": "business_process", "scope_status": "under_analysis"})
    # 1 fornecedor
    client.post("/assets", headers=h, json={"name": "Forn", "item_type": "supplier", "scope_status": "out_of_scope",
                                            "scope_justification": "Terceiro fora do escopo"})


def test_summary_counts(client, org_headers, metrics_org):
    h = org_headers(metrics_org["admin"].email, metrics_org["org"].id)
    _seed(client, h, str(metrics_org["admin"].id))
    s = client.get("/assets/summary", headers=h).json()
    assert s["total"] == 3
    assert s["assets"] == 1
    assert s["processes"] == 1
    assert s["suppliers"] == 1
    assert s["in_scope"] == 1
    assert s["critical"] == 1
    assert s["without_responsible"] == 2  # processo + fornecedor
    assert s["cia_incomplete"] == 2


def test_dashboard_distributions(client, org_headers, metrics_org):
    h = org_headers(metrics_org["admin"].email, metrics_org["org"].id)
    _seed(client, h, str(metrics_org["admin"].id))
    d = client.get("/assets/dashboard", headers=h).json()
    assert d["by_type"]["information_asset"] == 1
    assert d["by_type"]["business_process"] == 1
    assert d["by_criticality"]["critica"] == 1
    assert d["by_scope"]["in_scope"] == 1
    assert d["by_scope"]["out_of_scope"] == 1
    assert d["with_personal_data"] == 1
    assert d["without_responsible"] == 2
    assert d["by_review_status"]["undefined"] == 3


def test_archived_excluded_from_metrics(client, org_headers, metrics_org):
    h = org_headers(metrics_org["admin"].email, metrics_org["org"].id)
    created = client.post("/assets", headers=h, json={"name": "Temp", "item_type": "other", "scope_status": "under_analysis"}).json()
    client.post(f"/assets/{created['id']}/archive", headers=h, json={"reason": "fim"})
    s = client.get("/assets/summary", headers=h).json()
    assert s["total"] == 0
