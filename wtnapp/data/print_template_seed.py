"""Default system print templates for Feature 009.

Seeds are metadata only and never include tenant data. The migration and service
use the same definitions so default templates stay deterministic.
"""

from __future__ import annotations

from copy import deepcopy

from wtnapp.settings import Classification, PrintableDocumentType


DEFAULT_TEMPLATE_DEFINITIONS: tuple[dict, ...] = (
    {
        "document_type": PrintableDocumentType.context_report.value,
        "name": "Relatorio consolidado de Contexto",
        "description": "Template padrao para diagnostico e contexto da organizacao.",
        "default_classification": Classification.uso_interno.value,
        "layout_schema": {
            "title": "Relatorio de Contexto da Organizacao",
            "sections": [
                {"key": "diagnostic", "title": "Diagnostico"},
                {"key": "analysis", "title": "Analise de contexto"},
                {"key": "stakeholders", "title": "Partes interessadas"},
                {"key": "scope", "title": "Escopo do SGSI"},
            ],
        },
        "allowed_variables": {
            "required": ["organization_name", "document_title", "generated_at"],
            "optional": ["classification", "document_status", "source_reference"],
        },
        "required_sections": ["diagnostic", "analysis", "stakeholders", "scope"],
    },
    {
        "document_type": PrintableDocumentType.gap_report.value,
        "name": "Relatorio de Gap Analysis",
        "description": "Template padrao para matriz e dashboard de aderencia.",
        "default_classification": Classification.uso_interno.value,
        "layout_schema": {
            "title": "Relatorio de Gap Analysis",
            "sections": [
                {"key": "summary", "title": "Resumo de aderencia"},
                {"key": "distribution", "title": "Distribuicao por status"},
                {"key": "items", "title": "Matriz de controles"},
                {"key": "gaps", "title": "Lacunas priorizadas"},
            ],
        },
        "allowed_variables": {
            "required": ["organization_name", "document_title", "generated_at"],
            "optional": ["classification", "document_status", "source_reference"],
        },
        "required_sections": ["summary", "items"],
    },
    {
        "document_type": PrintableDocumentType.soa_report.value,
        "name": "Relatorio de Declaracao de Aplicabilidade",
        "description": "Template padrao para SoA consolidada e controles aplicaveis.",
        "default_classification": Classification.uso_interno.value,
        "layout_schema": {
            "title": "Declaracao de Aplicabilidade (SoA)",
            "sections": [
                {"key": "summary", "title": "Resumo"},
                {"key": "items", "title": "Controles da SoA"},
                {"key": "divergences", "title": "Divergencias com Gap Analysis"},
            ],
        },
        "allowed_variables": {
            "required": ["organization_name", "document_title", "generated_at"],
            "optional": ["classification", "document_status", "source_reference"],
        },
        "required_sections": ["summary", "items"],
    },
)


def default_templates() -> list[dict]:
    """Return a defensive copy of default template definitions."""
    return deepcopy(list(DEFAULT_TEMPLATE_DEFINITIONS))
