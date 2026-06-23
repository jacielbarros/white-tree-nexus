"""Encrypted local storage for Gap Analysis evidence files.

The API must never expose ``storage_key`` or filesystem paths. Routers keep this
module as the only place that knows how keys map to disk paths.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from fastapi import UploadFile

from wtnapp import settings


class EvidenceStorageError(ValueError):
    """Raised for user-correctable evidence storage validation failures."""


class EvidenceStorageUnavailable(RuntimeError):
    """Raised when storage/encryption is not correctly configured."""


@dataclass(frozen=True)
class StoredEvidence:
    storage_key: str
    original_filename: str
    content_hash: str
    hash_algorithm: str
    size_bytes: int
    mime_type: str | None
    extension: str
    encrypted: bool = True
    encryption_scheme: str = "fernet"


_FILENAME_RE = re.compile(r"[^A-Za-z0-9._ -]+")


def sanitize_filename(filename: str | None) -> str:
    value = (filename or "evidencia").strip().replace("\\", "/").split("/")[-1]
    value = _FILENAME_RE.sub("_", value).strip(" .")
    return value[:255] or "evidencia"


def build_storage_key(tenant_id: uuid.UUID, evidence_id: uuid.UUID, version_id: uuid.UUID) -> str:
    return f"{tenant_id}/{evidence_id}/{version_id}.fernet"


def _storage_root() -> Path:
    root = Path(settings.EVIDENCE_STORAGE_DIR).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path_for_key(storage_key: str) -> Path:
    if storage_key.startswith(("/", "\\")) or ".." in Path(storage_key).parts:
        raise EvidenceStorageUnavailable("Chave de storage invalida.")
    root = _storage_root()
    path = (root / storage_key).resolve()
    if root not in path.parents and path != root:
        raise EvidenceStorageUnavailable("Chave de storage invalida.")
    return path


def _fernet() -> Fernet:
    key = settings.FIELD_ENCRYPTION_KEY
    if not key:
        raise EvidenceStorageUnavailable("Chave de cifragem nao configurada.")
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except (TypeError, ValueError):
        raise EvidenceStorageUnavailable("Chave de cifragem invalida.")


def _validate_payload(filename: str, content: bytes, content_type: str | None) -> tuple[str, int]:
    extension = Path(filename).suffix.lower()
    size = len(content)
    if size <= 0:
        raise EvidenceStorageError("Arquivo vazio.")
    if size > settings.EVIDENCE_MAX_FILE_BYTES:
        raise EvidenceStorageError("Arquivo excede o tamanho maximo permitido.")
    if not extension or extension not in settings.EVIDENCE_ALLOWED_EXTENSIONS:
        raise EvidenceStorageError("Formato de arquivo nao permitido.")
    allowed_mimes = settings.EVIDENCE_ALLOWED_MIME_TYPES
    if allowed_mimes and content_type and content_type.lower() not in allowed_mimes:
        raise EvidenceStorageError("Tipo de arquivo nao permitido.")
    return extension, size


def store_bytes(
    *,
    content: bytes,
    original_filename: str | None,
    content_type: str | None,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
    version_id: uuid.UUID,
) -> StoredEvidence:
    filename = sanitize_filename(original_filename)
    extension, size = _validate_payload(filename, content, content_type)
    content_hash = hashlib.sha256(content).hexdigest()
    encrypted = _fernet().encrypt(content)
    storage_key = build_storage_key(tenant_id, evidence_id, version_id)
    path = _path_for_key(storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_bytes(encrypted)
    tmp_path.replace(path)
    return StoredEvidence(
        storage_key=storage_key,
        original_filename=filename,
        content_hash=content_hash,
        hash_algorithm="sha256",
        size_bytes=size,
        mime_type=content_type or None,
        extension=extension,
    )


async def store_upload_file(
    *,
    upload: UploadFile,
    tenant_id: uuid.UUID,
    evidence_id: uuid.UUID,
    version_id: uuid.UUID,
) -> StoredEvidence:
    content = await upload.read()
    return store_bytes(
        content=content,
        original_filename=upload.filename,
        content_type=upload.content_type,
        tenant_id=tenant_id,
        evidence_id=evidence_id,
        version_id=version_id,
    )


def read_bytes(storage_key: str) -> bytes:
    path = _path_for_key(storage_key)
    try:
        encrypted = path.read_bytes()
        return _fernet().decrypt(encrypted)
    except FileNotFoundError:
        raise EvidenceStorageUnavailable("Arquivo de evidencia indisponivel.")
    except InvalidToken:
        raise EvidenceStorageUnavailable("Conteudo de evidencia invalido.")
