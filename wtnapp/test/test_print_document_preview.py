from wtnapp.test.print_document_helpers import (
    configure_document_storage,
    headers_for,
    seed_context,
    seed_gap,
    seed_soa,
)


def test_preview_context_gap_and_soa(client, db, factory, gap_seed, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)

    context = seed_context(db, factory, "preview-context")
    gap = seed_gap(db, factory, gap_seed, "preview-gap")
    soa = seed_soa(db, factory, gap_seed, "preview-soa")

    cases = [
        (context, "context_report"),
        (gap, "gap_report"),
        (soa, "soa_report"),
    ]
    for seed, document_type in cases:
        headers = headers_for(org_headers, seed["admin"], seed["org"])
        resp = client.post(
            "/print-documents/previews",
            headers=headers,
            json={"document_type": document_type, "classification": "uso_interno"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["document_type"] == document_type
        assert body["status"] == "active"
        assert body["snapshot_hash"]

        pdf = client.get(f"/print-documents/previews/{body['id']}/pdf", headers=headers)
        assert pdf.status_code == 200, pdf.text
        assert pdf.content.startswith(b"%PDF")
