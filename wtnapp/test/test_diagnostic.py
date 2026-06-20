from wtnapp.models.audit_log_model import AuditLog


def test_diagnostic_draft_can_be_resumed(client, context_seed, org_headers, db):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    payload = {"status": "draft", "sections": {"dados": {"dados_pessoais": True}}}

    save = client.put("/context/diagnostic", headers=headers, json=payload)
    assert save.status_code == 200, save.text

    resumed = client.get("/context/diagnostic", headers=headers)
    assert resumed.status_code == 200, resumed.text
    assert resumed.json()["sections"] == payload["sections"]

    assert db.query(AuditLog).filter(AuditLog.operation == "DIAGNOSTIC_SAVE").count() == 1


def test_client_cannot_manage_diagnostic(client, context_seed, org_headers):
    headers = org_headers("client@ctx-acme.com", context_seed["org"].id)

    response = client.put("/context/diagnostic", headers=headers, json={"status": "draft", "sections": {}})

    assert response.status_code == 403
