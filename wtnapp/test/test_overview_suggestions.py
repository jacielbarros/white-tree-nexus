def test_suggestions_are_not_persisted_until_accept(client, context_seed, org_headers):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    client.put(
        "/context/diagnostic",
        headers=headers,
        json={"status": "draft", "sections": {"dados": {"dados_pessoais": True}}},
    )

    suggestions = client.get("/context/suggestions", headers=headers)
    assert suggestions.status_code == 200, suggestions.text
    assert len(suggestions.json()) == 2

    before = client.get("/context/stakeholders", headers=headers)
    assert before.json()["stakeholders"] == []

    accepted = client.post("/context/suggestions/accept", headers=headers, json={"suggestion_id": "stakeholder-anpd"})
    assert accepted.status_code == 200, accepted.text

    after = client.get("/context/stakeholders", headers=headers)
    assert after.json()["stakeholders"][0]["name"] == "ANPD"


def test_suggestions_detect_personal_data_in_form_builder_shape(client, context_seed, org_headers):
    """O motor de sugestoes le o formato form-builder (campos[]), nao so o legado."""
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)
    client.put(
        "/context/diagnostic",
        headers=headers,
        json={
            "status": "draft",
            "sections": {
                "versao_form": 1,
                "campos": [
                    {"secao": "Negocio", "rotulo": "Setor", "chave": "setor", "tipo": "text", "valor": "SaaS"},
                    {
                        "secao": "Dados tratados",
                        "rotulo": "A organizacao trata dados pessoais?",
                        "chave": "dados_pessoais",
                        "tipo": "boolean",
                        "valor": True,
                    },
                ],
            },
        },
    )
    suggestions = client.get("/context/suggestions", headers=headers)
    assert suggestions.status_code == 200, suggestions.text
    assert {s["id"] for s in suggestions.json()} == {"stakeholder-anpd", "stakeholder-titulares"}
