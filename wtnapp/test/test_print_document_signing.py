from wtnapp.models.context_analysis_model import ContextAnalysis
from wtnapp.settings import OrgStatus
from wtnapp.test.print_document_helpers import (
    configure_document_storage,
    default_placement_payload,
    headers_for,
    seed_context,
)


def _preview(client, headers):
    resp = client.post(
        "/print-documents/previews",
        headers=headers,
        json={"document_type": "context_report", "classification": "uso_interno"},
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_sign_preview_creates_immutable_signed_pdf(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "sign-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    preview = _preview(client, headers)
    signed = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    )
    assert signed.status_code == 201, signed.text
    signed_body = signed.json()
    assert signed_body["identifier"].startswith("WTN-CONTEXT-REPORT")
    assert signed_body["pdf_hash"]
    assert signed_body["signature_method"] == "internal_electronic_signature"
    assert signed_body["visual_signature_present"] is True
    assert signed_body["signature_placement"]["origin"] == "default"

    pdf = client.get(f"/print-documents/signed/{signed_body['id']}/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content.startswith(b"%PDF")

    analysis = db.query(ContextAnalysis).filter_by(tenant_id=seed["org"].id).first()
    analysis.intended_outcomes = "Texto alterado depois da assinatura."
    db.commit()

    again = client.get(f"/print-documents/signed/{signed_body['id']}", headers=headers)
    assert again.status_code == 200
    assert again.json()["pdf_hash"] == signed_body["pdf_hash"]


def test_sign_preview_with_confirmed_placement_freezes_signed_placement(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "sign-confirmed-placement")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    preview = _preview(client, headers)
    layout = client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers)
    assert layout.status_code == 200, layout.text
    placement_payload = default_placement_payload(preview, layout.json())
    placement_payload["x_points"] = placement_payload["x_points"] - 18
    placement = client.post(
        f"/print-documents/previews/{preview['id']}/signature-placements",
        headers=headers,
        json=placement_payload,
    )
    assert placement.status_code == 201, placement.text

    signed = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={
            "confirm_snapshot_hash": preview["snapshot_hash"],
            "confirmed_placement_id": placement.json()["id"],
        },
    )
    assert signed.status_code == 201, signed.text
    signed_body = signed.json()
    assert signed_body["signature_placement"]["placement_id"] == placement.json()["id"]
    assert signed_body["signature_placement"]["placement_hash"] == placement.json()["placement_hash"]

    frozen = client.get(f"/print-documents/signed/{signed_body['id']}/signature-placement", headers=headers)
    assert frozen.status_code == 200, frozen.text
    assert frozen.json()["placement_id"] == placement.json()["id"]


def test_stale_preview_cannot_be_signed(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "stale-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = _preview(client, headers)

    analysis = db.query(ContextAnalysis).filter_by(tenant_id=seed["org"].id).first()
    analysis.intended_outcomes = "Mudanca apos preview."
    db.commit()

    resp = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    )
    assert resp.status_code == 409


def test_suspended_organization_cannot_sign_preview(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "sign-suspended")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview = _preview(client, headers)

    seed["org"].status = OrgStatus.suspended
    db.commit()

    resp = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    )
    assert resp.status_code == 403
