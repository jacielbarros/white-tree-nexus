"""T019 — Assinatura eletronica avancada de membro autenticado + verificacao de integridade."""

import pytest


def _headers(login, email, org_id):
    h = login(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _full_submitted(client, login, form_seed, form_outbox):
    """Helper: cria template → atribui ao client → claim → salva → envia. Retorna (a_id, h_admin, h_client)."""
    h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
    h_client = _headers(login, form_seed["client"].email, form_seed["org"].id)
    schema = [
        {"secao": "S", "campos": [{"chave": "k", "label": "K", "tipo": "text", "obrigatorio": False}]}
    ]
    tpl = client.post(
        "/form-templates",
        json={"kind": "generic", "title": "Sign T", "schema": schema},
        headers=h_admin,
    ).json()
    a = client.post(
        "/form-assignments",
        json={"template_id": tpl["id"], "respondent_user_id": str(form_seed["client"].id)},
        headers=h_admin,
    ).json()
    client.post(f"/form-assignments/{a['id']}/claim", headers=h_client)
    client.put(f"/form-assignments/{a['id']}/answers", json={"answers": {"k": "v"}}, headers=h_client)
    client.post(f"/form-assignments/{a['id']}/submit", headers=h_client)
    return a["id"], h_admin, h_client


class TestMemberSignature:
    def test_sign_generates_content_hash(self, client, login, form_seed, form_outbox):
        a_id, _, h_client = _full_submitted(client, login, form_seed, form_outbox)
        r = client.post(f"/form-assignments/{a_id}/sign", headers=h_client)
        assert r.status_code == 200, r.text
        data = r.json()
        assert len(data["content_hash"]) == 64  # SHA-256 hex
        assert data["otp_verified"] is False
        assert data["level"] == "advanced"

    def test_integrity_verify_valid(self, client, login, form_seed, form_outbox):
        a_id, h_admin, h_client = _full_submitted(client, login, form_seed, form_outbox)
        client.post(f"/form-assignments/{a_id}/sign", headers=h_client)

        r = client.get(f"/form-assignments/{a_id}/verify", headers=h_admin)
        assert r.status_code == 200, r.text
        assert r.json()["valid"] is True

    def test_sign_wrong_user_returns_403(self, client, login, form_seed, form_outbox):
        """Apenas o respondente designado pode assinar como filler."""
        a_id, h_admin, _ = _full_submitted(client, login, form_seed, form_outbox)
        # Admin nao e o respondente designado → 403
        r = client.post(f"/form-assignments/{a_id}/sign", headers=h_admin)
        assert r.status_code == 403, r.text

    def test_cannot_sign_if_not_submitted(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        h_client = _headers(login, form_seed["client"].email, form_seed["org"].id)
        schema = [{"secao": "S", "campos": []}]
        tpl = client.post(
            "/form-templates",
            json={"kind": "generic", "title": "T", "schema": schema},
            headers=h_admin,
        ).json()
        a = client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_user_id": str(form_seed["client"].id)},
            headers=h_admin,
        ).json()
        # Status e pending, ainda nao foi claimado
        r = client.post(f"/form-assignments/{a['id']}/sign", headers=h_client)
        assert r.status_code in (403, 409), r.text

    def test_signatures_trail_listed(self, client, login, form_seed, form_outbox):
        a_id, h_admin, h_client = _full_submitted(client, login, form_seed, form_outbox)
        client.post(f"/form-assignments/{a_id}/sign", headers=h_client)

        r = client.get(f"/form-assignments/{a_id}/signatures", headers=h_admin)
        assert r.status_code == 200
        sigs = r.json()
        assert len(sigs) >= 1
        assert sigs[0]["signer_role"] == "filler"

    def test_single_signature_policy_completes_assignment(self, client, login, form_seed, form_outbox):
        """Politica padrao (sem contra-assinatura) → assinatura do filler ja conclui."""
        a_id, h_admin, h_client = _full_submitted(client, login, form_seed, form_outbox)
        client.post(f"/form-assignments/{a_id}/sign", headers=h_client)

        r = client.get(f"/form-assignments/{a_id}", headers=h_admin)
        assert r.status_code == 200
        assert r.json()["status"] == "completed"
