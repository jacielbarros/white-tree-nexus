from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context


def test_system_templates_seed_and_tenant_template_activation(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "template-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    listed = client.get("/print-documents/templates", headers=headers)
    assert listed.status_code == 200, listed.text
    assert {"context_report", "gap_report", "soa_report"} <= {row["document_type"] for row in listed.json()}

    created = client.post(
        "/print-documents/templates",
        headers=headers,
        json={"document_type": "context_report", "name": "Contexto tenant", "default_classification": "uso_interno"},
    )
    assert created.status_code == 201, created.text
    template = created.json()

    version = client.post(
        f"/print-documents/templates/{template['id']}/versions",
        headers=headers,
        json={
            "layout_schema": {
                "title": "Contexto tenant",
                "sections": [{"key": "diagnostic", "title": "Diagnostico"}],
            },
            "allowed_variables": {
                "required": ["organization_name", "document_title", "generated_at"],
                "optional": ["classification"],
            },
            "required_sections": ["diagnostic"],
        },
    )
    assert version.status_code == 201, version.text

    activated = client.post(
        f"/print-documents/templates/{template['id']}/versions/{version.json()['id']}/activate",
        headers=headers,
    )
    assert activated.status_code == 200, activated.text
    assert activated.json()["current_version_id"] == version.json()["id"]


def test_system_template_version_cannot_be_mutated_by_org_admin(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "template-system")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    system_template = next(row for row in client.get("/print-documents/templates", headers=headers).json() if row["scope"] == "system")

    resp = client.post(
        f"/print-documents/templates/{system_template['id']}/versions",
        headers=headers,
        json={"layout_schema": {"sections": []}, "allowed_variables": {}, "required_sections": []},
    )
    assert resp.status_code == 403
