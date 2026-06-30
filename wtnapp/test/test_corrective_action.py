"""Feature 015 / US2 — Ações corretivas (responsável+prazo) e sinalização de prazo vencido."""

from datetime import date, timedelta

from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    return seed


def _nc(client, h):
    return client.post("/nonconformities", headers=h, json={"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}).json()["id"]


def test_add_action_validates_member_and_flags_overdue(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "ca-add")
    h = org_headers(seed["admin"].email, seed["org"].id)
    nc_id = _nc(client, h)

    # responsável não-membro → 422
    import uuid
    bad = client.post(f"/nonconformities/{nc_id}/actions", headers=h, json={"description": "a", "responsible_member_id": str(uuid.uuid4())})
    assert bad.status_code == 422

    # ação com prazo no passado → overdue
    past = (date.today() - timedelta(days=2)).isoformat()
    a = client.post(f"/nonconformities/{nc_id}/actions", headers=h, json={"description": "corrigir", "responsible_member_id": str(seed["admin"].id), "due_date": past})
    assert a.status_code == 201, a.text
    assert a.json()["overdue"] is True

    # filtro overdue na lista de NCs retorna esta NC
    overdue_ncs = client.get("/nonconformities", headers=h, params={"overdue": "true"}).json()
    assert nc_id in {n["id"] for n in overdue_ncs}

    # concluir a ação → deixa de ser overdue
    upd = client.put(f"/nonconformities/actions/{a.json()['id']}", headers=h, json={"description": "corrigir", "responsible_member_id": str(seed["admin"].id), "due_date": past, "status": "done"})
    assert upd.json()["overdue"] is False
