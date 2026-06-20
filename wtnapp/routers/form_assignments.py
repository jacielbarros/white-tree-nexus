"""Atribuicoes de formulario — ciclo de vida autenticado (T013, T026)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.models.form_signature_model import FormSignature
from wtnapp.schemas.form_assignment_schema import (
    AnswersUpdate,
    AssignmentCreate,
    AssignmentEventResponse,
    AssignmentResponse,
    ReturnRequest,
    SignatureResponse,
    VerifyResult,
)
from wtnapp.services import form_workflow_service as svc
from wtnapp.services import signature_service as sig_svc

router = APIRouter(prefix="/form-assignments", tags=["form-assignments"])

db_dep = Annotated[Session, Depends(get_db)]
assign_dep = Annotated[OrgContext, Depends(require_permission("assign_form"))]
fill_dep = Annotated[OrgContext, Depends(require_permission("fill_form"))]
sign_dep = Annotated[OrgContext, Depends(require_permission("sign_form"))]
view_dep = Annotated[OrgContext, Depends(require_permission("view_form"))]


def _get_assignment(assignment_id: uuid.UUID, ctx: OrgContext, db: Session) -> FormAssignment:
    obj = scoped_query(db, FormAssignment, ctx).filter(
        FormAssignment.id == assignment_id
    ).first()
    if obj is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuicao nao encontrada.")
    return obj


@router.post("", response_model=AssignmentResponse, status_code=status.HTTP_201_CREATED)
def create_assignment(
    body: AssignmentCreate,
    ctx: assign_dep,
    db: db_dep,
    request: Request,
):
    assignment, _token = svc.create_assignment(db, body, ctx, request)
    return assignment


@router.get("", response_model=list[AssignmentResponse])
def list_assignments(ctx: view_dep, db: db_dep):
    return scoped_query(db, FormAssignment, ctx).all()


@router.get("/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(assignment_id: uuid.UUID, ctx: view_dep, db: db_dep):
    return _get_assignment(assignment_id, ctx, db)


@router.post("/{assignment_id}/claim", response_model=AssignmentResponse)
def claim_assignment(
    assignment_id: uuid.UUID,
    ctx: fill_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    return svc.claim(db, assignment, ctx, request)


@router.put("/{assignment_id}/answers", response_model=AssignmentResponse)
def save_answers(
    assignment_id: uuid.UUID,
    body: AnswersUpdate,
    ctx: fill_dep,
    db: db_dep,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    # Apenas o preenchedor designado pode salvar respostas
    if assignment.respondent_user_id != ctx.principal.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o preenchedor designado pode salvar respostas.")
    return svc.save_answers(db, assignment, body.answers, actor_user_id=ctx.principal.user.id)


@router.post("/{assignment_id}/submit", response_model=AssignmentResponse)
def submit_assignment(
    assignment_id: uuid.UUID,
    ctx: fill_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    if assignment.respondent_user_id != ctx.principal.user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o preenchedor designado pode enviar.")
    return svc.submit(db, assignment, actor_user_id=ctx.principal.user.id, request=request)


@router.post("/{assignment_id}/return", response_model=AssignmentResponse)
def return_assignment(
    assignment_id: uuid.UUID,
    body: ReturnRequest,
    ctx: assign_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    return svc.return_assignment(db, assignment, body.reason, ctx, request)


@router.post("/{assignment_id}/cancel", response_model=AssignmentResponse)
def cancel_assignment(
    assignment_id: uuid.UUID,
    ctx: assign_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    return svc.cancel(db, assignment, ctx, request)


@router.post("/{assignment_id}/remind", status_code=status.HTTP_204_NO_CONTENT)
def remind(
    assignment_id: uuid.UUID,
    ctx: assign_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    svc.remind(db, assignment, ctx, request)


@router.post("/{assignment_id}/sign", response_model=SignatureResponse)
def sign_assignment(
    assignment_id: uuid.UUID,
    ctx: sign_dep,
    db: db_dep,
    request: Request,
):
    assignment = _get_assignment(assignment_id, ctx, db)
    return sig_svc.sign_as_member(db, assignment, ctx, request)


@router.get("/{assignment_id}/events", response_model=list[AssignmentEventResponse])
def list_events(assignment_id: uuid.UUID, ctx: view_dep, db: db_dep):
    _get_assignment(assignment_id, ctx, db)
    return db.query(FormAssignmentEvent).filter(
        FormAssignmentEvent.assignment_id == assignment_id
    ).order_by(FormAssignmentEvent.at).all()


@router.get("/{assignment_id}/signatures", response_model=list[SignatureResponse])
def list_signatures(assignment_id: uuid.UUID, ctx: view_dep, db: db_dep):
    _get_assignment(assignment_id, ctx, db)
    return db.query(FormSignature).filter(
        FormSignature.assignment_id == assignment_id
    ).order_by(FormSignature.signed_at).all()


@router.get("/{assignment_id}/verify", response_model=VerifyResult)
def verify_integrity(assignment_id: uuid.UUID, ctx: view_dep, db: db_dep):
    assignment = _get_assignment(assignment_id, ctx, db)
    result = sig_svc.verify_integrity(db, assignment)
    return result
