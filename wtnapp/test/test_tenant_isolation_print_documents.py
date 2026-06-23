from wtnapp.models.audit_log_model import AuditLog
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context
from wtnapp.settings import Role


def test_preview_and_signed_documents_are_tenant_scoped(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    a = seed_context(db, factory, "print-tenant-a")
    b = seed_context(db, factory, "print-tenant-b")
    ha = headers_for(org_headers, a["admin"], a["org"])
    hb = headers_for(org_headers, b["admin"], b["org"])

    preview = client.post("/print-documents/previews", headers=ha, json={"document_type": "context_report"}).json()
    signed = client.post(
        f"/print-documents/previews/{preview['id']}/sign",
        headers=ha,
        json={"confirm_snapshot_hash": preview["snapshot_hash"]},
    ).json()

    assert client.get(f"/print-documents/previews/{preview['id']}", headers=hb).status_code == 404
    assert client.get(f"/print-documents/signed/{signed['id']}", headers=hb).status_code == 404
    assert client.get(f"/print-documents/signed/{signed['id']}/pdf", headers=hb).status_code == 404


def test_super_admin_requires_explicit_org_context(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "print-super-admin")
    super_admin = factory.user("super@platform.com", full_name="Super", super_admin=True)
    headers = org_headers(super_admin.email, seed["org"].id)
    preview = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"})
    assert preview.status_code == 201, preview.text

    no_context = {k: v for k, v in headers.items() if k != "X-Org-Context"}
    denied = client.post("/print-documents/previews", headers=no_context, json={"document_type": "context_report"})
    assert denied.status_code == 400
