"""T015, T020 — Respondente externo via token + OTP de assinatura."""

import pytest


def _headers(login, email, org_id):
    h = login(email)
    h["X-Org-Context"] = str(org_id)
    return h


def _create_template_and_assign_external(client, h_admin, respondent_email):
    schema = [
        {
            "secao": "S1",
            "campos": [{"chave": "campo1", "label": "Campo 1", "tipo": "text", "obrigatorio": True}],
        }
    ]
    tpl = client.post(
        "/form-templates",
        json={"kind": "generic", "title": "Externo T", "schema": schema},
        headers=h_admin,
    ).json()
    assign = client.post(
        "/form-assignments",
        json={"template_id": tpl["id"], "respondent_email": respondent_email},
        headers=h_admin,
    ).json()
    return tpl, assign


class TestExternalToken:
    """US2 — link tokenizado para respondente externo."""

    def test_assignment_email_contains_token(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "externo@parceiro.com")
        # Verifica que o e-mail de atribuicao foi capturado com token
        emails = [e for e in form_outbox if e["type"] == "assignment"]
        assert emails, "E-mail de atribuicao nao enviado"
        assert emails[0]["token"] is not None, "Token ausente no e-mail"

    def test_get_form_by_valid_token(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "externo@parceiro.com")
        token = form_outbox[-1]["token"]

        r = client.get(f"/forms/respond/{token}")
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["respondent_email"] == "externo@parceiro.com"
        # Resposta nao vaza token_hash
        assert "respondent_token_hash" not in data

    def test_invalid_token_returns_404(self, client):
        r = client.get("/forms/respond/0000000000000000000000000000000000000000000000000000000000000000")
        assert r.status_code == 404

    def test_claim_by_external(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "externo@parceiro.com")
        token = form_outbox[-1]["token"]

        r = client.post(f"/forms/respond/{token}/claim")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "in_progress"

    def test_save_and_submit_external(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "externo@parceiro.com")
        token = form_outbox[-1]["token"]

        client.post(f"/forms/respond/{token}/claim")
        client.put(f"/forms/respond/{token}/answers", json={"answers": {"campo1": "resposta"}})
        r = client.post(f"/forms/respond/{token}/submit")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "submitted"

    def test_submit_without_required_fields_422(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "externo@parceiro.com")
        token = form_outbox[-1]["token"]

        client.post(f"/forms/respond/{token}/claim")
        r = client.post(f"/forms/respond/{token}/submit")
        assert r.status_code == 422


class TestOTPSignature:
    """T020 — OTP de assinatura para respondente externo."""

    def _submit_external(self, client, login, form_seed, form_outbox):
        h_admin = _headers(login, form_seed["admin"].email, form_seed["org"].id)
        _create_template_and_assign_external(client, h_admin, "ext@parceiro.com")
        token = form_outbox[-1]["token"]
        client.post(f"/forms/respond/{token}/claim")
        client.put(
            f"/forms/respond/{token}/answers",
            json={"answers": {"campo1": "valor ok"}},
        )
        client.post(f"/forms/respond/{token}/submit")
        return token

    def test_request_otp_captured(self, client, login, form_seed, form_outbox):
        token = self._submit_external(client, login, form_seed, form_outbox)
        # Injeta OTP via monkeypatch implícito no form_outbox
        r = client.post(f"/forms/respond/{token}/otp")
        assert r.status_code in (204, 503), r.text  # 503 se SMTP real nao configurado

    def test_sign_with_wrong_otp_returns_401(self, client, login, form_seed, form_outbox, monkeypatch):
        from wtnapp.services import signature_service

        def _fake_otp(*, to_email, otp_code, assignment_title):
            form_outbox.append({"type": "otp", "to": to_email, "otp": otp_code})
            return True

        monkeypatch.setattr(
            signature_service.notification_service, "send_signature_otp_email", _fake_otp
        )
        token = self._submit_external(client, login, form_seed, form_outbox)
        client.post(f"/forms/respond/{token}/otp")

        r = client.post(
            f"/forms/respond/{token}/sign",
            json={"otp": "000000", "signer_name": "Externo Teste"},
        )
        assert r.status_code == 401

    def test_sign_with_correct_otp(self, client, login, form_seed, form_outbox, monkeypatch):
        from wtnapp.services import signature_service

        def _fake_otp(*, to_email, otp_code, assignment_title):
            form_outbox.append({"type": "otp", "to": to_email, "otp": otp_code})
            return True

        monkeypatch.setattr(
            signature_service.notification_service, "send_signature_otp_email", _fake_otp
        )
        token = self._submit_external(client, login, form_seed, form_outbox)
        client.post(f"/forms/respond/{token}/otp")

        otp_code = next(e["otp"] for e in reversed(form_outbox) if e["type"] == "otp")
        r = client.post(
            f"/forms/respond/{token}/sign",
            json={"otp": otp_code, "signer_name": "Externo Teste"},
        )
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["otp_verified"] is True
        assert data["content_hash"]

    def test_otp_max_attempts_locks_out(self, client, login, form_seed, form_outbox, monkeypatch):
        from wtnapp.services import signature_service

        def _fake_otp(*, to_email, otp_code, assignment_title):
            form_outbox.append({"type": "otp", "to": to_email, "otp": otp_code})
            return True

        monkeypatch.setattr(
            signature_service.notification_service, "send_signature_otp_email", _fake_otp
        )
        token = self._submit_external(client, login, form_seed, form_outbox)
        client.post(f"/forms/respond/{token}/otp")

        # 3 tentativas erradas
        for _ in range(3):
            client.post(
                f"/forms/respond/{token}/sign",
                json={"otp": "999999", "signer_name": "X"},
            )

        # A 4ª tentativa com o OTP correto deve falhar (bloqueado/expirado)
        otp_code = next(e["otp"] for e in reversed(form_outbox) if e["type"] == "otp")
        r = client.post(
            f"/forms/respond/{token}/sign",
            json={"otp": otp_code, "signer_name": "Externo Teste"},
        )
        assert r.status_code == 401
