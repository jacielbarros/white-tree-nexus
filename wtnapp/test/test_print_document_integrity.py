from pathlib import Path
from uuid import UUID

from wtnapp import settings
from wtnapp.models.print_document_model import SignedDocument
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context


def test_integrity_verification_detects_tampered_storage(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "integrity-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"}).json()
    signed = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    ).json()

    ok = client.post(f"/print-documents/signed/{signed['id']}/verify", headers=headers)
    assert ok.status_code == 200
    assert ok.json()["valid"] is True

    doc = db.get(SignedDocument, UUID(signed["id"]))
    path = Path(settings.DOCUMENT_STORAGE_DIR) / doc.pdf_storage_key
    path.write_bytes(b"tampered")

    tampered = client.post(f"/print-documents/signed/{signed['id']}/verify", headers=headers)
    assert tampered.status_code == 200
    assert tampered.json()["valid"] is False
