from wtnapp import settings
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context


def test_renderer_timeout_is_reported(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "DOCUMENT_RENDER_TIMEOUT_SECONDS", 0)
    seed = seed_context(db, factory, "timeout-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    resp = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"})
    assert resp.status_code == 503
