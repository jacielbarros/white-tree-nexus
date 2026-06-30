"""Relatório de Auditoria Interna como Documento Controlado (Feature 014, US6).

Consolida escopo/critérios/itens/constatações num snapshot imutável, reusando
`controlled_document_service` (versões + aprovação) e `signature_service` (assinatura opcional).
Gate duro de completude conforme FR-029.
"""

import hashlib
import json
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.internal_audit_model import (
    InternalAudit,
    InternalAuditChecklistItem,
    InternalAuditFinding,
    InternalAuditProgram,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import internal_audit_service as ia
from wtnapp.settings import AuditFindingStatus, AuditFindingType, Classification, DocStatus, DocType


def _now() -> datetime:
    return datetime.now(timezone.utc)


def build_snapshot(db: Session, ctx: OrgContext, audit: InternalAudit) -> dict:
    program = db.get(InternalAuditProgram, audit.program_id)
    items = (
        scoped_query(db, InternalAuditChecklistItem, ctx)
        .filter(InternalAuditChecklistItem.audit_id == audit.id)
        .order_by(InternalAuditChecklistItem.order_index.asc())
        .all()
    )
    findings = (
        scoped_query(db, InternalAuditFinding, ctx)
        .filter(InternalAuditFinding.audit_id == audit.id, InternalAuditFinding.status == AuditFindingStatus.active)
        .order_by(InternalAuditFinding.created_at.asc())
        .all()
    )
    item_snaps = [
        {
            "criterion": i.criterion,
            "target_type": i.target_type.value if i.target_type else None,
            "target_id": str(i.target_id) if i.target_id else None,
            "result": i.result.value,
            "note": i.note,
        }
        for i in items
    ]
    finding_snaps = [
        {
            "finding_type": f.finding_type.value,
            "title": f.title,
            "description": f.description,
            "target_type": f.target_type.value if f.target_type else None,
            "target_id": str(f.target_id) if f.target_id else None,
            "promotable": f.promotable,
            "evidence_count": len(ia.finding_evidence_links(db, ctx, f.id)),
        }
        for f in findings
    ]
    by_type = {t.value: sum(1 for f in findings if f.finding_type == t) for t in AuditFindingType}
    return {
        "audit_code": audit.code,
        "title": audit.title,
        "program": program.name if program else None,
        "scope": audit.scope,
        "criteria": audit.criteria,
        "auditor_member_id": str(audit.auditor_member_id),
        "period_start": audit.period_start.isoformat() if audit.period_start else None,
        "period_end": audit.period_end.isoformat() if audit.period_end else None,
        "checklist": item_snaps,
        "findings": finding_snaps,
        "findings_by_type": by_type,
        "summary": {"checklist_total": len(item_snaps), "findings_total": len(finding_snaps)},
    }


def _ensure_gate(db: Session, ctx: OrgContext, audit: InternalAudit) -> None:
    """FR-029: auditoria concluída e nenhum item de checklist pendente."""
    if not ia.can_approve_report(db, ctx, audit):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Relatório bloqueado: a auditoria deve estar concluída e sem itens de checklist pendentes.",
        )


def submit_review(db: Session, ctx: OrgContext, audit: InternalAudit) -> InternalAudit:
    _ensure_gate(db, ctx, audit)
    return cds.submit_review(db, audit)


def approve(
    db: Session,
    ctx: OrgContext,
    audit: InternalAudit,
    *,
    sign: bool,
    classification: Classification,
    next_review_at,
    change_nature: str,
) -> DocumentVersion:
    if audit.draft_status != DocStatus.in_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Envie o relatório para revisão antes de aprovar.")
    _ensure_gate(db, ctx, audit)
    snapshot = build_snapshot(db, ctx, audit)

    signature = None
    if sign:
        canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
        signature = {
            "signer_user_id": str(ctx.principal.user.id),
            "signer_name": ctx.principal.user.full_name or str(ctx.principal.user.id),
            "signed_at": _now().isoformat(),
            "content_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "algorithm": "sha256",
            "level": "advanced",
        }

    def _snapshot():
        snap = dict(snapshot)
        if signature:
            snap["signature"] = signature
        return snap

    version = cds.approve_document(
        db=db, artifact=audit, doc_type=DocType.internal_audit_report, actor_id=ctx.principal.user.id,
        classification=classification, next_review_at=next_review_at,
        change_nature=change_nature, snapshot_factory=_snapshot,
    )
    ia.log_event(db, ctx=ctx, entity_type="report", event_type="approved", audit_id=audit.id, entity_id=audit.id, details={"version_number": version.version_number, "signed": bool(signature)})
    return version
