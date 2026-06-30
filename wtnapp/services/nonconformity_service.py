"""Lógica do domínio de Não Conformidades (Feature 015, 10.2).

NC + ações corretivas + verificação de eficácia, com máquina de estados, **gate de encerramento**
(verificação eficaz + zero ações em estado não terminal) e **promoção** idempotente de constatação
de auditoria (5a) — única escrita num módulo consumido (`internal_audit_finding.nonconformity_ref`).
"""

import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.internal_audit_model import InternalAuditFinding
from wtnapp.models.membership_model import Membership
from wtnapp.models.nonconformity_model import (
    CorrectiveAction,
    NonConformity,
    NonConformityEvent,
    NonConformityVerification,
)
from wtnapp.settings import (
    CORRECTIVE_ACTION_TERMINAL,
    AuditOutcome,
    CorrectiveActionStatus,
    FINDING_TO_NC_SEVERITY,
    MembershipStatus,
    NC_CODE_PREFIX,
    NCOrigin,
    NCSeverity,
    NCStatus,
    PROMOTABLE_FINDING_TYPES,
    VerificationResult,
)

# Transições válidas (o `close` é guardado pelo gate de encerramento).
_TRANSITIONS = {
    (NCStatus.open, "start"): NCStatus.in_progress,
    (NCStatus.in_progress, "send-verify"): NCStatus.in_verification,
    (NCStatus.in_verification, "close"): NCStatus.closed,
    (NCStatus.open, "cancel"): NCStatus.cancelled,
    (NCStatus.in_progress, "cancel"): NCStatus.cancelled,
    (NCStatus.in_verification, "cancel"): NCStatus.cancelled,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_event(
    db: Session,
    *,
    ctx: OrgContext,
    entity_type: str,
    event_type: str,
    nonconformity_id: uuid.UUID | None = None,
    entity_id: uuid.UUID | None = None,
    outcome: AuditOutcome = AuditOutcome.success,
    details: dict | None = None,
) -> None:
    db.add(
        NonConformityEvent(
            tenant_id=ctx.tenant_id,
            nonconformity_id=nonconformity_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            outcome=outcome.value,
            actor_id=ctx.principal.user.id,
            details=details or {},
        )
    )


def _validate_member(db: Session, ctx: OrgContext, member_id: uuid.UUID) -> None:
    membership = (
        db.query(Membership)
        .filter(Membership.tenant_id == ctx.tenant_id, Membership.user_id == member_id, Membership.status == MembershipStatus.active)
        .first()
    )
    if membership is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Responsavel deve ser membro ativo da organizacao.")


def _validate_target(db: Session, ctx: OrgContext, target_type, target_id) -> None:
    if target_type is None and target_id is None:
        return
    if target_type is None or target_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe tipo e id do alvo, ou nenhum.")
    from wtnapp.services.evidence_service import target_exists  # noqa: PLC0415

    if not target_exists(db, ctx, target_type, target_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


# ───────────────────────────── NC ─────────────────────────────

def _next_code(db: Session, ctx: OrgContext) -> str:
    count = scoped_query(db, NonConformity, ctx).count()
    return f"{NC_CODE_PREFIX}{count + 1:04d}"


def get_nc(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> NonConformity:
    nc = scoped_query(db, NonConformity, ctx).filter(NonConformity.id == nc_id).first()
    if nc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return nc


def create_nc(db: Session, ctx: OrgContext, data, *, origin=None, source_finding_id=None) -> NonConformity:
    _validate_target(db, ctx, data.target_type, data.target_id)
    nc = NonConformity(
        tenant_id=ctx.tenant_id,
        code=_next_code(db, ctx),
        origin=origin or data.origin,
        source_finding_id=source_finding_id,
        title=data.title,
        description=data.description,
        severity=data.severity,
        target_type=data.target_type,
        target_id=data.target_id,
        root_cause=data.root_cause,
        root_cause_method=data.root_cause_method,
        status=NCStatus.open,
        opened_by=ctx.principal.user.id,
    )
    db.add(nc)
    db.flush()
    log_event(db, ctx=ctx, entity_type="nonconformity", event_type="created", nonconformity_id=nc.id, entity_id=nc.id)
    return nc


def update_nc(db: Session, ctx: OrgContext, nc: NonConformity, data) -> NonConformity:
    _validate_target(db, ctx, data.target_type, data.target_id)
    nc.title = data.title
    nc.description = data.description
    nc.severity = data.severity
    nc.target_type = data.target_type
    nc.target_id = data.target_id
    nc.root_cause = data.root_cause
    nc.root_cause_method = data.root_cause_method
    log_event(db, ctx=ctx, entity_type="nonconformity", event_type="updated", nonconformity_id=nc.id, entity_id=nc.id)
    return nc


def promote_finding(db: Session, ctx: OrgContext, finding_id: uuid.UUID) -> tuple[NonConformity, bool]:
    """Promove uma constatação de auditoria (5a) a NC. Idempotente. Retorna (nc, created)."""
    finding = scoped_query(db, InternalAuditFinding, ctx).filter(InternalAuditFinding.id == finding_id).first()
    if finding is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    if finding.nonconformity_ref is not None:
        existing = get_nc(db, ctx, finding.nonconformity_ref)
        return existing, False
    if not finding.promotable:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Constatacao nao e promovivel a NC.")

    nc = NonConformity(
        tenant_id=ctx.tenant_id,
        code=_next_code(db, ctx),
        origin=NCOrigin.audit_finding,
        source_finding_id=finding.id,
        title=finding.title,
        description=finding.description,
        severity=FINDING_TO_NC_SEVERITY.get(finding.finding_type, NCSeverity.menor),
        target_type=finding.target_type,
        target_id=finding.target_id,
        status=NCStatus.open,
        opened_by=ctx.principal.user.id,
    )
    db.add(nc)
    db.flush()
    # Única escrita num módulo consumido: o ponteiro reservado pela 5a.
    finding.nonconformity_ref = nc.id
    log_event(db, ctx=ctx, entity_type="nonconformity", event_type="promoted", nonconformity_id=nc.id, entity_id=nc.id, details={"finding_id": str(finding.id)})
    return nc, True


def transition(db: Session, ctx: OrgContext, nc: NonConformity, action: str) -> NonConformity:
    new_status = _TRANSITIONS.get((nc.status, action))
    if new_status is None:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Transicao invalida de '{nc.status.value}' por '{action}'.")
    if action == "close" and not can_close(db, ctx, nc):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Encerramento bloqueado: exige verificacao de eficacia 'eficaz' e nenhuma acao corretiva em aberto.",
        )
    nc.status = new_status
    if new_status == NCStatus.closed:
        nc.closed_by = ctx.principal.user.id
        nc.closed_at = _now()
    log_event(db, ctx=ctx, entity_type="nonconformity", event_type="status_changed", nonconformity_id=nc.id, entity_id=nc.id, details={"to": new_status.value})
    return nc


# ───────────────────────────── Ações corretivas ─────────────────────────────

def list_actions(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> list[CorrectiveAction]:
    return (
        scoped_query(db, CorrectiveAction, ctx)
        .filter(CorrectiveAction.nonconformity_id == nc_id)
        .order_by(CorrectiveAction.created_at.asc())
        .all()
    )


def is_overdue(action: CorrectiveAction) -> bool:
    return action.due_date is not None and action.due_date < date.today() and action.status not in CORRECTIVE_ACTION_TERMINAL


def add_action(db: Session, ctx: OrgContext, nc: NonConformity, data) -> CorrectiveAction:
    _validate_member(db, ctx, data.responsible_member_id)
    action = CorrectiveAction(
        tenant_id=ctx.tenant_id, nonconformity_id=nc.id, description=data.description,
        responsible_member_id=data.responsible_member_id, due_date=data.due_date,
        status=data.status, created_by=ctx.principal.user.id,
    )
    db.add(action)
    db.flush()
    log_event(db, ctx=ctx, entity_type="corrective_action", event_type="action_added", nonconformity_id=nc.id, entity_id=action.id)
    return action


def get_action(db: Session, ctx: OrgContext, action_id: uuid.UUID) -> CorrectiveAction:
    action = scoped_query(db, CorrectiveAction, ctx).filter(CorrectiveAction.id == action_id).first()
    if action is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return action


def update_action(db: Session, ctx: OrgContext, action: CorrectiveAction, data) -> CorrectiveAction:
    _validate_member(db, ctx, data.responsible_member_id)
    action.description = data.description
    action.responsible_member_id = data.responsible_member_id
    action.due_date = data.due_date
    action.status = data.status
    log_event(db, ctx=ctx, entity_type="corrective_action", event_type="updated", nonconformity_id=action.nonconformity_id, entity_id=action.id)
    return action


def inactivate_action(db: Session, ctx: OrgContext, action: CorrectiveAction) -> None:
    action.status = CorrectiveActionStatus.cancelled
    log_event(db, ctx=ctx, entity_type="corrective_action", event_type="inactivated", nonconformity_id=action.nonconformity_id, entity_id=action.id)


# ───────────────────────────── Verificação de eficácia ─────────────────────────────

def list_verifications(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> list[NonConformityVerification]:
    return (
        scoped_query(db, NonConformityVerification, ctx)
        .filter(NonConformityVerification.nonconformity_id == nc_id)
        .order_by(NonConformityVerification.verified_at.desc())
        .all()
    )


def add_verification(db: Session, ctx: OrgContext, nc: NonConformity, data) -> NonConformityVerification:
    verification = NonConformityVerification(
        tenant_id=ctx.tenant_id, nonconformity_id=nc.id, result=data.result, notes=data.notes,
        verified_by=ctx.principal.user.id,
    )
    db.add(verification)
    db.flush()
    log_event(db, ctx=ctx, entity_type="verification", event_type="verified", nonconformity_id=nc.id, entity_id=verification.id, details={"result": data.result.value})
    return verification


def latest_verification(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> NonConformityVerification | None:
    return list_verifications(db, ctx, nc_id)[0] if list_verifications(db, ctx, nc_id) else None


# ───────────────────────────── Readiness / gate ─────────────────────────────

def open_actions(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> int:
    return sum(1 for a in list_actions(db, ctx, nc_id) if a.status not in CORRECTIVE_ACTION_TERMINAL)


def overdue_actions(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> int:
    return sum(1 for a in list_actions(db, ctx, nc_id) if is_overdue(a))


def has_effective_verification(db: Session, ctx: OrgContext, nc_id: uuid.UUID) -> bool:
    latest = latest_verification(db, ctx, nc_id)
    return latest is not None and latest.result == VerificationResult.effective


def can_close(db: Session, ctx: OrgContext, nc: NonConformity) -> bool:
    """FR-007: encerrar exige verificação mais recente 'eficaz' e zero ações em estado não terminal."""
    return has_effective_verification(db, ctx, nc.id) and open_actions(db, ctx, nc.id) == 0
