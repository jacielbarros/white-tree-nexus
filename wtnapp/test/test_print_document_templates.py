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


def test_template_variable_catalog_seeds_and_controls_template_versions(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "template-variables")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    listed = client.get("/print-documents/template-variables?document_type=gap_report", headers=headers)
    assert listed.status_code == 200, listed.text
    keys = {row["variable_key"] for row in listed.json()}
    assert {"organization_name", "document_title", "generated_at", "overall_adherence"} <= keys

    created = client.post(
        "/print-documents/template-variables",
        headers=headers,
        json={
            "document_type": "gap_report",
            "variable_key": "audit_cycle",
            "label": "Ciclo de auditoria",
            "description": "Ciclo ou janela de auditoria usada no documento.",
            "value_type": "string",
            "optional_by_default": True,
            "sort_order": 500,
        },
    )
    assert created.status_code == 201, created.text

    template = client.post(
        "/print-documents/templates",
        headers=headers,
        json={"document_type": "gap_report", "name": "Gap com catalogo", "default_classification": "uso_interno"},
    ).json()

    unknown = client.post(
        f"/print-documents/templates/{template['id']}/versions",
        headers=headers,
        json={
            "layout_schema": {"title": "Gap", "sections": [{"key": "summary", "title": "Resumo"}]},
            "allowed_variables": {"required": ["organization_name"], "optional": ["variavel_solto"]},
            "required_sections": ["summary"],
        },
    )
    assert unknown.status_code == 422, unknown.text
    assert "variavel_solto" in unknown.text

    accepted = client.post(
        f"/print-documents/templates/{template['id']}/versions",
        headers=headers,
        json={
            "layout_schema": {"title": "Gap", "sections": [{"key": "summary", "title": "Resumo"}]},
            "allowed_variables": {"required": ["organization_name"], "optional": ["audit_cycle"]},
            "required_sections": ["summary"],
        },
    )
    assert accepted.status_code == 201, accepted.text


def test_tenant_template_variables_are_logically_deactivated(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "template-variable-delete")
    headers = headers_for(org_headers, seed["admin"], seed["org"])
    created = client.post(
        "/print-documents/template-variables",
        headers=headers,
        json={
            "document_type": "context_report",
            "variable_key": "review_cycle",
            "label": "Ciclo de revisao",
            "optional_by_default": True,
        },
    )
    assert created.status_code == 201, created.text

    deleted = client.delete(f"/print-documents/template-variables/{created.json()['id']}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["status"] == "inactive"

    active = client.get("/print-documents/template-variables?document_type=context_report", headers=headers)
    assert "review_cycle" not in {row["variable_key"] for row in active.json()}

    inactive = client.get(
        "/print-documents/template-variables?document_type=context_report&include_inactive=true",
        headers=headers,
    )
    assert "review_cycle" in {row["variable_key"] for row in inactive.json()}


def test_tenant_template_variables_are_isolated_by_org(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    org_a = seed_context(db, factory, "template-variable-org-a")
    org_b = seed_context(db, factory, "template-variable-org-b")
    headers_a = headers_for(org_headers, org_a["admin"], org_a["org"])
    headers_b = headers_for(org_headers, org_b["admin"], org_b["org"])

    created = client.post(
        "/print-documents/template-variables",
        headers=headers_a,
        json={
            "document_type": "gap_report",
            "variable_key": "tenant_private_note",
            "label": "Nota privada do tenant",
            "optional_by_default": True,
        },
    )
    assert created.status_code == 201, created.text

    listed_a = client.get("/print-documents/template-variables?document_type=gap_report", headers=headers_a)
    listed_b = client.get("/print-documents/template-variables?document_type=gap_report", headers=headers_b)
    assert "tenant_private_note" in {row["variable_key"] for row in listed_a.json()}
    assert "tenant_private_note" not in {row["variable_key"] for row in listed_b.json()}

    denied = client.patch(
        f"/print-documents/template-variables/{created.json()['id']}",
        headers=headers_b,
        json={"label": "Tentativa cross-tenant"},
    )
    assert denied.status_code == 404


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
