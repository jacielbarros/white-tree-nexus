"""Notificações por e-mail (convite, redefinição, atribuição de formulário). Best-effort."""

import logging

from wtnapp.utils import email as email_util

logger = logging.getLogger(__name__)


def send_invite_email(
    *, to_email: str, token: str, org_name: str, role: str, existing_user: bool = False
) -> bool:
    """Convite por e-mail. Texto/assunto variam se o convidado já tem conta (existing_user)."""
    accept_link = f"http://localhost:4200/accept?token={token}"
    if existing_user:
        subject = f"Você foi adicionado a {org_name} — White Tree Nexus"
        body = (
            f"Você foi adicionado à organização {org_name} como {role}.\n\n"
            "Como você já tem uma conta, basta acessar o link abaixo para confirmar o acesso — "
            f"sua senha atual continua valendo:\n\n{accept_link}\n"
        )
    else:
        subject = "Convite — White Tree Nexus"
        body = (
            f"Você foi convidado para a organização {org_name} como {role}.\n\n"
            f"Acesse o link abaixo para aceitar o convite e definir sua senha:\n\n{accept_link}\n"
        )
    ok = email_util.send_email(to_email, subject, body)
    # Diagnóstico sem PII: registra o tipo e se o servidor de e-mail ACEITOU a mensagem.
    logger.info(
        "convite: tipo=%s entrega_aceita=%s", "existente" if existing_user else "novo", ok
    )
    return ok


def send_password_reset_email(*, to_email: str, token: str) -> bool:
    body = f"Para redefinir sua senha, use o token a seguir:\n\n{token}\n"
    return email_util.send_email(to_email, "Redefinição de senha — White Tree Nexus", body)


# --- Motor de Workflow de Preenchimento (Feature 003) ---

def send_form_assignment_email(
    *,
    to_email: str,
    assignment_title: str,
    token: str | None = None,
    app_link: str | None = None,
    deadline: str | None = None,
    instructions: str | None = None,
) -> bool:
    """Notificação de atribuição. Para externo: token no link; para membro: link para o app."""
    if token:
        link = f"http://localhost:4200/respond/{token}"
        body = (
            f"Você foi convidado para preencher o formulário: {assignment_title}\n\n"
            f"Acesse pelo link (válido por 7 dias):\n{link}\n"
        )
    else:
        link = app_link or "http://localhost:4200/app/form-assignments"
        body = (
            f"Um formulário foi atribuído a você: {assignment_title}\n\n"
            f"Acesse em:\n{link}\n"
        )
    if deadline:
        body += f"\nPrazo: {deadline}"
    if instructions:
        body += f"\nInstruções: {instructions}"
    return email_util.send_email(to_email, f"Formulário atribuído: {assignment_title}", body)


def send_form_reminder_email(*, to_email: str, assignment_title: str, link: str = "") -> bool:
    body = (
        f"Lembrete: você tem um formulário pendente: {assignment_title}\n\n"
        f"Acesse em:\n{link or 'http://localhost:4200/app/form-assignments'}\n"
    )
    return email_util.send_email(to_email, f"Lembrete: {assignment_title}", body)


def send_signature_otp_email(*, to_email: str, otp_code: str, assignment_title: str) -> bool:
    """OTP de assinatura — gate de segurança (fail-closed). Nunca logar o otp_code."""
    body = (
        f"Código de confirmação para assinar o formulário: {assignment_title}\n\n"
        f"Código: {otp_code}\n\n"
        "Este código expira em 15 minutos e é de uso único.\n"
        "Não compartilhe este código com ninguém."
    )
    return email_util.send_email(to_email, "Código de assinatura — White Tree Nexus", body)
