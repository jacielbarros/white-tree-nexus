"""Sugestoes deterministicas a partir do diagnostico."""

from wtnapp.models.diagnostic_model import Diagnostic

_TRUTHY = {True, 1, "true", "sim", "yes", "1"}


def _is_truthy(value) -> bool:
    return value in _TRUTHY or (isinstance(value, str) and value.strip().lower() in {"true", "sim", "yes", "1"})


def _has_personal_data(sections: dict) -> bool:
    """Detecta tratamento de dados pessoais nos dois formatos de diagnostico.

    - Formato form-builder: ``{"campos": [{"chave"/"rotulo", "tipo": "boolean", "valor": ...}]}``.
    - Formato legado/compat: ``{"dados": {"dados_pessoais": true}}``.
    """
    for field in sections.get("campos", []) or []:
        if not isinstance(field, dict):
            continue
        chave = str(field.get("chave", "")).strip().lower()
        rotulo = str(field.get("rotulo", "")).strip().lower()
        if (chave == "dados_pessoais" or "dados pessoais" in rotulo) and _is_truthy(field.get("valor")):
            return True
    return sections.get("dados", {}).get("dados_pessoais") is True


def build_suggestions(diagnostic: Diagnostic | None) -> list[dict]:
    if diagnostic is None:
        return []
    sections = diagnostic.sections or {}
    suggestions: list[dict] = []
    if _has_personal_data(sections):
        suggestions.extend(
            [
                {
                    "id": "stakeholder-anpd",
                    "target": "stakeholder",
                    "payload": {
                        "name": "ANPD",
                        "type": "external",
                        "power": "alto",
                        "interest": "medio",
                        "requirements": [
                            {
                                "type": "regulatory",
                                "description": "Atender aos requisitos da LGPD aplicaveis.",
                                "how_addressed": "Governanca de privacidade integrada ao SGSI.",
                            }
                        ],
                    },
                    "reason": "Diagnostico indica tratamento de dados pessoais.",
                },
                {
                    "id": "stakeholder-titulares",
                    "target": "stakeholder",
                    "payload": {
                        "name": "Titulares de dados pessoais",
                        "type": "external",
                        "power": "medio",
                        "interest": "alto",
                        "requirements": [
                            {
                                "type": "legal",
                                "description": "Preservar direitos dos titulares conforme LGPD.",
                                "how_addressed": "Controles de atendimento e seguranca da informacao.",
                            }
                        ],
                    },
                    "reason": "Diagnostico indica tratamento de dados pessoais.",
                },
            ]
        )
    return suggestions
