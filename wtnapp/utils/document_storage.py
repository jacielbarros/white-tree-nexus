"""Encrypted local storage for preliminary and signed PDF documents."""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from wtnapp import settings


class DocumentStorageError(ValueError):
    """Raised for user-correctable document storage validation failures."""


class DocumentStorageUnavailable(RuntimeError):
    """Raised when storage/encryption is not correctly configured."""


@dataclass(frozen=True)
class StoredDocument:
    storage_key: str
    content_hash: str
    hash_algorithm: str
    size_bytes: int
    encrypted: bool = True
    encryption_scheme: str = "fernet"


def build_storage_key(tenant_id: uuid.UUID, kind: str, document_id: uuid.UUID) -> str:
    return f"{tenant_id}/{kind}/{document_id}.pdf.fernet"


def _storage_root() -> Path:
    root = Path(settings.DOCUMENT_STORAGE_DIR).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for_key(storage_key: str) -> Path:
    if storage_key.startswith(("/", "\\")) or ".." in Path(storage_key).parts:
        raise DocumentStorageUnavailable("Chave de storage invalida.")
    root = _storage_root()
    path = (root / storage_key).resolve()
    if root not in path.parents and path != root:
        raise DocumentStorageUnavailable("Chave de storage invalida.")
    return path


def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise DocumentStorageUnavailable("Chave de cifragem nao configurada.")
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except (TypeError, ValueError):
        raise DocumentStorageUnavailable("Chave de cifragem invalida.")


def validate_pdf_bytes(content: bytes) -> None:
    size = len(content)
    if size <= 0:
        raise DocumentStorageError("PDF vazio.")
    if size > settings.DOCUMENT_MAX_PDF_BYTES:
        raise DocumentStorageError("PDF excede o tamanho maximo permitido.")
    if not content.startswith(b"%PDF"):
        raise DocumentStorageError("Conteudo gerado nao e um PDF valido.")


def store_pdf(
    *,
    content: bytes,
    tenant_id: uuid.UUID,
    kind: str,
    document_id: uuid.UUID,
) -> StoredDocument:
    validate_pdf_bytes(content)
    content_hash = hashlib.sha256(content).hexdigest()
    encrypted = _fernet().encrypt(content)
    storage_key = build_storage_key(tenant_id, kind, document_id)
    path = _path_for_key(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(encrypted)
    tmp_path.replace(path)
    return StoredDocument(
        storage_key=storage_key,
        content_hash=content_hash,
        hash_algorithm="sha256",
        size_bytes=len(content),
    )


def read_pdf(storage_key: str) -> bytes:
    path = _path_for_key(storage_key)
    try:
        encrypted = path.read_bytes()
        content = _fernet().decrypt(encrypted)
    except FileNotFoundError:
        raise DocumentStorageUnavailable("Documento indisponivel.")
    except InvalidToken:
        raise DocumentStorageUnavailable("Conteudo de documento invalido.")
    validate_pdf_bytes(content)
    return content


def delete_storage_key(storage_key: str) -> None:
    path = _path_for_key(storage_key)
    try:
        path.unlink()
    except FileNotFoundError:
        return


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
