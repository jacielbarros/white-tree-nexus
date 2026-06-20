def test_scope_items_and_version_references(client, context_seed, org_headers):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)

    item = client.post(
        "/context/scope/items",
        headers=headers,
        json={
            "kind": "inclusion",
            "description": "Plataforma SaaS e suporte",
            "justification": "Receita principal",
        },
    )
    assert item.status_code == 201, item.text

    updated = client.put(
        "/context/scope",
        headers=headers,
        json={"interfaces_dependencies": "Provedor de nuvem", "context_version_ref": None, "stakeholder_version_ref": None},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["items"][0]["kind"] == "inclusion"


def test_scope_signals_obsolete_context_reference(client, context_seed, org_headers):
    """FR-010 / T022 — referência a versão superada da Análise de Contexto é sinalizada."""
    consultant = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    admin = org_headers("admin@ctx-acme.com", context_seed["org"].id)

    # Emite a versão 1 da Análise de Contexto.
    client.put("/context/analysis", headers=consultant, json={"intended_outcomes": "v1"})
    client.post("/context/analysis/submit-review", headers=consultant)
    v1 = client.post(
        "/context/analysis/approve", headers=admin, json={"classification": "uso_interno"}
    ).json()["id"]

    # Escopo referencia a versão 1; ainda não está obsoleta.
    client.put(
        "/context/scope",
        headers=consultant,
        json={"interfaces_dependencies": "x", "context_version_ref": v1, "stakeholder_version_ref": None},
    )
    assert client.get("/context/scope", headers=consultant).json()["context_ref_obsolete"] is False

    # Emite a versão 2 da Análise de Contexto → a referência (v1) fica desatualizada.
    client.put("/context/analysis", headers=consultant, json={"intended_outcomes": "v2"})
    client.post("/context/analysis/submit-review", headers=consultant)
    client.post("/context/analysis/approve", headers=admin, json={"classification": "uso_interno"})

    assert client.get("/context/scope", headers=consultant).json()["context_ref_obsolete"] is True
