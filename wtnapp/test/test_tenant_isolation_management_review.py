"""Feature 015 — Isolamento de tenant da Análise Crítica (obrigatório)."""

from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    return seed


def _full():
    return {"title": "Reunião", "review_date": "2026-06-30", "inputs": {"a": "x"}, "outputs": {"b": "y"}}


def test_org_b_cannot_access_org_a_review(client, db, gap_seed, gap_seed_factory, org_headers):
    a = _seed(db, gap_seed_factory, "mr-iso-a")
    b = _seed(db, gap_seed_factory, "mr-iso-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)
    rid = client.post("/management-reviews", headers=ha, json=_full()).json()["id"]

    assert rid not in {r["id"] for r in client.get("/management-reviews", headers=hb).json()}
    assert client.get(f"/management-reviews/{rid}", headers=hb).status_code == 404
    assert client.put(f"/management-reviews/{rid}", headers=hb, json=_full()).status_code == 404
    assert client.post(f"/management-reviews/{rid}/submit-review", headers=hb).status_code == 404
    assert client.get(f"/management-reviews/{rid}/versions", headers=hb).status_code == 404
