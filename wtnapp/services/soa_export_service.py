"""SoA — geração de PDF a partir do snapshot imutável de uma versão (reportlab).

O PDF reflete **exatamente** o `content_snapshot` da `DocumentVersion` selecionada (não o rascunho).
reportlab é pure-Python (sem libs nativas) — adequado ao ambiente Windows do projeto.
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from wtnapp.models.document_version_model import DocumentVersion

_STATUS_LABELS = {
    "implemented": "Implementado",
    "in_progress": "Em andamento",
    "planned": "Planejado",
    "not_started": "Não iniciado",
    "not_applicable": "Não aplicável",
}
_REASON_LABELS = {
    "risk_treatment": "Risco",
    "legal": "Legal",
    "contractual": "Contratual",
    "best_practice": "Boa prática",
}


def _fmt_reasons(reasons) -> str:
    return ", ".join(_REASON_LABELS.get(r, r) for r in (reasons or []))


def render_pdf(version: DocumentVersion) -> bytes:
    """Renderiza a SoA de uma versão emitida como PDF (bytes)."""
    snapshot = version.content_snapshot or {}
    items = snapshot.get("items", [])

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm,
        title=f"{version.identifier} v{version.version_number}",
    )
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small")
    small.fontSize = 7
    small.leading = 8
    elements = []

    # Cabeçalho do Documento Controlado
    elements.append(Paragraph("Declaração de Aplicabilidade (SoA) — ISO/IEC 27001:2022", styles["Title"]))
    signed = "Sim" if snapshot.get("signature") else "Não"
    emitted = version.emitted_at.strftime("%d/%m/%Y") if version.emitted_at else ""
    review = version.next_review_at.strftime("%d/%m/%Y") if version.next_review_at else "—"
    header = (
        f"<b>Documento:</b> {version.identifier} &nbsp; "
        f"<b>Versão:</b> {version.version_number} &nbsp; "
        f"<b>Classificação:</b> {version.classification.value} &nbsp; "
        f"<b>Status:</b> {version.status.value}<br/>"
        f"<b>Emitido em:</b> {emitted} &nbsp; "
        f"<b>Próxima análise:</b> {review} &nbsp; "
        f"<b>Assinada:</b> {signed}<br/>"
        f"<b>Natureza:</b> {version.change_nature}"
    )
    elements.append(Paragraph(header, styles["BodyText"]))
    elements.append(Spacer(1, 6 * mm))

    # Tabela de controles
    head = ["Controle", "Aplicável", "Justificativa", "Status impl.", "Responsável", "Riscos", "Evidências"]
    data = [[Paragraph(f"<b>{h}</b>", small) for h in head]]
    for it in items:
        applicable = it.get("applicable")
        justif = it.get("inclusion_note") or _fmt_reasons(it.get("inclusion_reasons")) if applicable \
            else (it.get("exclusion_justification") or "")
        data.append([
            Paragraph(f"<b>{it.get('ref_code','')}</b><br/>{it.get('name','')}", small),
            Paragraph("Sim" if applicable else "Não", small),
            Paragraph(str(justif or ""), small),
            Paragraph(_STATUS_LABELS.get(it.get("implementation_status"), it.get("implementation_status") or ""), small),
            Paragraph(it.get("responsible") or "", small),
            Paragraph(it.get("risks_treated") or "", small),
            Paragraph(it.get("evidence_refs") or "", small),
        ])

    table = Table(data, repeatRows=1, colWidths=[55 * mm, 16 * mm, 70 * mm, 26 * mm, 35 * mm, 30 * mm, 35 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bdc3c7")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f6f7")]),
    ]))
    elements.append(table)

    doc.build(elements)
    return buf.getvalue()
