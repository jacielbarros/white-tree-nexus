"""ReportLab renderer for printable previews and signed PDFs."""

from __future__ import annotations

import html
import time
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from wtnapp import settings
from wtnapp.models.print_document_model import PrintTemplateVersion


class DocumentRenderTimeout(RuntimeError):
    """Raised when PDF rendering exceeds the configured timeout."""


class DocumentRenderError(RuntimeError):
    """Raised when rendering fails before producing a valid PDF."""


def _pagesize_for_document(document_type: str | None) -> tuple[float, float]:
    pagesize = landscape(A4) if document_type in {"gap_report", "soa_report"} else A4
    return float(pagesize[0]), float(pagesize[1])


def extract_page_metrics(pdf: bytes, document_type: str | None) -> list[dict[str, Any]]:
    """Return stable page metrics for PDFs rendered by this service.

    ReportLab uses a single pagesize for each document type in this renderer. Counting page objects
    is enough for the controlled PDFs we generate and avoids adding another backend dependency.
    """
    width, height = _pagesize_for_document(document_type)
    page_count = max(1, pdf.count(b"/Type /Page") - pdf.count(b"/Type /Pages"))
    return [
        {"page_number": page, "width_points": width, "height_points": height, "rotation": 0}
        for page in range(1, page_count + 1)
    ]


def default_signature_placement(
    *,
    page_metrics: list[dict[str, Any]],
    policy: dict[str, Any],
) -> dict[str, Any]:
    if not page_metrics:
        raise DocumentRenderError("Metricas de pagina indisponiveis.")
    default_page = policy.get("default_page", "last")
    if default_page == "last":
        page = page_metrics[-1]
    else:
        page_number = int(default_page)
        page = next((p for p in page_metrics if int(p["page_number"]) == page_number), page_metrics[-1])
    margin = float(policy.get("default_margin_points", 36))
    width = float(policy.get("default_width_points", 180))
    height = float(policy.get("default_height_points", 54))
    page_width = float(page["width_points"])
    page_height = float(page["height_points"])
    anchor = str(policy.get("default_anchor", "bottom_right"))
    x = margin
    y = margin
    if "right" in anchor:
        x = page_width - width - margin
    if "top" in anchor:
        y = page_height - height - margin
    return {
        "page_number": int(page["page_number"]),
        "x_points": round(max(0, x), 2),
        "y_points": round(max(0, y), 2),
        "width_points": width,
        "height_points": height,
        "page_width_points": page_width,
        "page_height_points": page_height,
        "coordinate_system": "pdf_points_bottom_left",
        "origin": "template" if policy.get("default_page") not in (None, "last") else "default",
    }


def _draw_signature_seal(canvas, doc, signature_meta: dict[str, Any], placement: dict[str, Any] | None) -> None:
    if not placement or canvas.getPageNumber() != int(placement.get("page_number", 0)):
        return
    x = float(placement["x_points"])
    y = float(placement["y_points"])
    width = float(placement["width_points"])
    height = float(placement["height_points"])
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#13715f"))
    canvas.setFillColor(colors.HexColor("#f1fbf8"))
    canvas.roundRect(x, y, width, height, 5, stroke=1, fill=1)
    canvas.setFillColor(colors.HexColor("#10231f"))
    canvas.setFont("Helvetica-Bold", 7.5)
    canvas.drawString(x + 8, y + height - 13, "Assinatura eletronica interna")
    canvas.setFont("Helvetica", 6.6)
    signer = str(signature_meta.get("signer_name") or "Nao informado")[:42]
    signed_at = str(signature_meta.get("signed_at") or "")[:28]
    identifier = str(signature_meta.get("identifier") or "")[:42]
    canvas.drawString(x + 8, y + height - 25, signer)
    canvas.drawString(x + 8, y + height - 36, signed_at)
    canvas.drawString(x + 8, y + 8, identifier)
    canvas.restoreState()


def _escape(value: Any) -> str:
    if value is None:
        return "Nao informado"
    if isinstance(value, bool):
        return "Sim" if value else "Nao"
    return html.escape(str(value))


def _status_label(status: str | None) -> str:
    labels = {
        "not_filled": "Nao avaliado",
        "meets": "Atende",
        "partial": "Parcialmente atende",
        "not_meet": "Nao atende",
        "not_applicable": "N/A",
        "implemented": "Implementado",
        "in_progress": "Em andamento",
        "planned": "Planejado",
        "not_started": "Nao iniciado",
    }
    return labels.get(status or "", status or "Nao informado")


