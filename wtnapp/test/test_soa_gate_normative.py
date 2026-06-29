"""Feature 013 — gate da esteira: Pré-SoA vs. SoA normativa na aprovação (US5)."""


def _approve(client, headers):
    client.post("/soa/submit-review", headers=headers)
    return client.post("/soa/approve", headers=headers, json={})


def test_readiness_pre_soa_without_approved_plan(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    complete_soa(s["org"].id)

    body = client.get("/soa", headers=headers).json()
    assert body["readiness"]["kind"] == "pre_soa"
    assert body["readiness"]["risk_plan_approved"] is False
    assert any("Plano de Tratamento" in p for p in body["readiness"]["pending_for_normative"])


def test_readiness_normative_with_approved_plan(
    client, soa_seed, org_headers, complete_soa, approve_risk_plan
):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    complete_soa(s["org"].id)
    approve_risk_plan(s["org"])

    body = client.get("/soa", headers=headers).json()
    assert body["readiness"]["kind"] == "normative"
    assert body["readiness"]["risk_plan_approved"] is True


def test_approve_labels_version_pre_soa_without_plan(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    complete_soa(s["org"].id)

    resp = _approve(client, headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "pre_soa"


def test_approve_labels_version_normative_with_plan(
    client, soa_seed, org_headers, complete_soa, approve_risk_plan
):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    complete_soa(s["org"].id)
    approve_risk_plan(s["org"])

    resp = _approve(client, headers)
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "normative"


def test_version_label_is_immutable_after_plan_change(
    client, soa_seed, org_headers, complete_soa, approve_risk_plan, db
):
    """Versão emitida como pre_soa permanece pre_soa mesmo após o plano ser aprovado depois."""
    from wtnapp.models.risk_model import RiskPlan

    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)
    complete_soa(s["org"].id)
    v1 = _approve(client, headers).json()
    assert v1["kind"] == "pre_soa"

    # plano aprovado depois não altera a versão já emitida
    approve_risk_plan(s["org"])
    versions = client.get("/soa/versions", headers=headers).json()
    assert versions[0]["kind"] == "pre_soa"


def test_incomplete_still_blocks_approval(
    client, soa_seed, org_headers, link_risk_to_control, db
):
    """FR-009a — controle aplicável sem razão bloqueia aprovação (422), independe do gate de risco."""
    from wtnapp.models.gap_catalog_model import GapCatalogItem
    from wtnapp.models.risk_model import RiskTreatmentControl

    s = soa_seed()
    cat_id = s["annex_items"][0].catalog_item_id
    ref = db.get(GapCatalogItem, cat_id).ref_code
    link_risk_to_control(s["org"], cat_id, code="RSK-0020")
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    # completa tudo, depois orfaniza+reconcilia para deixar 1 item incompleto
    for it in client.get("/soa", headers=headers).json()["items"]:
        if it["applicable"] and not it["inclusion_reasons"]:
            client.put(f"/soa/items/{it['id']}", headers=headers,
                       json={"inclusion_reasons": ["best_practice"]})
        elif not it["applicable"] and not it["exclusion_justification"]:
            client.put(f"/soa/items/{it['id']}", headers=headers,
                       json={"exclusion_justification": "Fora do escopo."})

    db.query(RiskTreatmentControl).filter_by(tenant_id=s["org"].id).delete()
    db.commit()
    target = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["ref_code"] == ref)
    client.post(f"/soa/items/{target['id']}/reconcile", headers=headers, json={"source": "risk"})

    client.post("/soa/submit-review", headers=headers)
    resp = client.post("/soa/approve", headers=headers, json={})
    assert resp.status_code == 422
