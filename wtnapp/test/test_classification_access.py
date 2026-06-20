def test_classification_policy_restricts_reading_in_force_artifact(client, context_seed, org_headers):
    consultant_headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    admin_headers = org_headers("admin@ctx-acme.com", context_seed["org"].id)

    client.post("/context/analysis/submit-review", headers=consultant_headers)
    approved = client.post(
        "/context/analysis/approve",
        headers=admin_headers,
        json={"classification": "restrito", "change_nature": "Emissao inicial"},
    )
    assert approved.status_code == 201, approved.text

    allowed_before_policy = client.get("/context/analysis", headers=consultant_headers)
    assert allowed_before_policy.status_code == 200

    policy = client.put(
        "/context/classification-policy",
        headers=admin_headers,
        json={"rules": {"restrito": ["org_admin"]}},
    )
    assert policy.status_code == 200, policy.text

    denied_after_policy = client.get("/context/analysis", headers=consultant_headers)
    assert denied_after_policy.status_code == 403
