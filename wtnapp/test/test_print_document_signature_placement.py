from wtnapp.test.print_document_helpers import (
    configure_document_storage,
    create_preview,
    default_placement_payload,
    headers_for,
    seed_context,
)


def _preview_and_layout(client, headers):
    preview = create_preview(client, headers)
    layout = client.get(f"/print-documents/previews/{preview['id']}/layout", headers=headers)
    assert layout.status_code == 200, layout.text
    return preview, layout.json()


def test_confirm_and_list_signature_placements_are_append_only(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-happy")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview, layout = _preview_and_layout(client, headers)

    payload = default_placement_payload(preview, layout)
    first = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert first.status_code == 201, first.text
    assert first.json()["placement_revision"] == 1
    assert first.json()["placement_hash"]

    second_payload = {**payload, "x_points": payload["x_points"] - 12}
    second = client.post(
        f"/print-documents/previews/{preview['id']}/signature-placements",
        headers=headers,
        json=second_payload,
    )
    assert second.status_code == 201, second.text
    assert second.json()["placement_revision"] == 2

    listed = client.get(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers)
    assert listed.status_code == 200, listed.text
    assert [row["placement_revision"] for row in listed.json()] == [1, 2]


def test_invalid_signature_placement_bounds_are_rejected(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-bounds")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview, layout = _preview_and_layout(client, headers)

    payload = default_placement_payload(preview, layout)
    payload["x_points"] = payload["page_width_points"]
    resp = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert resp.status_code == 400


def test_invalid_signature_placement_page_is_rejected(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-page")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview, layout = _preview_and_layout(client, headers)

    payload = default_placement_payload(preview, layout)
    payload["page_number"] = 999
    resp = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert resp.status_code == 400


def test_page_dimension_mismatch_is_rejected(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "placement-dimension")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    preview, layout = _preview_and_layout(client, headers)

    payload = default_placement_payload(preview, layout)
    payload["page_width_points"] = payload["page_width_points"] + 10
    resp = client.post(f"/print-documents/previews/{preview['id']}/signature-placements", headers=headers, json=payload)
    assert resp.status_code == 400
