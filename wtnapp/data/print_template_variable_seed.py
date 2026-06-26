"""Default variable catalog for printable templates."""

from __future__ import annotations

from copy import deepcopy

from wtnapp.settings import PrintableDocumentType

COMMON_VARIABLES: tuple[dict, ...] = (
    {
        "variable_key": "organization_name",
        "label": "Organizacao",
        "description": "Nome da organizacao no documento.",
        "value_type": "string",
        "required_by_default": True,
        "optional_by_default": False,
        "sort_order": 10,
    },
    {
        "variable_key": "document_title",
        "label": "Titulo do documento",
        "description": "Titulo usado no cabecalho e no registro controlado.",
        "value_type": "string",
        "required_by_default": True,
        "optional_by_default": False,
        "sort_order": 20,
    },
    {
        "variable_key": "generated_at",
        "label": "Data de geracao",
        "description": "Momento em que o documento foi gerado.",
        "value_type": "datetime",
        "required_by_default": True,
        "optional_by_default": False,
        "sort_order": 30,
    },
    {
        "variable_key": "classification",
        "label": "Classificacao",
        "description": "Classificacao de sensibilidade do documento.",
        "value_type": "string",
        "required_by_default": False,
        "optional_by_default": True,
        "sort_order": 40,
    },
    {
        "variable_key": "document_status",
        "label": "Status",
        "description": "Estado visual do documento: preview, assinado ou obsoleto.",
        "value_type": "string",
        "required_by_default": False,
        "optional_by_default": True,
        "sort_order": 50,
    },
    {
        "variable_key": "source_reference",
        "label": "Referencia de origem",
        "description": "Identificador do artefato usado como fonte.",
        "value_type": "string",
        "required_by_default": False,
        "optional_by_default": True,
        "sort_order": 60,
    },
)

DOMAIN_VARIABLES: dict[str, tuple[dict, ...]] = {
    PrintableDocumentType.context_report.value: (
        {
            "variable_key": "diagnostic_status",
            "label": "Status do diagnostico",
            "description": "Status do diagnostico de contexto usado no documento.",
            "value_type": "string",
            "sort_order": 110,
        },
        {
            "variable_key": "context_issue_count",
            "label": "Fatores de contexto",
            "description": "Quantidade de fatores internos e externos registrados.",
            "value_type": "number",
            "sort_order": 120,
        },
        {
            "variable_key": "stakeholder_count",
            "label": "Partes interessadas",
            "description": "Quantidade de partes interessadas mapeadas.",
            "value_type": "number",
            "sort_order": 130,
        },
    ),
    PrintableDocumentType.gap_report.value: (
        {
            "variable_key": "total_controls",
            "label": "Total de controles",
            "description": "Quantidade total de controles do Gap Analysis.",
            "value_type": "number",
            "sort_order": 110,
        },
        {
            "variable_key": "assessed_controls",
            "label": "Controles avaliados",
            "description": "Quantidade de controles com avaliacao preenchida.",
            "value_type": "number",
            "sort_order": 120,
        },
        {
            "variable_key": "overall_adherence",
            "label": "Aderencia geral",
            "description": "Percentual geral de aderencia do Gap Analysis.",
            "value_type": "number",
            "sort_order": 130,
        },
        {
            "variable_key": "critical_gaps",
            "label": "Lacunas criticas",
            "description": "Quantidade de lacunas classificadas como criticas.",
            "value_type": "number",
            "sort_order": 140,
        },
    ),
    PrintableDocumentType.soa_report.value: (
        {
            "variable_key": "applicable_controls",
            "label": "Controles aplicaveis",
            "description": "Quantidade de controles marcados como aplicaveis na SoA.",
            "value_type": "number",
            "sort_order": 110,
        },
        {
            "variable_key": "excluded_controls",
            "label": "Controles excluidos",
            "description": "Quantidade de controles justificados como nao aplicaveis.",
            "value_type": "number",
            "sort_order": 120,
        },
        {
            "variable_key": "divergent_controls",
            "label": "Divergencias com Gap",
            "description": "Quantidade de divergencias entre SoA e Gap Analysis.",
            "value_type": "number",
            "sort_order": 130,
        },
    ),
    PrintableDocumentType.gap_baseline.value: (
        {
            "variable_key": "baseline_version",
            "label": "Versao da baseline",
            "description": "Numero da baseline congelada.",
            "value_type": "string",
            "sort_order": 110,
        },
        {
            "variable_key": "baseline_date",
            "label": "Data da baseline",
            "description": "Data de emissao da baseline.",
            "value_type": "date",
            "sort_order": 120,
        },
    ),
    PrintableDocumentType.form_response.value: (
        {
            "variable_key": "form_title",
            "label": "Titulo do formulario",
            "description": "Titulo do formulario respondido.",
            "value_type": "string",
            "sort_order": 110,
        },
        {
            "variable_key": "respondent_name",
            "label": "Respondente",
            "description": "Nome ou identificacao do respondente.",
            "value_type": "string",
            "sort_order": 120,
        },
        {
            "variable_key": "submitted_at",
            "label": "Data de envio",
            "description": "Momento em que a resposta foi enviada.",
            "value_type": "datetime",
            "sort_order": 130,
        },
        {
            "variable_key": "signed_at",
            "label": "Data de assinatura",
            "description": "Momento em que a resposta foi assinada.",
            "value_type": "datetime",
            "sort_order": 140,
        },
    ),
}


def default_template_variables() -> list[dict]:
    """Return a defensive copy of default variable definitions."""
    rows: list[dict] = []
    for document_type in PrintableDocumentType:
        for variable in COMMON_VARIABLES:
            rows.append({"document_type": document_type.value, **variable})
        for variable in DOMAIN_VARIABLES.get(document_type.value, ()):
            rows.append(
                {
                    "document_type": document_type.value,
                    "required_by_default": False,
                    "optional_by_default": False,
                    **variable,
                }
            )
    return deepcopy(rows)
