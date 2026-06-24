from datetime import datetime, timedelta, timezone
from uuid import UUID

from wtnapp.models.context_analysis_model import ContextAnalysis
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.models.print_document_model import DocumentPreview
from wtnapp.settings import OrgStatus
from wtnapp.test.print_document_helpers import (
    configure_document_storage,
    create_preview,
    headers_for,
    seed_context,
)


def test_inline_pdf_and_layout_happy_path(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "interactive-preview")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    preview = create_preview(client, headers)

    pdf = client.get(f"/print-documents/previews/{preview['id']}/inline-pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")
    assert pdf.headers["content-disposition"].startswith("inline")

    layout = client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers)
    assert layout.status_code == 200, layout.text
    body = layout.json()
    assert body["preview_id"] == preview["id"]
    assert body["snapshot_hash"] == preview["snapshot_hash"]
    assert body["page_metrics"]
    assert body["default_placement"]["coordinate_system"] == "pdf_points_bottom_left"


def test_expired_preview_blocks_inline_layout(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "interactive-expired")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = create_preview(client, headers)

    row = db.get(DocumentPreview, UUID(preview["id"]))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    assert client.get(f"/print-documents/previews/{preview['id']}/inline-pdf", headers=headers).status_code == 409
    assert client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers).status_code == 409


def test_stale_preview_blocks_inline_layout(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "interactive-stale")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = create_preview(client, headers)

    analysis = db.query(ContextAnalysis).filter_by(tenant_id=seed["org"].id).first()
    analysis.intended_outcomes = "Mudanca apos preview."
    db.commit()

    assert client.get(f"/print-documents/previews/{preview['id']}/inline-pdf", headers=headers).status_code == 409
    assert client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers).status_code == 409


def test_suspended_organization_blocks_inline_layout(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "interactive-suspended")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = create_preview(client, headers)

    seed["org"].status = OrgStatus.suspended
    db.commit()

    assert client.get(f"/print-documents/previews/{preview['id']}/inline-pdf", headers=headers).status_code == 403
    assert client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers).status_code == 403


def test_classification_denial_blocks_inline_layout(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "interactive-classification")
    admin_headers = headers_for(org_headers, seed["admin"], seed["org"])
    client_headers = headers_for(org_headers, seed["client"], seed["org"])
    preview = create_preview(client, admin_headers, classification="restrito")

    db.add(
        ClassificationAccessPolicy(
            tenant_id=seed["org"].id,
            rules={"restrito": ["org_admin"]},
        )
    )
    db.commit()

    assert client.get(f"/print-documents/previews/{preview['id']}/inline-pdf", headers=client_headers).status_code == 403
    assert client.get(f"/print-documents/previews/{preview['id']}/layout", headers=client_headers).status_code == 403
