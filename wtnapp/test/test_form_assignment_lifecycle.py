"""T011, T025 — Ciclo de vida de atribuicao: create→claim→save→submit + trail/return/cancel."""

import pytest
from fastapi.testclient import TestClient

from wtnapp.settings import AssignmentStatus, FormKind, TemplateStatus


@pytest.fixture
def seed(form_seed, factory, form_outbox):
    """Template ativo + segunda org para isolamento."""
    return form_seed


def _headers(login, email, org_id):
    h = login(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _make_template(client, headers, kind=FormKind.generic, title="T001"):
    schema = [
        {
            "secao": "Principal",
            "campos": [
                {"chave": "resposta", "label": "Resposta", "tipo": "text", "obrigatorio": True}
            ],
        }
    ]
    r = client.post("/form-templates", json={"kind": kind, "title": title, "schema": schema}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------------------
# US1 — criar → atribuir → assumir → salvar → enviar
# ---------------------------------------------------------------------------

class TestAssignmentLifecycle:
    def test_create_template_and_assign_to_member(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        assert tpl["status"] == TemplateStatus.draft

        # Atribuir ao cliente
        r = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["status"] == AssignmentStatus.pending
        assert data["fields_snapshot"]  # snapshot congelado

    def test_claim_by_respondent(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        h_client = _headers(login, seed["client"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        assignment = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()

        r = client.post(f"/form-assignments/{assignment['id']}/claim", headers=h_client)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == AssignmentStatus.in_progress

    def test_save_answers_partial(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        h_client = _headers(login, seed["client"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        assignment = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()
        client.post(f"/form-assignments/{assignment['id']}/claim", headers=h_client)

        r = client.put(
            f"/form-assignments/{assignment['id']}/answers",
            json={"answers": {"resposta": "parcial"}},
            headers=h_client,
        )
        assert r.status_code == 200, r.text
        assert r.json()["answers"]["resposta"] == "parcial"

    def test_submit_validates_mandatory_fields(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        h_client = _headers(login, seed["client"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        assignment = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()
        client.post(f"/form-assignments/{assignment['id']}/claim", headers=h_client)

        # Tenta enviar sem preencher campo obrigatório
        r = client.post(f"/form-assignments/{assignment['id']}/submit", headers=h_client)
        assert r.status_code == 422, r.text

    def test_submit_succeeds_with_all_required_fields(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        h_client = _headers(login, seed["client"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        assignment = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()
        client.post(f"/form-assignments/{assignment['id']}/claim", headers=h_client)
        client.put(
            f"/form-assignments/{assignment['id']}/answers",
            json={"answers": {"resposta": "completo"}},
            headers=h_client,
        )
        r = client.post(f"/form-assignments/{assignment['id']}/submit", headers=h_client)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == AssignmentStatus.submitted

    def test_respondent_xor_email_validation(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        # Nenhum dos dois → 422
        r = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"]},
            headers=h_admin,
        )
        assert r.status_code == 422, r.text
        # Ambos → 422
        r2 = client.post(
            "/form-assignments",
            json={
                "template_id": tpl["id"],
                "respondent_user_id": str(seed["client"].id),
                "respondent_email": "x@example.com",
            },
            headers=h_admin,
        )
        assert r2.status_code == 422, r2.text


# ---------------------------------------------------------------------------
# T025 — Trail, return, cancel
# ---------------------------------------------------------------------------

class TestTrailReturnCancel:
    def _full_assignment(self, client, login, seed):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        h_client = _headers(login, seed["client"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        a = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()
        client.post(f"/form-assignments/{a['id']}/claim", headers=h_client)
        client.put(
            f"/form-assignments/{a['id']}/answers",
            json={"answers": {"resposta": "ok"}},
            headers=h_client,
        )
        client.post(f"/form-assignments/{a['id']}/submit", headers=h_client)
        return a["id"], h_admin, h_client

    def test_trail_events_present(self, client, login, seed, form_outbox):
        a_id, h_admin, _ = self._full_assignment(client, login, seed)
        r = client.get(f"/form-assignments/{a_id}/events", headers=h_admin)
        assert r.status_code == 200
        events = [e["event"] for e in r.json()]
        assert "assigned" in events
        assert "claimed" in events
        assert "submitted" in events

    def test_return_goes_back_to_in_progress(self, client, login, seed, form_outbox):
        a_id, h_admin, _ = self._full_assignment(client, login, seed)
        r = client.post(
            f"/form-assignments/{a_id}/return",
            json={"reason": "ajustar campo X"},
            headers=h_admin,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == AssignmentStatus.in_progress

    def test_cancel_assignment(self, client, login, seed, form_outbox):
        a_id, h_admin, _ = self._full_assignment(client, login, seed)
        r = client.post(f"/form-assignments/{a_id}/cancel", headers=h_admin)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == AssignmentStatus.cancelled

    def test_cancel_already_cancelled_returns_409(self, client, login, seed, form_outbox):
        a_id, h_admin, _ = self._full_assignment(client, login, seed)
        client.post(f"/form-assignments/{a_id}/cancel", headers=h_admin)
        r = client.post(f"/form-assignments/{a_id}/cancel", headers=h_admin)
        assert r.status_code == 409, r.text

    def test_remind_records_event(self, client, login, seed, form_outbox):
        h_admin = _headers(login, seed["admin"].email, seed["org"].id)
        tpl = _make_template(client, h_admin)
        a = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(seed["client"].id)},
            headers=h_admin,
        ).json()
        r = client.post(f"/form-assignments/{a['id']}/remind", headers=h_admin)
        assert r.status_code == 204
