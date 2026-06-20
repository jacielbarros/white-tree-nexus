"""Motor de workflow de preenchimento — maquina de estados, snapshot, token, eventos.

Cada transicao:
1. Valida que a transicao e permitida (409 se invalida).
2. Atualiza o status da atribuicao.
3. Grava um FormAssignmentEvent (append-only).
4. Chama AuditService.log_from_request (sem PII/token/respostas).
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.models.form_template_model import FormTemplate
from wtnapp.services.audit_service import AuditService
from wtnapp.services import notification_service
from wtnapp.settings import (
    AssignmentEventType,
    AssignmentStatus,
    AuditOutcome,
    FORM_TOKEN_EXPIRY_DAYS,
)

if TYPE_CHECKING:
    from wtnapp.helpers.tenant_scope import OrgContext

logger = logging.getLogger(__name__)

# Transicoes validas da maquina de estados
VALID_TRANSITIONS: dict[AssignmentStatus, set[AssignmentStatus]] = {
    AssignmentStatus.draft: {AssignmentStatus.pending, AssignmentStatus.cancelled},
    AssignmentStatus.pending: {AssignmentStatus.in_progress, AssignmentStatus.cancelled},
    AssignmentStatus.in_progress: {AssignmentStatus.submitted, AssignmentStatus.cancelled},
    AssignmentStatus.submitted: {
        AssignmentStatus.in_progress,
        AssignmentStatus.signed,
        AssignmentStatus.cancelled,
    },
    AssignmentStatus.signed: {AssignmentStatus.completed, AssignmentStatus.cancelled},
    AssignmentStatus.completed: set(),
    AssignmentStatus.cancelled: set(),
    AssignmentStatus.returned: set(),
}

_FINAL_STATUSES = {AssignmentStatus.completed, AssignmentStatus.cancelled}


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def generate_respondent_token() -> tuple[str, str, datetime]:
    """Retorna (plain_token, token_hash, expires_at). Nunca persistir o plain_token."""
    plain = secrets.token_bytes(32).hex()
    token_hash = _hash_token(plain)
    expires_at = datetime.now(timezone.utc) + timedelta(days=FORM_TOKEN_EXPIRY_DAYS)
    return plain, token_hash, expires_at


def resolve_by_token(db: Session, token: str) -> tuple[FormAssignment | None, bool]:
    """Resolve atribuicao pelo token. Retorna (assignment, is_expired).

    Retorna (None, False) se nao encontrado; (assignment, True) se expirado.
    """
    token_hash = _hash_token(token)
    assignment = db.query(FormAssignment).filter(
        FormAssignment.respondent_token_hash == token_hash
    ).first()
    if assignment is None:
        return None, False
    now = datetime.now(timezone.utc)
    if assignment.token_expires_at is not None:
        exp = assignment.token_expires_at
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if now > exp:
            return assignment, True
    return assignment, False


def _record_event(
    db: Session,
    assignment: FormAssignment,
    event_type: AssignmentEventType,
    actor_user_id=None,
    actor_label: str | None = None,
    note: str | None = None,
) -> FormAssignmentEvent:
    evt = FormAssignmentEvent(
        tenant_id=assignment.tenant_id,
        assignment_id=assignment.id,
        event=event_type,
        actor_user_id=actor_user_id,
        actor_label=actor_label,
        note=note,
    )
    db.add(evt)
    return evt


def _transition(
    db: Session,
    assignment: FormAssignment,
    new_status: AssignmentStatus,
    event_type: AssignmentEventType,
    actor_user_id=None,
    actor_label: str | None = None,
    note: str | None = None,
    request: Request | None = None,
) -> FormAssignment:
    allowed = VALID_TRANSITIONS.get(assignment.status, set())
    if new_status not in allowed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Transicao invalida: {assignment.status.value} → {new_status.value}.",
        )
    assignment.status = new_status
    _record_event(db, assignment, event_type, actor_user_id=actor_user_id,
                  actor_label=actor_label, note=note)
    db.commit()
    db.refresh(assignment)
    if request:
        AuditService.log_from_request(
            request=request,
            operation=event_type.value.upper(),
            outcome=AuditOutcome.success,
            actor_user_id=actor_user_id,
            tenant_id=assignment.tenant_id,
            entity_type="form_assignment",
            entity_id=str(assignment.id),
        )
    return assignment


def validate_mandatory_fields(snapshot: list, answers: dict) -> list[str]:
    """Retorna lista de chaves de campos obrigatorios nao preenchidos."""
    missing = []
    for section in snapshot or []:
        for field in section.get("campos", []) if isinstance(section, dict) else []:
            if not isinstance(field, dict):
                continue
            if field.get("obrigatorio") or field.get("required"):
                chave = field.get("chave") or field.get("key", "")
                if not chave:
                    continue
                val = answers.get(chave)
                if val is None or val == "" or val is False:
                    missing.append(chave)
    return missing


def create_assignment(
    db: Session,
    create_data,
    ctx: "OrgContext",
    request: Request,
) -> tuple[FormAssignment, str | None]:
    """Cria uma FormAssignment, congela snapshot do template, gera token se externo.

    Retorna (assignment, plain_token_or_none).
    """
    template = db.query(FormTemplate).filter(
        FormTemplate.id == create_data.template_id,
        FormTemplate.tenant_id == ctx.tenant_id,
    ).first()
    if template is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template nao encontrado.")
    if template.status.value == "archived":
        raise HTTPException(status.HTTP_409_CONFLICT, "Nao e possivel atribuir um template arquivado.")

    now = datetime.now(timezone.utc)
    plain_token = None
    token_hash = None
    expires_at = None

    if create_data.respondent_email:
        plain_token, token_hash, expires_at = generate_respondent_token()

    assignment = FormAssignment(
        tenant_id=ctx.tenant_id,
        template_id=template.id,
        kind=template.kind,
        title=template.title,
        fields_snapshot=list(template.schema or []),
        instructions=create_data.instructions,
        status=AssignmentStatus.pending,
        respondent_user_id=create_data.respondent_user_id,
        respondent_email=create_data.respondent_email,
        respondent_name=create_data.respondent_name,
        respondent_token_hash=token_hash,
        token_expires_at=expires_at,
        deadline_at=create_data.deadline_at,
        answers={},
        assigned_by=ctx.principal.user.id,
        assigned_at=now,
    )
    db.add(assignment)
    db.flush()

    _record_event(db, assignment, AssignmentEventType.assigned,
                  actor_user_id=ctx.principal.user.id)

    db.commit()
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="CREATE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
        entity_type="form_assignment",
        entity_id=str(assignment.id),
        details={"kind": template.kind.value, "external": plain_token is not None},
    )

    # Notificacao best-effort (fail-soft)
    _send_assignment_notification(assignment, plain_token)

    return assignment, plain_token


def _send_assignment_notification(assignment: FormAssignment, plain_token: str | None) -> None:
    try:
        if plain_token:
            notification_service.send_form_assignment_email(
                to_email=assignment.respondent_email,
                assignment_title=assignment.title,
                token=plain_token,
            )
        elif assignment.respondent_email:
            notification_service.send_form_assignment_email(
                to_email=assignment.respondent_email,
                assignment_title=assignment.title,
            )
    except Exception:
        logger.warning("Falha ao enviar email de atribuicao (best-effort)", exc_info=True)


def claim(
    db: Session,
    assignment: FormAssignment,
    ctx: "OrgContext",
    request: Request,
) -> FormAssignment:
    """pending → in_progress. Apenas o respondent_user_id designado pode assumir."""
    if assignment.respondent_user_id != ctx.principal.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o preenchedor designado pode assumir.")
    now = datetime.now(timezone.utc)
    assignment.claimed_at = now
    assignment = _transition(
        db, assignment, AssignmentStatus.in_progress, AssignmentEventType.claimed,
        actor_user_id=ctx.principal.user.id, request=request,
    )
    return assignment


def save_answers(
    db: Session,
    assignment: FormAssignment,
    answers: dict,
    actor_user_id=None,
    request: Request | None = None,
) -> FormAssignment:
    """Salva respostas parciais (retomavel). Apenas em in_progress."""
    if assignment.status != AssignmentStatus.in_progress:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Respostas so podem ser salvas em preenchimento.")
    assignment.answers = {**assignment.answers, **answers}
    _record_event(db, assignment, AssignmentEventType.saved, actor_user_id=actor_user_id)
    db.commit()
    db.refresh(assignment)
    return assignment


def submit(
    db: Session,
    assignment: FormAssignment,
    actor_user_id=None,
    request: Request | None = None,
) -> FormAssignment:
    """in_progress → submitted. Valida campos obrigatorios."""
    missing = validate_mandatory_fields(assignment.fields_snapshot, assignment.answers)
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Campos obrigatorios nao preenchidos: {', '.join(missing)}",
        )
    now = datetime.now(timezone.utc)
    assignment.submitted_at = now
    return _transition(
        db, assignment, AssignmentStatus.submitted, AssignmentEventType.submitted,
        actor_user_id=actor_user_id, request=request,
    )


def return_assignment(
    db: Session,
    assignment: FormAssignment,
    reason: str | None,
    ctx: "OrgContext",
    request: Request,
) -> FormAssignment:
    """submitted → in_progress (devolucao com motivo)."""
    return _transition(
        db, assignment, AssignmentStatus.in_progress, AssignmentEventType.returned,
        actor_user_id=ctx.principal.user.id, note=reason, request=request,
    )


def cancel(
    db: Session,
    assignment: FormAssignment,
    ctx: "OrgContext",
    request: Request,
) -> FormAssignment:
    """Qualquer status nao-final → cancelled."""
    if assignment.status in _FINAL_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT, "Atribuicao ja finalizada.")
    return _transition(
        db, assignment, AssignmentStatus.cancelled, AssignmentEventType.cancelled,
        actor_user_id=ctx.principal.user.id, request=request,
    )


def remind(
    db: Session,
    assignment: FormAssignment,
    ctx: "OrgContext",
    request: Request,
) -> None:
    """Envia lembrete por email (best-effort)."""
    _record_event(db, assignment, AssignmentEventType.reminded,
                  actor_user_id=ctx.principal.user.id)
    db.commit()

    try:
        to_email = assignment.respondent_email
        if not to_email and assignment.respondent_user_id:
            # Busca o email do usuario (importado aqui para evitar ciclo)
            from wtnapp.models.user_model import User
            user = db.get(User, assignment.respondent_user_id)
            if user:
                to_email = user.email
        if to_email:
            notification_service.send_form_reminder_email(
                to_email=to_email, assignment_title=assignment.title
            )
    except Exception:
        logger.warning("Falha ao enviar lembrete (best-effort)", exc_info=True)

    AuditService.log_from_request(
        request=request,
        operation="REMIND",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=assignment.tenant_id,
        entity_type="form_assignment",
        entity_id=str(assignment.id),
    )