def _check_timeout(start: float) -> None:
    timeout = settings.DOCUMENT_RENDER_TIMEOUT_SECONDS
    if timeout <= 0:
        raise DocumentRenderTimeout("Tempo limite de renderizacao excedido.")
    if time.monotonic() - start > timeout:
        raise DocumentRenderTimeout("Tempo limite de renderizacao excedido.")


def _paragraph(text: Any, style) -> Paragraph:
    return Paragraph(_escape(text).replace("\n", "<br/>"), style)


def _small_table(rows: list[list[Any]], widths: list[float] | None = None) -> Table:
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("wtn-small-table")
    small.fontSize = 7.2
    small.leading = 8.4
    data = [[Paragraph(f"<b>{_escape(c)}</b>", small) for c in rows[0]]]
    data.extend([[Paragraph(_escape(c), small) for c in row] for row in rows[1:]])
    table = Table(data, repeatRows=1, colWidths=widths)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17352f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c7d7d2")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f8f6")]),
            ]
        )
    )
    return table


def _header_elements(
    *,
    title: str,
    variables: dict[str, Any],
    template_version: PrintTemplateVersion,
    is_preview: bool,
    signature_meta: dict[str, Any] | None,
):
    styles = getSampleStyleSheet()
    title_style = styles["Title"].clone("wtn-title")
    title_style.textColor = colors.HexColor("#10231f")
    subtitle = styles["BodyText"].clone("wtn-subtitle")
    subtitle.fontSize = 9
    subtitle.leading = 11
    badge = styles["BodyText"].clone("wtn-badge")
    badge.fontSize = 11
    badge.leading = 13
    badge.textColor = colors.HexColor("#b42318") if is_preview else colors.HexColor("#13715f")

    status = "NAO ASSINADO / PREVIEW" if is_preview else "ASSINADO ELETRONICAMENTE"
    elements = [
        Paragraph(_escape(title), title_style),
        Paragraph(f"<b>{status}</b>", badge),
        Paragraph(
            "Organizacao: <b>{}</b> &nbsp; Classificacao: <b>{}</b><br/>"
            "Gerado em: <b>{}</b> &nbsp; Template: <b>v{} / {}</b>".format(
                _escape(variables.get("organization_name")),
                _escape(variables.get("classification")),
                _escape(variables.get("generated_at")),
                template_version.version_number,
                _escape(template_version.content_hash[:12]),
            ),
            subtitle,
        ),
        Spacer(1, 5 * mm),
    ]
    if signature_meta:
        elements.append(
            Paragraph(
                "Identificador: <b>{}</b><br/>Assinado por: <b>{}</b> em <b>{}</b><br/>"
                "Hash do snapshot: <b>{}</b>".format(
                    _escape(signature_meta.get("identifier")),
                    _escape(signature_meta.get("signer_name")),
                    _escape(signature_meta.get("signed_at")),
                    _escape(signature_meta.get("pdf_hash")),
                ),
                subtitle,
            )
        )
        elements.append(Spacer(1, 5 * mm))
    return elements


def _render_context(elements: list, source: dict[str, Any], styles) -> None:
    elements.append(Paragraph("Diagnostico", styles["Heading2"]))
    diagnostic = source.get("diagnostic", {})
    elements.append(_paragraph(diagnostic.get("sections") or "Nao informado", styles["BodyText"]))
    elements.append(Spacer(1, 4 * mm))

    analysis = source.get("analysis", {})
    elements.append(Paragraph("Analise de contexto", styles["Heading2"]))
    elements.append(_paragraph(analysis.get("intended_outcomes"), styles["BodyText"]))
    if analysis.get("issues"):
        rows = [["Origem", "Categoria", "Descricao", "Impacto"]]
        rows.extend(
            [
                item.get("origin"),
                item.get("category"),
                item.get("description"),
                item.get("impact"),
            ]
            for item in analysis["issues"]
        )
        elements.append(_small_table(rows))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Partes interessadas", styles["Heading2"]))
    rows = [["Parte", "Tipo", "Poder", "Interesse", "Estrategia"]]
    rows.extend(
        [
            item.get("name"),
            item.get("type"),
            item.get("power"),
            item.get("interest"),
            item.get("strategy"),
        ]
        for item in source.get("stakeholders", [])
    )
    elements.append(_small_table(rows))
    elements.append(Spacer(1, 4 * mm))

    scope = source.get("scope", {})
    elements.append(Paragraph("Escopo do SGSI", styles["Heading2"]))
    elements.append(_paragraph(scope.get("interfaces_dependencies"), styles["BodyText"]))
    rows = [["Tipo", "Descricao", "Justificativa"]]
    rows.extend(
        [item.get("kind"), item.get("description"), item.get("justification")]
        for item in scope.get("items", [])
    )
    elements.append(_small_table(rows))


