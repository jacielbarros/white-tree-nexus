"""Feature 015 / US7 — Dashboard NC/Melhoria (PDCA): indicadores + card de readiness."""

from datetime import date, timedelta

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _nc_body(**over):
    body = {"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}
    body.update(over)
    return body


def test_nc_dashboard_metrics(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-metrics")
    h = org_headers(seed["admin"].email, seed["org"].id)
    a = client.post("/nonconformities", headers=h, json=_nc_body(severity="maior")).json()["id"]
    client.post("/nonconformities", headers=h, json=_nc_body(severity="menor"))
    client.post(f"/nonconformities/{a}/transition", headers=h, json={"action": "start"})
    # ação vencida
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    client.post(f"/nonconformities/{a}/actions", headers=h, json={
        "description": "corrigir", "responsible_member_id": str(seed["admin"].id),
        "due_date": yesterday, "status": "planned",
    })
    # melhoria
    client.post("/improvements", headers=h, json={"title": "M", "description": "d", "origin": "suggestion"})

    d = client.get("/nonconformities/dashboard", headers=h)
    assert d.status_code == 200, d.text
    body = d.json()
    assert body["nc_by_status"].get("in_progress") == 1
    assert body["nc_by_status"].get("open") == 1
    assert body["nc_by_severity"].get("maior") == 1
    assert body["nc_by_severity"].get("menor") == 1
    assert body["overdue_actions"] == 1
    assert body["improvements_by_status"].get("proposed") == 1


def test_dashboard_card_reflects_pdca_closure(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "nc-card")
    h = org_headers(seed["admin"].email, seed["org"].id)

    # sem NC → card not_started
    cards = {c["id"]: c for c in client.get("/dashboard", headers=h).json()["cards"]}
    assert cards["action_plan"]["status"] == "not_started"

    # com NC aberta → draft (ciclo em andamento)
    client.post("/nonconformities", headers=h, json=_nc_body())
    cards = {c["id"]: c for c in client.get("/dashboard", headers=h).json()["cards"]}
    assert cards["action_plan"]["status"] == "draft"
    assert cards["action_plan"]["placeholder"] is False
