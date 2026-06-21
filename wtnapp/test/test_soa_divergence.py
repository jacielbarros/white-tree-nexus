"""US5 — detecção de divergência (valor vivo do Gap) e reconciliação explícita."""


def _consolidate(client, headers):
    assert client.post("/soa/consolidate", headers=headers).status_code == 200


def _implemented_item(client, headers):
    """Item consolidado como 'implemented' (origem: Gap 'meets')."""
    items = client.get("/soa", headers=headers).json()["items"]
    return next(i for i in items if i["implementation_status"] == "implemented")


def test_manual_edit_creates_divergence(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = _implemented_item(client, headers)
    # mantém aplicável (com razão) mas muda o status → diverge do valor vivo do Gap
    client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={"inclusion_reasons": ["best_practice"], "implementation_status": "planned"},
    )

    refreshed = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["id"] == item["id"])
    fields = {d["field"]: d for d in refreshed["divergence"]}
    assert "implementation_status" in fields
    assert fields["implementation_status"]["soa_value"] == "planned"
    assert fields["implementation_status"]["gap_value"] == "implemented"


def test_divergences_endpoint_lists_divergent(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = _implemented_item(client, headers)
    client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={"inclusion_reasons": ["best_practice"], "implementation_status": "planned"},
    )

    divergences = client.get("/soa/divergences", headers=headers).json()
    assert any(d["id"] == item["id"] for d in divergences)


def test_reconcile_applies_live_gap_value(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = _implemented_item(client, headers)
    client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={"inclusion_reasons": ["best_practice"], "implementation_status": "planned"},
    )

    resp = client.post(
        f"/soa/items/{item['id']}/reconcile", headers=headers,
        json={"fields": ["implementation_status"]},
    )
    assert resp.status_code == 200, resp.text
    reconciled = resp.json()
    assert reconciled["implementation_status"] == "implemented"
    assert not any(d["field"] == "implementation_status" for d in reconciled["divergence"])
