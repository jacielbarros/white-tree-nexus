"""Feature 013 — consolidação da SoA dirigida pelo Tratamento de Riscos (US1 + US3)."""

from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.risk_model import RiskTreatmentControl
from wtnapp.settings import GapDimension


def _ref(db, catalog_item_id):
    return db.get(GapCatalogItem, catalog_item_id).ref_code


# ── US1 — consolidação dirigida por risco ────────────────────────────────────

def test_risk_consolidation_marks_applicable_with_reason_and_links(
    client, soa_seed, org_headers, link_risk_to_control
):
    s = soa_seed()
    link_risk_to_control(s["org"], s["annex_items"][0].catalog_item_id, code="RSK-0001")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    items = client.get("/soa", headers=headers).json()["items"]

    linked = [i for i in items if i["risk_links"]]
    assert len(linked) == 1
    it = linked[0]
    assert it["applicable"] is True
    assert "risk_treatment" in it["inclusion_reasons"]
    assert it["risk_links"][0]["risk_code"] == "RSK-0001"
    assert it["origin"] in ("risk", "risk+manual")


def test_risk_feed_out_of_scope_control_is_noticed(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    s = soa_seed()
    clause = (
        db.query(GapCatalogItem)
        .filter(GapCatalogItem.tenant_id == s["org"].id, GapCatalogItem.dimension == GapDimension.clause)
        .first()
    )
    link_risk_to_control(s["org"], clause.id, code="RSK-0009")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    body = client.get("/soa", headers=headers).json()

    assert clause.ref_code in body["readiness"]["out_of_scope_risk_notices"]
    # Nenhum item de SoA criado para o controle fora do Anexo A.
    assert all(not i["risk_links"] for i in body["items"])


def test_items_without_risk_default_empty_links(client, soa_seed, org_headers):
    """T018 — itens consolidados sem risco trazem risk_links=[] (default da coluna)."""
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    items = client.get("/soa", headers=headers).json()["items"]
    assert all(i["risk_links"] == [] for i in items)


# ── US3 — aditiva, idempotente, não destrutiva ───────────────────────────────

def test_risk_consolidation_is_idempotent(client, soa_seed, org_headers, link_risk_to_control):
    s = soa_seed()
    link_risk_to_control(s["org"], s["annex_items"][0].catalog_item_id, code="RSK-0001")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    r2 = client.post("/soa/consolidate", headers=headers).json()
    assert r2["summary"]["total"] == 93

    linked = [i for i in client.get("/soa", headers=headers).json()["items"] if i["risk_links"]]
    assert len(linked) == 1
    assert len(linked[0]["risk_links"]) == 1  # não duplica
    assert linked[0]["inclusion_reasons"].count("risk_treatment") == 1


def test_risk_consolidation_preserves_manual_reasons(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = _ref(db, cat_id)
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    target = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    client.put(
        f"/soa/items/{target['id']}", headers=headers,
        json={"applicable": True, "inclusion_reasons": ["legal"]},
    )

    # Liga um risco ao mesmo controle e reconsolida → risco é ADITIVO, manual preservado.
    link_risk_to_control(s["org"], cat_id, code="RSK-0002")
    client.post("/soa/consolidate", headers=headers)

    updated = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    assert "legal" in updated["inclusion_reasons"]
    assert "risk_treatment" in updated["inclusion_reasons"]
    assert updated["risk_links"][0]["risk_code"] == "RSK-0002"
    assert updated["origin"] == "risk+manual"


def test_risk_makes_na_control_applicable(client, soa_seed, org_headers, link_risk_to_control, db):
    s = soa_seed()
    na_cat = s["annex_items"][2].catalog_item_id  # N/A no Gap
    ref = _ref(db, na_cat)
    link_risk_to_control(s["org"], na_cat, code="RSK-0003")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    assert it["applicable"] is True
    assert "risk_treatment" in it["inclusion_reasons"]


def test_risk_step_preserves_gap_implementation_status(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """FR-005 (C2) — o status derivado do Gap não é alterado pelo passo de risco."""
    s = soa_seed()
    meets_cat = s["annex_items"][0].catalog_item_id  # meets → implemented
    ref = _ref(db, meets_cat)
    link_risk_to_control(s["org"], meets_cat, code="RSK-0005")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    it = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    assert it["implementation_status"] == "implemented"


def test_legacy_risks_treated_text_preserved(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = _ref(db, cat_id)
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    target = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    client.put(
        f"/soa/items/{target['id']}", headers=headers,
        json={"inclusion_reasons": ["best_practice"], "risks_treated": "R-legado-01"},
    )

    link_risk_to_control(s["org"], cat_id, code="RSK-0006")
    client.post("/soa/consolidate", headers=headers)

    updated = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    assert updated["risks_treated"] == "R-legado-01"          # legado coexiste
    assert updated["risk_links"][0]["risk_code"] == "RSK-0006"  # estruturado


def test_consolidation_does_not_erase_links_when_feed_empty(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """SEC-006 (T016a) — feed vazio/indisponível NÃO apaga risk_links já consolidados."""
    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    link_risk_to_control(s["org"], cat_id, code="RSK-0007")
    headers = org_headers(s["admin"].email, s["org"].id)

    client.post("/soa/consolidate", headers=headers)
    db.query(RiskTreatmentControl).filter_by(tenant_id=s["org"].id).delete()
    db.commit()
    client.post("/soa/consolidate", headers=headers)

    linked = [i for i in client.get("/soa", headers=headers).json()["items"] if i["risk_links"]]
    assert len(linked) == 1  # preservado (apenas vira divergência)
