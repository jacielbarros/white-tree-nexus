"""Testa as credenciais SMTP do .env enviando um e-mail real — SEM o fail-soft da app.

Uso:
    .venv\\Scripts\\python.exe scripts\\test_smtp.py destinatario@exemplo.com

Diferente da aplicação (que engole o erro e retorna 201), este script mostra o
ERRO REAL do servidor: 535 (credenciais), conexão recusada, identidade não
verificada no SES (sandbox), região errada, etc. Ativa o debug do diálogo SMTP.
"""

import smtplib
import sys
from email.message import EmailMessage

from wtnapp import settings


def main() -> int:
    to = sys.argv[1] if len(sys.argv) > 1 else settings.EMAIL_FROM
    host, port = settings.SMTP_HOST, settings.SMTP_PORT
    user, pwd = settings.SMTP_USER, settings.SMTP_PASSWORD

    print(f"SMTP_HOST          = {host!r}")
    print(f"SMTP_PORT          = {port!r}")
    print(f"SMTP_USER          = {user!r}")
    print(f"SMTP_PASSWORD len  = {len(pwd) if pwd else 0} (conteúdo oculto)")
    print(f"EMAIL_FROM         = {settings.EMAIL_FROM!r}")
    print(f"Destinatário teste = {to!r}")
    print("-" * 60)

    if not host:
        print("ERRO: SMTP_HOST está vazio — a aplicação NÃO tentaria enviar (best-effort).")
        return 1

    msg = EmailMessage()
    msg["From"] = settings.EMAIL_FROM
    msg["To"] = to
    msg["Subject"] = "Teste SMTP — White Tree Nexus"
    msg.set_content("Se você recebeu este e-mail, o SMTP está funcionando.")

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.set_debuglevel(1)  # mostra o diálogo SMTP completo (inclui respostas do SES)
        if user:
            server.starttls()
            server.login(user, pwd)
        server.send_message(msg)

    print("-" * 60)
    print("OK: o servidor SMTP ACEITOU a mensagem.")
    print("Se mesmo assim não chegou: verifique SPAM e, no SES sandbox, se o")
    print("DESTINATÁRIO é uma identidade verificada (no sandbox, remetente E")
    print("destinatário precisam estar verificados).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
