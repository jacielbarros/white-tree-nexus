#!/usr/bin/env python
r"""Seed interativo do 1º Super Admin da plataforma (White Tree Nexus).

Cria um usuário com `is_platform_super_admin=True` direto no banco configurado em `.env`
(mesma regra do `POST /bootstrap/super-admin`: só roda se ainda não existir Super Admin).

Uso (a partir da raiz do projeto):

    .\.venv\Scripts\python.exe scripts\seed_super_admin.py

Observação: a plataforma identifica usuários pelo **e-mail** (não há "username" separado);
o nome informado é o nome de exibição (`full_name`).
"""
from __future__ import annotations

import getpass
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")  # popula DATABASE_URL antes de importar wtnapp

from wtnapp import settings  # noqa: E402
from wtnapp.database.database import SessionLocal  # noqa: E402
from wtnapp.models.user_model import User  # noqa: E402
from wtnapp.services import crypto_service  # noqa: E402
from wtnapp.settings import UserStatus  # noqa: E402


def _prompt(label: str) -> str:
    return input(label).strip()


def main() -> int:
    print("== Seed do Super Admin da plataforma ==")
    print(f"Banco: {settings.DATABASE_URL.split('@')[-1]}\n")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.is_platform_super_admin.is_(True)).first()
        if existing is not None:
            print(f"Já existe um Super Admin ({existing.email}). Nada a fazer.")
            return 1

        email = _prompt("E-mail (login): ").lower()
        if "@" not in email or "." not in email:
            print("E-mail inválido.")
            return 2
        if db.query(User).filter(User.email == email).first() is not None:
            print("Já existe um usuário com esse e-mail.")
            return 3

        full_name = _prompt("Nome completo: ")
        if not full_name:
            print("Nome completo é obrigatório.")
            return 4

        pwd = getpass.getpass(f"Senha (mín. {settings.PASSWORD_MIN_LENGTH} caracteres): ")
        if len(pwd) < settings.PASSWORD_MIN_LENGTH:
            print(f"Senha deve ter ao menos {settings.PASSWORD_MIN_LENGTH} caracteres.")
            return 5
        if pwd != getpass.getpass("Confirme a senha: "):
            print("As senhas não conferem.")
            return 6

        user = User(
            email=email,
            full_name=full_name,
            password_hash=crypto_service.hash_password(pwd),
            status=UserStatus.active,
            is_platform_super_admin=True,
            password_changed_at=datetime.now(timezone.utc),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"\nSuper Admin criado: {user.email} (id={user.id}).")
        print("Faça login em http://localhost:4200")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
