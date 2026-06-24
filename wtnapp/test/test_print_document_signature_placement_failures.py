from datetime import datetime, timedelta, timezone
from uuid import UUID

from wtnapp.models.print_document_model import DocumentPreview
from wtnapp.services import document_signature_service
from wtnapp.test.print_document_helpers import (
    configure_document_storage,
    create_preview,
    default_placement_payload,
    headers_for,
    seed_context,
)


def test_blocked_area_rejects_signature_placement(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-blocked")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = create_preview(client, headers)
    layout = client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers).json()
    payload = default_placement_payload(preview, layout)

    def _policy(_version):
        return {
            "default_page": "last",
            "default_anchor": "bottom_right",
            "default_margin_points": 36,
            "default_width_points": 180,
            "default_height_points": 54,
            "min_width_points": 96,
            "min_height_points": 32,
            "max_width_points": 260,
            "max_height_points": 96,
            "blocked_areas": [
                {
                    "page": payload["page_number"],
                    "x_points": payload["x_points"],
                    "y_points": payload["y_points"],
                    "width_points": payload["width_points"],
                    "height_points": payload["height_points"],
                    "reason": "Area reservada",
                }
            ],
        }

    monkeypatch.setattr(document_signature_service, "signature_appearance_policy", _policy)

    resp = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert resp.status_code == 400


def test_expired_preview_rejects_signature_placement(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-expired")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = create_preview(client, headers)
    layout = client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers).json()
    payload = default_placement_payload(preview, layout)

    row = db.get(DocumentPreview, UUID(preview["id"]))
    row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.commit()

    resp = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert resp.status_code == 409
