import uuid

import pytest
from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.utils import evidence_storage
from wtnapp.utils.evidence_storage import EvidenceStorageError, EvidenceStorageUnavailable


def _configure_storage(monkeypatch, tmp_path, *, max_bytes=64):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", max_bytes)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf", ".png", ".txt", ".zip"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def test_store_bytes_hashes_and_encrypts_file(monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    content = b"security evidence"

    stored = evidence_storage.store_bytes(
        content=content,
        original_filename="../policy.pdf",
        content_type="application/pdf",
        tenant_id=uuid.uuid4(),
        evidence_id=uuid.uuid4(),
        version_id=uuid.uuid4(),
    )

    assert stored.original_filename == "policy.pdf"
    assert stored.content_hash == "d3e03c71ab6dfc121caa538014277a3ee20c033d992d42749f9427c9c8562084"
    encrypted = (tmp_path / stored.storage_key).read_bytes()
    assert content not in encrypted
    assert evidence_storage.read_bytes(stored.storage_key) == content


@pytest.mark.parametrize(
    ("filename", "content", "max_bytes", "expected"),
    [
        ("empty.pdf", b"", 64, "Arquivo vazio."),
        ("large.pdf", b"x" * 65, 64, "Arquivo excede"),
        ("script.exe", b"x", 64, "Formato de arquivo"),
    ],
)
def test_store_bytes_rejects_invalid_payloads(monkeypatch, tmp_path, filename, content, max_bytes, expected):
    _configure_storage(monkeypatch, tmp_path, max_bytes=max_bytes)

    with pytest.raises(EvidenceStorageError, match=expected):
        evidence_storage.store_bytes(
            content=content,
            original_filename=filename,
            content_type="application/octet-stream",
            tenant_id=uuid.uuid4(),
            evidence_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
        )


def test_store_bytes_fails_closed_without_encryption_key(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", "")
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", 64)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())

    with pytest.raises(EvidenceStorageUnavailable, match="Chave de cifragem"):
        evidence_storage.store_bytes(
            content=b"x",
            original_filename="policy.pdf",
            content_type="application/pdf",
            tenant_id=uuid.uuid4(),
            evidence_id=uuid.uuid4(),
            version_id=uuid.uuid4(),
        )
