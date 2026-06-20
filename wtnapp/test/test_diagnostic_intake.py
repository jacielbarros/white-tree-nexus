"""T028 — Integração: formulário de diagnóstico concluído → Diagnostic vigente."""

import uuid

import pytest

from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.services.diagnostic_intake import apply_diagnostic_intake
from wtnapp.settings import DiagnosticStatus


def _headers(login, email, org_id):
    h = login(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _make_and_submit(client, login, form_seed, kind="diagnostic"):
    h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
    h_client = _headers(login, form_seed["client"].email, form_seed["org"].id)
    tpl = client.post(
        "/form-templates",
        json={"kind": kind, "title": "Diag Test", "schema": []},
        headers=h_admin,
    ).json()
    a = client.post(
        "/form-assignments",
        json={"template_id": tpl["id"], "respondent_user_id": str(form_seed["client"].id)},
        headers=h_admin,
    ).json()
    client.post(f"/form-assignments/{a['id']}/claim", headers=h_client)
    client.put(
        f"/form-assignments/{a['id']}/answers",
        json={"answers": {"nome_organizacao": "ACME", "setor": "TI"}},
        headers=h_client,
    )
    client.post(f"/form-assignments/{a['id']}/submit", headers=h_client)
    return a


class TestDiagnosticIntake:
    def test_apply_intake_creates_diagnostic(self, db, form_seed, form_outbox, client, login):
        a = _make_and_submit(client, login, form_seed, kind="diagnostic")

        # Encerra a transacao do teste para enxergar os commits do TestClient
        db.commit()
        assignment = db.query(FormAssignment).filter(
            FormAssignment.id == uuid.UUID(a["id"])
        ).first()
        assert assignment is not None, "Assignment nao encontrada na sessao de teste"

        apply_diagnostic_intake(db, assignment)

        diag = db.query(Diagnostic).filter(Diagnostic.tenant_id == form_seed["org"].id).first()
        assert diag is not None
        assert diag.status == DiagnosticStatus.completed
        assert "form_intake" in diag.sections
        assert diag.sections["form_intake"]["answers"]["nome_organizacao"] == "ACME"

    def test_intake_is_idempotent(self, db, form_seed, form_outbox, client, login):
        """Reaplicar intake com o mesmo assignment sobrescreve form_intake sem duplicar."""
        a = _make_and_submit(client, login, form_seed, kind="diagnostic")

        db.commit()
        assignment = db.query(FormAssignment).filter(
            FormAssignment.id == uuid.UUID(a["id"])
        ).first()

        apply_diagnostic_intake(db, assignment)
        apply_diagnostic_intake(db, assignment)

        count = db.query(Diagnostic).filter(Diagnostic.tenant_id == form_seed["org"].id).count()
        assert count == 1  # nao duplica

    def test_non_diagnostic_kind_is_ignored(self, db, form_seed, form_outbox, client, login):
        """Kind=generic nao cria Diagnostic."""
        a = _make_and_submit(client, login, form_seed, kind="generic")

        db.commit()
        assignment = db.query(FormAssignment).filter(
            FormAssignment.id == uuid.UUID(a["id"])
        ).first()

        apply_diagnostic_intake(db, assignment)

        count = db.query(Diagnostic).filter(Diagnostic.tenant_id == form_seed["org"].id).count()
        assert count == 0