def _render_gap(elements: list, source: dict[str, Any], styles) -> None:
    dashboard = source.get("assessment", {}).get("dashboard", {})
    elements.append(Paragraph("Resumo de aderencia", styles["Heading2"]))
    rows = [["Indicador", "Valor"]]
    rows.extend(
        [
            ["Aderencia geral", dashboard.get("overall_adherence")],
            ["Completude", dashboard.get("completeness")],
            ["Distribuicao", dashboard.get("status_distribution")],
        ]
    )
    elements.append(_small_table(rows, [55 * mm, 210 * mm]))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Matriz de controles", styles["Heading2"]))
    rows = [["Ref.", "Controle", "Status", "Prioridade", "Responsavel", "Evidencias esperadas"]]
    for item in source.get("items", []):
        rows.append(
            [
                item.get("ref_code"),
                item.get("name"),
                _status_label(item.get("status")),
                item.get("priority"),
                item.get("responsible"),
                "; ".join(item.get("guidance", {}).get("expected_evidence") or []),
            ]
        )
    elements.append(_small_table(rows, [18 * mm, 58 * mm, 28 * mm, 25 * mm, 34 * mm, 90 * mm]))


def _render_soa(elements: list, source: dict[str, Any], styles) -> None:
    summary = source.get("summary", {})
    elements.append(Paragraph("Resumo", styles["Heading2"]))
    rows = [["Total", "Aplicaveis", "Nao aplicaveis"]]
    rows.append([summary.get("total"), summary.get("applicable"), summary.get("not_applicable")])
    elements.append(_small_table(rows, [40 * mm, 40 * mm, 40 * mm]))
    elements.append(Spacer(1, 4 * mm))

    elements.append(Paragraph("Controles da SoA", styles["Heading2"]))
    rows = [["Ref.", "Controle", "Aplicavel", "Status", "Responsavel", "Evidencias"]]
    for item in source.get("items", []):
        rows.append(
            [
                item.get("ref_code"),
                item.get("name"),
                "Sim" if item.get("applicable") else "Nao",
                _status_label(item.get("implementation_status")),
                item.get("responsible"),
                item.get("evidence_refs") or item.get("expected_evidence"),
            ]
        )
    elements.append(_small_table(rows, [20 * mm, 72 * mm, 22 * mm, 32 * mm, 36 * mm, 72 * mm]))


def render_pdf(
    *,
    template_version: PrintTemplateVersion,
    snapshot: dict[str, Any],
    variables: dict[str, Any],
    is_preview: bool,
    signature_meta: dict[str, Any] | None = None,
    signature_placement: dict[str, Any] | None = None,
) -> bytes:
    start = time.monotonic()
    title = str(variables.get("document_title") or template_version.layout_schema.get("title") or "Documento SGSI")
    document_type = snapshot.get("document_type")
    pagesize = landscape(A4) if document_type in {"gap_report", "soa_report"} else A4
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=pagesize,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="WTNMuted", parent=styles["BodyText"], fontSize=8, textColor=colors.grey))
    elements = _header_elements(
        title=title,
        variables=variables,
        template_version=template_version,
        is_preview=is_preview,
        signature_meta=signature_meta,
    )
    source = snapshot.get("source", {})
    try:
        if document_type == "context_report":
            _render_context(elements, source, styles)
        elif document_type == "gap_report":
            _render_gap(elements, source, styles)
        elif document_type == "soa_report":
            _render_soa(elements, source, styles)
        else:
            elements.append(_paragraph(source, styles["BodyText"]))
        _check_timeout(start)
        if signature_meta and signature_placement:
            def _seal(canvas, built_doc):
                _draw_signature_seal(canvas, built_doc, signature_meta, signature_placement)

            doc.build(elements, onFirstPage=_seal, onLaterPages=_seal)
        else:
            doc.build(elements)
        _check_timeout(start)
    except DocumentRenderTimeout:
        raise
    except Exception as exc:
        raise DocumentRenderError("Nao foi possivel renderizar o PDF.") from exc
    return buf.getvalue()
