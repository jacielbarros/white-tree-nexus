"""Notificações por e-mail (convite, redefinição). Best-effort — o artefato é a fonte de verdade."""

from wtnapp.utils import email as email_util


def send_invite_email(*, to_email: str, token: str, org_name: str, role: str) -> bool:
    body = (
        f"Você foi convidado para a organização {org_name} como {role}.\n"
        f"Use o token a seguir para aceitar o convite e definir sua senha:\n\n{token}\n"
    )
    return email_util.send_email(to_email, "Convite — White Tree Nexus", body)


def send_password_reset_email(*, to_email: str, token: str) -> bool:
    body = f"Para redefinir sua senha, use o token a seguir:\n\n{token}\n"
    return email_util.send_email(to_email, "Redefinição de senha — White Tree Nexus", body)
