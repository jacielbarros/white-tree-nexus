"""Relatório de Auditoria Interna — PDF a partir do snapshot imutável da versão (reportlab).

Reflete exatamente o `content_snapshot` da `DocumentVersion` (não o rascunho). reportlab é
pure-Python — adequado ao ambiente do projeto (mesmo padrão de `soa_export_service`).
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from wtnapp.models.document_version_model import DocumentVersion

_FINDING_LABELS = {
    "conforme": "Conforme",
    "nc_maior": "Não conformidade maior",
    "nc_menor": "Não conformidade menor",
    "oportunidade_melhoria": "Oportunidade de melhoria",
    "observacao": "Observação",
}
_RESULT_LABELS = {
    "conforme": "Conforme",
    "nao_conforme": "Não conforme",
    "nao_aplicavel": "Não aplicável",
    "pendente": "Pendente",
}


def render_pdf(version: DocumentVersion) -> bytes:
    snap = version.content_snapshot or {}
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=f"Relatório de Auditoria {snap.get('audit_code', '')}")
    story: list = []

    story.append(Paragraph(f"Relatório de Auditoria Interna — {snap.get('audit_code', '')}", styles["Title"]))
    story.append(Paragraph(snap.get("title", ""), styles["Heading2"]))
    story.append(Spacer(1, 4 * mm))

    meta = [
        ("Programa", snap.get("program") or "—"),
        ("Período", f"{snap.get('period_start') or '—'} a {snap.get('period_end') or '—'}"),
        ("Versão", f"v{version.version_number} ({version.status.value if version.status else ''})"),
        ("Assinado", "Sim" if snap.get("signature") else "Não"),
    ]
    story.append(Table([[k, v] for k, v in meta], colWidths=[40 * mm, 130 * mm]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Escopo", styles["Heading3"]))
    story.append(Paragraph(snap.get("scope", "") or "—", styles["BodyText"]))
    story.append(Paragraph("Critérios", styles["Heading3"]))
    story.append(Paragraph(snap.get("criteria", "") or "—", styles["BodyText"]))
    story.append(Spacer(1, 4 * mm))

    # Resumo de constatações por tipo
    by_type = snap.get("findings_by_type", {})
    if by_type:
        story.append(Paragraph("Constatações por tipo", styles["Heading3"]))
        rows = [["Tipo", "Qtde"]] + [[_FINDING_LABELS.get(k, k), str(v)] for k, v in by_type.items()]
        t = Table(rows, colWidths=[120 * mm, 30 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # Checklist
    checklist = snap.get("checklist", [])
    story.append(Paragraph(f"Itens auditados ({len(checklist)})", styles["Heading3"]))
    if checklist:
        rows = [["Critério", "Resultado"]] + [
            [Paragraph(i.get("criterion", ""), styles["BodyText"]), _RESULT_LABELS.get(i.get("result"), i.get("result", ""))]
            for i in checklist
        ]
        t = Table(rows, colWidths=[140 * mm, 30 * mm])
        t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecf0f1"))]))
        story.append(t)
    story.append(Spacer(1, 4 * mm))

    # Constatações detalhadas
    findings = snap.get("findings", [])
    story.append(Paragraph(f"Constatações ({len(findings)})", styles["Heading3"]))
    for f in findings:
        tag = _FINDING_LABELS.get(f.get("finding_type"), f.get("finding_type", ""))
        promo = " · promovível a NC" if f.get("promotable") else ""
        ev = f" · {f.get('evidence_count', 0)} evidência(s)" if f.get("evidence_count") else ""
        story.append(Paragraph(f"<b>[{tag}]</b> {f.get('title', '')}{promo}{ev}", styles["BodyText"]))
        story.append(Paragraph(f.get("description", "") or "", styles["BodyText"]))
        story.append(Spacer(1, 2 * mm))

    doc.build(story)
    return buf.getvalue()
