"""US1/US2 — leitura da SoA e edição de controle com validações."""


def _consolidate(client, headers):
    assert client.post("/soa/consolidate", headers=headers).status_code == 200


def test_get_soa_returns_items_and_summary(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    body = client.get("/soa", headers=headers).json()
    assert body["summary"]["total"] == 93
    assert body["summary"]["applicable"] == 92
    assert body["summary"]["not_applicable"] == 1


def test_applicable_without_inclusion_reason_returns_422(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["applicable"])
    # aplicável (mantido) e sem razões → 422
    resp = client.put(f"/soa/items/{item['id']}", headers=headers, json={"responsible": "TI"})
    assert resp.status_code == 422


def test_not_applicable_without_justification_returns_422(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["applicable"])
    resp = client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={"applicable": False, "exclusion_justification": ""},
    )
    assert resp.status_code == 422


def test_valid_edit_persists(client, soa_seed, org_headers):
    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["applicable"])
    resp = client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={
            "applicable": True,
            "inclusion_reasons": ["risk_treatment", "legal"],
            "responsible": "CISO",
            "risks_treated": "R01, R02",
            "evidence_refs": "POL-SI-001",
        },
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["inclusion_reasons"] == ["risk_treatment", "legal"]
    assert updated["responsible"] == "CISO"
    assert updated["evidence_refs"] == "POL-SI-001"


def test_edit_records_event(client, soa_seed, org_headers, db):
    import uuid

    from wtnapp.models.soa_model import SoaItemEvent

    s = soa_seed()
    headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, headers)

    item = next(i for i in client.get("/soa", headers=headers).json()["items"] if i["applicable"])
    client.put(
        f"/soa/items/{item['id']}", headers=headers,
        json={"applicable": False, "exclusion_justification": "Fora do escopo."},
    )
    db.rollback()
    events = db.query(SoaItemEvent).filter_by(item_id=uuid.UUID(item["id"])).all()
    assert any(e.field == "applicable" for e in events)


def test_view_requires_permission(client, soa_seed, org_headers):
    """Cliente tem view_soa; guest_collaborator não — aqui validamos que view funciona p/ cliente."""
    s = soa_seed()
    admin_headers = org_headers(s["admin"].email, s["org"].id)
    _consolidate(client, admin_headers)

    client_headers = org_headers(s["client"].email, s["org"].id)
    assert client.get("/soa", headers=client_headers).status_code == 200
