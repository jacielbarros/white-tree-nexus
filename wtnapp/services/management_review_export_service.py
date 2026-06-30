"""Ata de Análise Crítica — PDF a partir do snapshot imutável da versão (reportlab).

Reflete exatamente o `content_snapshot` da `DocumentVersion` (mesmo padrão de `soa_export_service` e
`internal_audit_export_service`).
"""

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from wtnapp.models.document_version_model import DocumentVersion


def _section(story, styles, title: str, data: dict) -> None:
    story.append(Paragraph(title, styles["Heading3"]))
    if not data:
        story.append(Paragraph("—", styles["BodyText"]))
        return
    rows = [[Paragraph(str(k), styles["BodyText"]), Paragraph(str(v), styles["BodyText"])] for k, v in data.items()]
    t = Table(rows, colWidths=[55 * mm, 115 * mm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(t)
    story.append(Spacer(1, 4 * mm))


def render_pdf(version: DocumentVersion) -> bytes:
    snap = version.content_snapshot or {}
    styles = getSampleStyleSheet()
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title="Ata de Análise Crítica pela Direção")
    story: list = []

    story.append(Paragraph("Ata de Análise Crítica pela Direção (9.3)", styles["Title"]))
    story.append(Paragraph(snap.get("title", ""), styles["Heading2"]))
    meta = [
        ("Data da reunião", snap.get("review_date") or "—"),
        ("Versão", f"v{version.version_number} ({version.status.value if version.status else ''})"),
        ("Assinada", "Sim" if snap.get("signature") else "Não"),
    ]
    story.append(Table([[k, v] for k, v in meta], colWidths=[55 * mm, 115 * mm]))
    story.append(Spacer(1, 4 * mm))

    _section(story, styles, "Entradas", snap.get("inputs", {}))
    _section(story, styles, "Saídas / Decisões", snap.get("outputs", {}))

    doc.build(story)
    return buf.getvalue()
