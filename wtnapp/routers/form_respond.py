"""Endpoints publicos para respondentes externos (token-based, T017)."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.limiter import limiter
from wtnapp.schemas.form_assignment_schema import (
    AnswersUpdate,
    AssignmentResponse,
    ExternalSignRequest,
    SignatureResponse,
)
from wtnapp.services import form_workflow_service as svc
from wtnapp.services import signature_service as sig_svc
from wtnapp import settings
from wtnapp.settings import AssignmentStatus

router = APIRouter(prefix="/forms/respond", tags=["form-respond"])

db_dep = Annotated[Session, Depends(get_db)]

_GONE = HTTPException(status.HTTP_410_GONE, "Link expirado ou invalido.")
_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Formulario nao encontrado.")


def _resolve(token: str, db: Session):
    assignment, is_expired = svc.resolve_by_token(db, token)
    if assignment is None:
        raise _NOT_FOUND
    if is_expired:
        raise _GONE
    return assignment


@router.get("/{token}", response_model=AssignmentResponse)
@limiter.limit(settings.RATE_LIMIT_FORM_TOKEN)
def get_form(token: str, db: db_dep, request: Request):
    """Retorna o formulario para o respondente externo (campos e instrucoes; sem respostas de outros)."""
    return _resolve(token, db)


@router.post("/{token}/claim", response_model=AssignmentResponse)
@limiter.limit(settings.RATE_LIMIT_FORM_TOKEN)
def claim_form(token: str, db: db_dep, request: Request):
    """Respondente externo assume o formulario (pending → in_progress)."""
    assignment = _resolve(token, db)
    if assignment.status == AssignmentStatus.pending:
        from datetime import datetime, timezone
        assignment.claimed_at = datetime.now(timezone.utc)
        assignment.status = AssignmentStatus.in_progress
        from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
        from wtnapp.settings import AssignmentEventType
        evt = FormAssignmentEvent(
            tenant_id=assignment.tenant_id,
            assignment_id=assignment.id,
            event=AssignmentEventType.claimed,
            actor_label=assignment.respondent_name or assignment.respondent_email,
        )
        db.add(evt)
        db.commit()
        db.refresh(assignment)
    elif assignment.status not in (AssignmentStatus.in_progress,):
        raise HTTPException(status.HTTP_409_CONFLICT, "Formulario nao pode ser assumido no status atual.")
    return assignment


@router.put("/{token}/answers", response_model=AssignmentResponse)
@limiter.limit(settings.RATE_LIMIT_FORM_TOKEN)
def save_answers(token: str, body: AnswersUpdate, db: db_dep, request: Request):
    """Salva respostas parciais — idempotente, retomavel."""
    assignment = _resolve(token, db)
    return svc.save_answers(db, assignment, body.answers)


@router.post("/{token}/submit", response_model=AssignmentResponse)
@limiter.limit(settings.RATE_LIMIT_FORM_TOKEN)
def submit_form(token: str, db: db_dep, request: Request):
    """Envia o formulario (in_progress → submitted). Valida campos obrigatorios."""
    assignment = _resolve(token, db)
    return svc.submit(db, assignment, request=request)


@router.post("/{token}/otp", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_FORM_OTP)
def request_otp(token: str, db: db_dep, request: Request):
    """Solicita OTP de assinatura por email (gate fail-closed)."""
    assignment = _resolve(token, db)
    sig_svc.request_otp(db, assignment, request=request)


@router.post("/{token}/sign", response_model=SignatureResponse)
@limiter.limit(settings.RATE_LIMIT_FORM_OTP)
def sign_form(token: str, body: ExternalSignRequest, db: db_dep, request: Request):
    """Assina o formulario com OTP (assinatura eletronica avancada)."""
    assignment = _resolve(token, db)
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return sig_svc.sign_as_external(
        db, assignment,
        otp=body.otp,
        signer_name=body.signer_name,
        ip=ip,
        user_agent=ua,
        request=request,
    )
