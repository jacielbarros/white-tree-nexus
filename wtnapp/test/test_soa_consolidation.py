"""US1 — consolidação da SoA a partir da avaliação corrente do Gap Analysis."""


def test_consolidate_materializes_annex_a_controls(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)

    resp = client.post("/soa/consolidate", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 93 controles do Anexo A
    assert body["summary"]["total"] == 93
    assert len(body["items"]) == 93


def test_consolidate_maps_status_and_applicability(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    items = client.get("/soa", headers=headers).json()["items"]
    statuses = [i["implementation_status"] for i in items]
    assert statuses.count("implemented") == 1      # meets
    assert statuses.count("in_progress") == 1       # partial
    assert statuses.count("not_applicable") == 1    # N/A

    not_applicable = [i for i in items if not i["applicable"]]
    assert len(not_applicable) == 1
    assert not_applicable[0]["exclusion_justification"]  # herdada do Gap


def test_consolidate_is_idempotent_and_preserves_edits(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    client.post("/soa/consolidate", headers=headers)

    items = client.get("/soa", headers=headers).json()["items"]
    target = next(i for i in items if i["applicable"])
    client.put(
        f"/soa/items/{target['id']}",
        headers=headers,
        json={"applicable": True, "inclusion_reasons": ["legal"], "responsible": "DPO"},
    )

    # 2ª consolidação não duplica nem sobrescreve a edição manual
    resp = client.post("/soa/consolidate", headers=headers)
    assert resp.json()["summary"]["total"] == 93
    edited = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["id"] == target["id"])
    assert edited["inclusion_reasons"] == ["legal"]
    assert edited["responsible"] == "DPO"


def test_consolidate_without_gap_returns_409(client, factory, org_headers, gap_seed):
    from wtnapp.settings import Role

    org = factory.org("no-gap", "No Gap")
    admin = factory.user("admin@no-gap.com", full_name="Admin")
    factory.membership(admin, org, Role.org_admin)
    headers = org_headers(admin.email, org.id)

    resp = client.post("/soa/consolidate", headers=headers)
    assert resp.status_code == 409


def test_get_soa_before_consolidate_returns_404(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    assert client.get("/soa", headers=headers).status_code == 404
