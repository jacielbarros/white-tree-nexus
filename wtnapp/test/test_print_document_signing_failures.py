from datetime import datetime, timedelta, timezone
from uuid import UUID

from wtnapp.models.print_document_model import DocumentPreview
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context


def test_expired_preview_cannot_be_signed(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "expired-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"}).json()
    row = db.get(DocumentPreview, UUID(preview["id"]))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    resp = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    )
    assert resp.status_code == 409


def test_client_with_view_permission_cannot_sign_context_report(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "sign-denied-context")
    admin_headers = headers_for(org_headers, seed["admin"], seed["org"])
    client_headers = headers_for(org_headers, seed["client"], seed["org"])
    preview = client.post("/print-documents/previews", headers=admin_headers, json={"document_type": "context_report"}).json()

    resp = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=client_headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    )
    assert resp.status_code == 403
