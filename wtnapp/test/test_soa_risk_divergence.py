"""Feature 013 — divergência e reconciliação da SoA contra o insumo de risco vivo (US4)."""

from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.risk_model import RiskTreatmentControl


def _ref(db, catalog_item_id):
    return db.get(GapCatalogItem, catalog_item_id).ref_code


def _risk_divs(item):
    return [d for d in item["divergence"] if d["source"] == "risk"]


def test_divergence_when_feed_points_but_soa_not_included(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """(a) risco trata o controle mas a SoA ainda não o inclui por risco."""
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)  # cria itens, ainda sem risco

    # Liga o risco DEPOIS da consolidação → vira divergência (não auto-aplica em item existente).
    cat_id = s["annex_items"][2].catalog_item_id  # N/A → não incluído
    ref = _ref(db, cat_id)
    link_risk_to_control(s["org"], cat_id, code="RSK-0010")

    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    rd = _risk_divs(it)
    assert rd and rd[0]["field"] == "risk_inclusion"
    assert "RSK-0010" in rd[0]["source_value"]


def test_divergence_when_included_by_risk_but_feed_orphan(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """(b) item incluído por risco mas o feed não aponta mais o controle (órfão)."""
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = _ref(db, cat_id)
    link_risk_to_control(s["org"], cat_id, code="RSK-0011")
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    # Esvazia o feed → item ainda tem risk_treatment → divergência "risco órfão".
    db.query(RiskTreatmentControl).filter_by(tenant_id=s["org"].id).delete()
    db.commit()

    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    rd = _risk_divs(it)
    assert rd and rd[0]["field"] == "risk_inclusion"


def test_reconcile_risk_includes_control(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    cat_id = s["annex_items"][2].catalog_item_id
    ref = _ref(db, cat_id)
    link_risk_to_control(s["org"], cat_id, code="RSK-0012")

    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    resp = client.post(f"/soa/items/{it['id']}/reconcile", headers=headers, json={"source": "risk"})
    assert resp.status_code == 200
    reconciled = resp.json()
    assert reconciled["applicable"] is True
    assert "risk_treatment" in reconciled["inclusion_reasons"]
    assert reconciled["risk_links"][0]["risk_code"] == "RSK-0012"
    assert _risk_divs(reconciled) == []


def test_reconcile_risk_removes_orphan_and_preserves_manual(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = _ref(db, cat_id)
    link_risk_to_control(s["org"], cat_id, code="RSK-0013")
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    # adiciona razão manual e depois orfaniza o risco
    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    client.put(
        f"/soa/items/{it['id']}", headers=headers,
        json={"inclusion_reasons": ["risk_treatment", "legal"]},
    )
    db.query(RiskTreatmentControl).filter_by(tenant_id=s["org"].id).delete()
    db.commit()

    resp = client.post(f"/soa/items/{it['id']}/reconcile", headers=headers, json={"source": "risk"})
    reconciled = resp.json()
    assert "risk_treatment" not in reconciled["inclusion_reasons"]
    assert "legal" in reconciled["inclusion_reasons"]      # manual preservada
    assert reconciled["risk_links"] == []
    assert reconciled["incomplete"] is False               # ainda tem 'legal'


def test_reconcile_removing_last_reason_leaves_incomplete(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """Remover a ÚNICA razão (risk_treatment) ⇒ item aplicável-incompleto (sem auto-flip)."""
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = _ref(db, cat_id)
    link_risk_to_control(s["org"], cat_id, code="RSK-0014")
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    db.query(RiskTreatmentControl).filter_by(tenant_id=s["org"].id).delete()
    db.commit()

    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    resp = client.post(f"/soa/items/{it['id']}/reconcile", headers=headers, json={"source": "risk"})
    reconciled = resp.json()
    assert reconciled["applicable"] is True                # permanece aplicável (sem auto-flip)
    assert reconciled["inclusion_reasons"] == []
    assert reconciled["incomplete"] is True                # bloqueia aprovação (FR-009a)
