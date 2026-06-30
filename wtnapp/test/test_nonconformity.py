"""Feature 015 / US1+US3 — Registrar/tratar NC (CRUD, causa raiz, status) + lista/filtros."""

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.nonconformity_model import NonConformity, NonConformityEvent
from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _nc_body(**over):
    body = {"origin": "incident", "title": "NC de teste", "description": "desvio", "severity": "menor"}
    body.update(over)
    return body


def test_create_nc_with_code_and_root_cause(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-create")
    h = org_headers(seed["admin"].email, seed["org"].id)

    resp = client.post("/nonconformities", headers=h, json=_nc_body(target_type="gap_item", target_id=str(seed["item"].id)))
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "NC-0001" and body["status"] == "open" and body["severity"] == "menor"
    nc_id = body["id"]

    # editar com causa raiz
    upd = client.put(f"/nonconformities/{nc_id}", headers=h, json=_nc_body(root_cause="Falta de controle", root_cause_method="5 Porques"))
    assert upd.status_code == 200
    detail = client.get(f"/nonconformities/{nc_id}", headers=h).json()
    assert detail["root_cause"] == "Falta de controle"
    assert detail["readiness"]["can_close"] is False  # sem verificação/ações

    # 2ª NC → NC-0002
    assert client.post("/nonconformities", headers=h, json=_nc_body()).json()["code"] == "NC-0002"


def test_status_transitions_and_invalid(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-status")
    h = org_headers(seed["admin"].email, seed["org"].id)
    nc_id = client.post("/nonconformities", headers=h, json=_nc_body()).json()["id"]

    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "start"}).json()["status"] == "in_progress"
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "send-verify"}).json()["status"] == "in_verification"
    # transição inválida (start de novo)
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "start"}).status_code == 409
    # encerrar sem verificação → bloqueado (gate)
    assert client.post(f"/nonconformities/{nc_id}/transition", headers=h, json={"action": "close"}).status_code == 409

    # trilha append-only registrada
    types = {e.event_type for e in db.query(NonConformityEvent).filter_by(nonconformity_id=__import__("uuid").UUID(nc_id))}
    assert {"created", "status_changed"} <= types


def test_list_filters_by_status_and_severity(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-filter")
    h = org_headers(seed["admin"].email, seed["org"].id)
    a = client.post("/nonconformities", headers=h, json=_nc_body(severity="maior")).json()["id"]
    client.post("/nonconformities", headers=h, json=_nc_body(severity="menor"))
    client.post(f"/nonconformities/{a}/transition", headers=h, json={"action": "start"})

    assert {n["severity"] for n in client.get("/nonconformities", headers=h, params={"severity": "maior"}).json()} == {"maior"}
    by_status = client.get("/nonconformities", headers=h, params={"status": "in_progress"}).json()
    assert [n["id"] for n in by_status] == [a]
