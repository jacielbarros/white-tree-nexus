"""Lógica da Auditoria Interna (Feature 014, Fase 2): programas, auditorias, checklist e
constatações. Máquina de estados e gate de completude do relatório."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.evidence_model import EvidenceLink
from wtnapp.models.gap_assessment_model import GapAssessmentItem
from wtnapp.models.internal_audit_model import (
    InternalAudit,
    InternalAuditChecklistItem,
    InternalAuditEvent,
    InternalAuditFinding,
    InternalAuditProgram,
)
from wtnapp.models.membership_model import Membership
from wtnapp.models.soa_model import SoaItem
from wtnapp.settings import (
    AUDIT_CODE_PREFIX,
    AuditChecklistResult,
    AuditFindingStatus,
    AuditFindingType,
    AuditOutcome,
    InternalAuditStatus,
    MembershipStatus,
    PROMOTABLE_FINDING_TYPES,
    SgsiArtifactType,
)

# Transições válidas do ciclo de vida da auditoria.
_TRANSITIONS = {
    (InternalAuditStatus.planned, "start"): InternalAuditStatus.in_progress,
    (InternalAuditStatus.in_progress, "complete"): InternalAuditStatus.completed,
    (InternalAuditStatus.planned, "cancel"): InternalAuditStatus.cancelled,
    (InternalAuditStatus.in_progress, "cancel"): InternalAuditStatus.cancelled,
}

# Alvos válidos para checklist/constatação (controle/cláusula/risco).
_AUDIT_TARGETS = {SgsiArtifactType.soa_item, SgsiArtifactType.gap_item, SgsiArtifactType.risk}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_event(
    db: Session,
    *,
    ctx: OrgContext,
    entity_type: str,
    event_type: str,
    audit_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    outcome: AuditOutcome = AuditOutcome.success,
    details: dict | None = None,
) -> None:
    db.add(
        InternalAuditEvent(
            tenant_id=ctx.tenant_id,
            audit_id=audit_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            outcome=outcome.value,
            actor_id=ctx.principal.user.id,
            details=details or {},
        )
    )


# ───────────────────────────── Programa ─────────────────────────────

def get_program(db: Session, ctx: OrgContext, program_id: uuid.UUID) -> InternalAuditProgram:
    program = scoped_query(db, InternalAuditProgram, ctx).filter(InternalAuditProgram.id == program_id).first()
    if program is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return program


# ───────────────────────────── Auditoria ─────────────────────────────

def _next_code(db: Session, ctx: OrgContext) -> str:
    count = scoped_query(db, InternalAudit, ctx).count()
    return f"{AUDIT_CODE_PREFIX}{count + 1:04d}"


def _validate_member(db: Session, ctx: OrgContext, member_id: uuid.UUID) -> None:
    membership = (
        db.query(Membership)
        .filter(
            Membership.tenant_id == ctx.tenant_id,
            Membership.user_id == member_id,
            Membership.status == MembershipStatus.active,
        )
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Auditor deve ser membro ativo da organizacao.")


def get_audit(db: Session, ctx: OrgContext, audit_id: uuid.UUID) -> InternalAudit:
    audit = scoped_query(db, InternalAudit, ctx).filter(InternalAudit.id == audit_id).first()
    if audit is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return audit


def create_audit(db: Session, ctx: OrgContext, *, program_id, title, scope, criteria, auditor_member_id, period_start, period_end) -> InternalAudit:
    get_program(db, ctx, program_id)  # valida tenant
    _validate_member(db, ctx, auditor_member_id)
    audit = InternalAudit(
        tenant_id=ctx.tenant_id,
        program_id=program_id,
        code=_next_code(db, ctx),
        title=title,
        scope=scope,
        criteria=criteria,
        auditor_member_id=auditor_member_id,
        period_start=period_start,
        period_end=period_end,
        status=InternalAuditStatus.planned,
        created_by=ctx.principal.user.id,
    )
    db.add(audit)
    db.flush()
    log_event(db, ctx=ctx, entity_type="audit", event_type="created", audit_id=audit.id, entity_id=audit.id)
    return audit


def transition_audit(db: Session, ctx: OrgContext, audit: InternalAudit, action: str) -> InternalAudit:
    new_status = _TRANSITIONS.get((audit.status, action))
    if new_status is None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Transicao invalida de '{audit.status.value}' por '{action}'.")
    audit.status = new_status
    log_event(db, ctx=ctx, entity_type="audit", event_type="status_changed", audit_id=audit.id, entity_id=audit.id, details={"to": new_status.value})
    return audit


def pending_items(db: Session, ctx: OrgContext, audit_id: uuid.UUID) -> int:
    return (
        scoped_query(db, InternalAuditChecklistItem, ctx)
        .filter(
            InternalAuditChecklistItem.audit_id == audit_id,
            InternalAuditChecklistItem.result == AuditChecklistResult.pendente,
        )
        .count()
    )


def findings_count(db: Session, ctx: OrgContext, audit_id: uuid.UUID) -> int:
    return (
        scoped_query(db, InternalAuditFinding, ctx)
        .filter(
            InternalAuditFinding.audit_id == audit_id,
            InternalAuditFinding.status == AuditFindingStatus.active,
        )
        .count()
    )


def can_approve_report(db: Session, ctx: OrgContext, audit: InternalAudit) -> bool:
    """Gate duro: auditoria concluída e nenhum item de checklist pendente (FR-029)."""
    return audit.status == InternalAuditStatus.completed and pending_items(db, ctx, audit.id) == 0


# ───────────────────────────── Checklist ─────────────────────────────

def _validate_target(db: Session, ctx: OrgContext, target_type, target_id) -> None:
    if target_type is None and target_id is None:
        return
    if target_type is None or target_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe tipo e id do alvo, ou nenhum.")
    if target_type not in _AUDIT_TARGETS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Alvo invalido para auditoria.")
    from wtnapp.services.evidence_service import target_exists  # noqa: PLC0415

    if not target_exists(db, ctx, target_type, target_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


def add_checklist_item(db: Session, ctx: OrgContext, audit: InternalAudit, data) -> InternalAuditChecklistItem:
    _validate_target(db, ctx, data.target_type, data.target_id)
    item = InternalAuditChecklistItem(
        tenant_id=ctx.tenant_id,
        audit_id=audit.id,
        target_type=data.target_type,
        target_id=data.target_id,
        criterion=data.criterion,
        result=data.result,
        note=data.note,
        order_index=data.order_index,
        created_by=ctx.principal.user.id,
    )
    db.add(item)
    db.flush()
    log_event(db, ctx=ctx, entity_type="checklist_item", event_type="created", audit_id=audit.id, entity_id=item.id)
    return item


def get_checklist_item(db: Session, ctx: OrgContext, audit_id: uuid.UUID, item_id: uuid.UUID) -> InternalAuditChecklistItem:
    item = (
        scoped_query(db, InternalAuditChecklistItem, ctx)
        .filter(InternalAuditChecklistItem.id == item_id, InternalAuditChecklistItem.audit_id == audit_id)
        .first()
    )
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return item


def update_checklist_item(db: Session, ctx: OrgContext, item: InternalAuditChecklistItem, *, result, note) -> InternalAuditChecklistItem:
    item.result = result
    if note is not None:
        item.note = note
    log_event(db, ctx=ctx, entity_type="checklist_item", event_type="updated", audit_id=item.audit_id, entity_id=item.id, details={"result": result.value})
    return item


def import_checklist(db: Session, ctx: OrgContext, audit: InternalAudit, source: str, only_applicable: bool) -> list[InternalAuditChecklistItem]:
    rows: list[InternalAuditChecklistItem] = []
    order = (
        scoped_query(db, InternalAuditChecklistItem, ctx)
        .filter(InternalAuditChecklistItem.audit_id == audit.id)
        .count()
    )
    if source == "soa":
        query = scoped_query(db, SoaItem, ctx)
        if only_applicable:
            query = query.filter(SoaItem.applicable.is_(True))
        for soa in query.all():
            label = f"{soa.ref_code} — {soa.name}" if soa.name else soa.ref_code
            rows.append(InternalAuditChecklistItem(
                tenant_id=ctx.tenant_id, audit_id=audit.id, target_type=SgsiArtifactType.soa_item,
                target_id=soa.id, criterion=label, created_by=ctx.principal.user.id, order_index=order,
            ))
            order += 1
    elif source == "gap":
        for gap in scoped_query(db, GapAssessmentItem, ctx).all():
            rows.append(InternalAuditChecklistItem(
                tenant_id=ctx.tenant_id, audit_id=audit.id, target_type=SgsiArtifactType.gap_item,
                target_id=gap.id, criterion=f"Item do Gap {gap.id}", created_by=ctx.principal.user.id, order_index=order,
            ))
            order += 1
    for item in rows:
        db.add(item)
    db.flush()
    log_event(db, ctx=ctx, entity_type="checklist_item", event_type="imported", audit_id=audit.id, details={"source": source, "count": len(rows)})
    return rows


# ───────────────────────────── Constatações ─────────────────────────────

def get_finding(db: Session, ctx: OrgContext, finding_id: uuid.UUID, *, include_inactive: bool = False) -> InternalAuditFinding:
    query = scoped_query(db, InternalAuditFinding, ctx).filter(InternalAuditFinding.id == finding_id)
    if not include_inactive:
        query = query.filter(InternalAuditFinding.status == AuditFindingStatus.active)
    finding = query.first()
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return finding


def create_finding(db: Session, ctx: OrgContext, audit: InternalAudit, data) -> InternalAuditFinding:
    _validate_target(db, ctx, data.target_type, data.target_id)
    if data.checklist_item_id is not None:
        item = (
            scoped_query(db, InternalAuditChecklistItem, ctx)
            .filter(InternalAuditChecklistItem.id == data.checklist_item_id, InternalAuditChecklistItem.audit_id == audit.id)
            .first()
        )
        if item is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    finding = InternalAuditFinding(
        tenant_id=ctx.tenant_id,
        audit_id=audit.id,
        checklist_item_id=data.checklist_item_id,
        finding_type=data.finding_type,
        title=data.title,
        description=data.description,
        target_type=data.target_type,
        target_id=data.target_id,
        promotable=data.finding_type in PROMOTABLE_FINDING_TYPES,
        status=AuditFindingStatus.active,
        created_by=ctx.principal.user.id,
    )
    db.add(finding)
    db.flush()
    log_event(db, ctx=ctx, entity_type="finding", event_type="created", audit_id=audit.id, entity_id=finding.id, details={"type": data.finding_type.value, "promotable": finding.promotable})
    return finding


def update_finding(db: Session, ctx: OrgContext, finding: InternalAuditFinding, data) -> InternalAuditFinding:
    _validate_target(db, ctx, data.target_type, data.target_id)
    finding.finding_type = data.finding_type
    finding.title = data.title
    finding.description = data.description
    finding.target_type = data.target_type
    finding.target_id = data.target_id
    finding.promotable = data.finding_type in PROMOTABLE_FINDING_TYPES
    log_event(db, ctx=ctx, entity_type="finding", event_type="updated", audit_id=finding.audit_id, entity_id=finding.id)
    return finding


def inactivate_finding(db: Session, ctx: OrgContext, finding: InternalAuditFinding) -> None:
    finding.status = AuditFindingStatus.inactive
    log_event(db, ctx=ctx, entity_type="finding", event_type="inactivated", audit_id=finding.audit_id, entity_id=finding.id)


def finding_evidence_links(db: Session, ctx: OrgContext, finding_id: uuid.UUID) -> list[EvidenceLink]:
    return (
        scoped_query(db, EvidenceLink, ctx)
        .filter(
            EvidenceLink.target_type == SgsiArtifactType.audit_finding,
            EvidenceLink.target_id == finding_id,
            EvidenceLink.active.is_(True),
        )
        .all()
    )
