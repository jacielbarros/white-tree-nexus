import pytest


@pytest.mark.parametrize(
    ("power", "interest", "expected"),
    [
        ("alto", "alto", "manage_closely"),
        ("alto", "medio", "keep_satisfied"),
        ("medio", "alto", "keep_informed"),
        ("baixo", "baixo", "monitor"),
    ],
)
def test_mendelow_strategy_derivation(client, context_seed, org_headers, power, interest, expected):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)

    response = client.post(
        "/context/stakeholders",
        headers=headers,
        json={"name": f"{power}-{interest}", "type": "external", "power": power, "interest": interest},
    )

    assert response.status_code == 201, response.text
    assert response.json()["strategy"] == expected


def test_stakeholder_requirements_crud_shape(client, context_seed, org_headers):
    headers = org_headers("consultant@ctx-acme.com", context_seed["org"].id)

    response = client.post(
        "/context/stakeholders",
        headers=headers,
        json={
            "name": "Cliente enterprise",
            "type": "external",
            "power": "alto",
            "interest": "alto",
            "requirements": [
                {
                    "type": "contractual",
                    "description": "SLA de seguranca",
                    "how_addressed": "Controles no SGSI",
                }
            ],
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["requirements"][0]["type"] == "contractual"
