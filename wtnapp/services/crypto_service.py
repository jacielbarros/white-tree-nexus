"""Hashing de senha (Argon2id) e de tokens opacos. Senhas/tokens nunca em texto claro fora daqui."""

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error

_ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Argon2id — não recuperável."""
    return _ph.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        return _ph.verify(password_hash, password)
    except Argon2Error:
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _ph.check_needs_rehash(password_hash)
    except Argon2Error:
        return False


def generate_opaque_token() -> str:
    """Segredo aleatório para convite/redefinição — enviado só por e-mail."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 — só o hash é persistido (R7)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
