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

    external_swot = client.post(
        "/context/analysis/issues",
        headers=headers,
        json={
            "origin": "external",
            "framework": "swot",
            "nature": "opportunity",
            "category": "Oportunidade",
            "description": "Mercado valoriza certificacao ISO 27001 em due diligence.",
            "impact": "medio",
        },
    )
    assert external_swot.status_code == 201, external_swot.text
    assert external_swot.json()["nature"] == "opportunity"

    internal_strength = client.post(
        "/context/analysis/issues",
        headers=headers,
        json={
            "origin": "internal",
            "framework": "swot",
            "nature": "strength",
            "category": "Forca",
            "description": "Patrocinio executivo direto fortalece a implantacao do SGSI.",
            "impact": "alto",
        },
    )
    assert internal_strength.status_code == 201, internal_strength.text
    assert internal_strength.json()["nature"] == "strength"

    created = client.post(
        "/context/analysis/issues",
        headers=headers,
        json={
            "origin": "external",
            "framework": "pestel",
            "nature": "threat",
            "category": "Legal",
            "description": "LGPD aplicavel",
            "impact": "alto",
        },
    )
    assert created.status_code == 201, created.text
    issue_id = created.json()["id"]

    listed = client.get("/context/analysis", headers=headers)
    assert listed.status_code == 200, listed.text
    assert issue_id in {item["id"] for item in listed.json()["issues"]}

    patched = client.patch(f"/context/analysis/issues/{issue_id}", headers=headers, json={"impact": "medio"})
    assert patched.status_code == 200, patched.text
    assert patched.json()["impact"] == "medio"

    deleted = client.delete(f"/context/analysis/issues/{issue_id}", headers=headers)
    assert deleted.status_code == 204
