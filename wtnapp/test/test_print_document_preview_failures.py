from wtnapp import settings
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context
from wtnapp.settings import OrgStatus


def test_preview_fails_with_insufficient_context_source_data(client, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    org = factory.org("missing-context", "Missing Context")
    admin = factory.user("admin@missing-context.com", full_name="Admin Missing")
    factory.membership(admin, org)
    headers = headers_for(org_headers, admin, org)

    resp = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"})
    assert resp.status_code == 422
    assert "missing_sections" in resp.json()["detail"] or "missing_sections" in resp.json()


def test_preview_fails_closed_without_encryption_key(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", "")
    seed = seed_context(db, factory, "no-key-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    resp = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"})
    assert resp.status_code == 503


def test_classification_denies_preliminary_download(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "class-context")
    db.add(ClassificationAccessPolicy(tenant_id=seed["org"].id, rules={"confidencial": ["org_admin"]}))
    db.commit()
    admin_headers = headers_for(org_headers, seed["admin"], seed["org"])
    client_headers = headers_for(org_headers, seed["client"], seed["org"])
    preview = client.post(
        "/print-documents/previews",
        headers=admin_headers,
        json={"document_type": "context_report", "classification": "confidencial"},
    ).json()

    denied = client.get(f"/print-documents/previews/{preview['id']}/pdf", headers=client_headers)
    assert denied.status_code == 403


def test_suspended_org_blocks_preview(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "suspended-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    seed["org"].status = OrgStatus.suspended
    db.commit()

    resp = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"})
    assert resp.status_code == 403
