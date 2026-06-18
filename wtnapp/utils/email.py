"""Envio de e-mail por SMTP — best-effort (fail-soft). Nunca derruba a operação (FR-035)."""

import logging
import smtplib
from email.message import EmailMessage

from wtnapp import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> bool:
    if not settings.SMTP_HOST:
        logger.info("SMTP não configurado; e-mail para %s não enviado (dev)", to_email)
        return False
    try:
        msg = EmailMessage()
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(body)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USER:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception:
        logger.warning("falha ao enviar e-mail (fail-soft)", exc_info=True)
        return False
