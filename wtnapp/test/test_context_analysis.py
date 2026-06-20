def test_context_issue_crud_and_framework_validation(client, context_seed, org_headers):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)

    invalid = client.post(
        "/context/analysis/issues",
        headers=headers,
        json={
            "origin": "external",
            "framework": "swot",
            "category": "Legal",
            "description": "LGPD aplicavel",
            "impact": "alto",
        },
    )
    assert invalid.status_code == 422

    created = client.post(
        "/context/analysis/issues",
        headers=headers,
        json={
            "origin": "external",
            "framework": "pestel",
            "category": "Legal",
            "description": "LGPD aplicavel",
            "impact": "alto",
        },
    )
    assert created.status_code == 201, created.text
    issue_id = created.json()["id"]

    listed = client.get("/context/analysis", headers=headers)
    assert listed.status_code == 200, listed.text
    assert listed.json()["issues"][0]["id"] == issue_id

    patched = client.patch(f"/context/analysis/issues/{issue_id}", headers=headers, json={"impact": "medio"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["impact"] == "medio"

    deleted = client.delete(f"/context/analysis/issues/{issue_id}", headers=headers)
    assert deleted.status_code == 204
