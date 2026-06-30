"""Feature 015 / US2 — Gate de encerramento da NC (FR-007): verificação eficaz + zero ações abertas."""

from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    return seed


def _nc(client, h):
    return client.post("/nonconformities", headers=h, json={"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}).json()["id"]


def test_close_gate_requires_effective_verification_and_no_open_actions(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-gate")
    h = org_headers(seed["admin"].email, seed["org"].id)
    nc_id = _nc(client, h)

    # ação aberta + sem verificação
    action = client.post(f"/nonconformities/{nc_id}/actions", headers=h, json={"description": "corrigir", "responsible_member_id": str(seed["admin"].id)}).json()["id"]
    client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "start"})
    client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "send-verify"})

    # sem verificação → 409
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "close"}).status_code == 409

    # verificação INEFICAZ → ainda bloqueado
    client.post(f"/nonconformities/{nc_id}/verifications", headers=h, json={"result": "ineffective"})
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "close"}).status_code == 409

    # verificação EFICAZ mas ação ainda aberta → bloqueado
    client.post(f"/nonconformities/{nc_id}/verifications", headers=h, json={"result": "effective"})
    detail = client.get(f"/nonconformities/{nc_id}", headers=h).json()
    assert detail["readiness"]["has_effective_verification"] is True
    assert detail["readiness"]["open_actions"] == 1
    assert detail["readiness"]["can_close"] is False
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "close"}).status_code == 409

    # conclui a ação → gate libera, encerra
    client.put(f"/nonconformities/actions/{action}", headers=h, json={"description": "corrigir", "responsible_member_id": str(seed["admin"].id), "status": "done"})
    assert client.get(f"/nonconformities/{nc_id}", headers=h).json()["readiness"]["can_close"] is True
    closed = client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "close"})
    assert closed.status_code == 200 and closed.json()["status"] == "closed"
