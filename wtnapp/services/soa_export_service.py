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
_ORIGIN_LABELS = {
    "risk": "Tratamento de risco",
    "manual": "Inclusão manual",
    "risk+manual": "Risco + manual",
    "none": "—",
}
_KIND_LABELS = {
    "pre_soa": "Pré-SoA (consolidação do Gap)",
    "normative": "SoA normativa (6.1.3 d)",
}


def _fmt_reasons(reasons) -> str:
    return ", ".join(_REASON_LABELS.get(r, r) for r in (reasons or []))


def _fmt_risks(item: dict) -> str:
    """Riscos tratados estruturados (códigos de risk_links); fallback ao texto legado."""
    codes = [rl.get("risk_code") for rl in (item.get("risk_links") or []) if rl.get("risk_code")]
    if codes:
        return ", ".join(codes)
    return item.get("risks_treated") or ""


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
    kind_label = _KIND_LABELS.get(snapshot.get("soa_kind", "pre_soa"), snapshot.get("soa_kind"))
    elements.append(Paragraph(f"<b>{kind_label}</b>", styles["Heading2"]))
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
    head = ["Controle", "Aplicável", "Justificativa", "Origem", "Status impl.", "Responsável", "Riscos", "Evidências"]
    data = [[Paragraph(f"<b>{h}</b>", small) for h in head]]
    for it in items:
        applicable = it.get("applicable")
        if applicable:
            reasons = _fmt_reasons(it.get("inclusion_reasons"))
            note = it.get("inclusion_note")
            justif = f"{note} ({reasons})" if note and reasons else (note or reasons)
        else:
            justif = it.get("exclusion_justification") or ""
        origin = _ORIGIN_LABELS.get(it.get("origin"), "—") if applicable else "—"
        data.append([
            Paragraph(f"<b>{it.get('ref_code','')}</b><br/>{it.get('name','')}", small),
            Paragraph("Sim" if applicable else "Não", small),
            Paragraph(str(justif or ""), small),
            Paragraph(origin, small),
            Paragraph(_STATUS_LABELS.get(it.get("implementation_status"), it.get("implementation_status") or ""), small),
            Paragraph(it.get("responsible") or "", small),
            Paragraph(_fmt_risks(it), small),
            Paragraph(it.get("evidence_refs") or "", small),
        ])

    table = Table(data, repeatRows=1, colWidths=[48 * mm, 14 * mm, 60 * mm, 26 * mm, 24 * mm, 30 * mm, 26 * mm, 28 * mm])
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
