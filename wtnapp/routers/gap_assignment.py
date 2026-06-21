"""Gap Assignment router — condutor de análise gap atribuível (US5)."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.gap_assessment_model import GapAssessment
from wtnapp.models.gap_assignment_model import GapAssignment
from wtnapp.services.audit_service import AuditService

router = APIRouter(prefix="/gap/assignments", tags=["gap-assignments"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_gap"))]

_TOKEN_EXPIRY_HOURS = 72


# ── Schemas ───────────────────────────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    scope: str = "whole"
    scope_theme: str | None = None
    respondent_user_id: uuid.UUID | None = None
    respondent_email: str | None = None
    deadline_at: datetime | None = None
    instructions: str | None = None


class AssignmentResponse(BaseModel):
    id: uuid.UUID
    assessment_id: uuid.UUID
    scope: str
    scope_theme: str | None
    status: str
    respondent_user_id: uuid.UUID | None
    respondent_email: str | None
    deadline_at: datetime | None
    instructions: str | None
    claimed_at: datetime | None
    submitted_at: datetime | None
    signed_at: datetime | None
    created_at: datetime
    token: str | None = None

    class Config:
        from_attributes = True


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_assessment(db: Session, tenant_id: uuid.UUID) -> GapAssessment:
    a = db.query(GapAssessment).filter_by(tenant_id=tenant_id).first()
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliação não encontrada. Adote o catálogo primeiro.")
    return a


def _to_response(a: GapAssignment, token: str | None = None) -> AssignmentResponse:
    return AssignmentResponse(
        id=a.id,
        assessment_id=a.assessment_id,
        scope=a.scope,
        scope_theme=a.scope_theme,
        status=a.status,
        respondent_user_id=a.respondent_user_id,
        respondent_email=a.respondent_email,
        deadline_at=a.deadline_at,
        instructions=a.instructions,
        claimed_at=a.claimed_at,
        submitted_at=a.submitted_at,
        signed_at=a.signed_at,
        created_at=a.created_at,
        token=token,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("", response_model=list[AssignmentResponse])
def list_assignments(db: db_dep, ctx: view_dep, status_filter: str | None = None):
    assessment = _get_assessment(db, ctx.tenant_id)
    q = scoped_query(db, GapAssignment, ctx).filter(
        GapAssignment.assessment_id == assessment.id
    )
    if status_filter:
        q = q.filter(GapAssignment.status == status_filter)
    return [_to_response(a) for a in q.order_by(GapAssignment.created_at.desc()).all()]


@router.post("", response_model=AssignmentResponse, status_code=201)
def create_assignment(
    body: AssignmentCreate,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    assessment = _get_assessment(db, ctx.tenant_id)

    if body.respondent_user_id is None and body.respondent_email is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Informe respondent_user_id (membro) ou respondent_email (externo).",
        )
    if body.respondent_user_id is not None and body.respondent_email is not None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Informe respondent_user_id OU respondent_email, não ambos.",
        )

    plain_token: str | None = None
    token_hash: str | None = None
    expires: datetime | None = None

    if body.respondent_email and body.respondent_user_id is None:
        plain_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(hours=_TOKEN_EXPIRY_HOURS)

    assignment = GapAssignment(
        tenant_id=ctx.tenant_id,
        assessment_id=assessment.id,
        scope=body.scope,
        scope_theme=body.scope_theme,
        status="pending",
        respondent_user_id=body.respondent_user_id,
        respondent_email=body.respondent_email,
        respondent_token_hash=token_hash,
        token_expires_at=expires,
        deadline_at=body.deadline_at,
        instructions=body.instructions,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="CREATE",
        entity_type="gap_assignment",
        entity_id=str(assignment.id),
        details={"scope": body.scope, "has_external_token": plain_token is not None},
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _to_response(assignment, token=plain_token)


@router.post("/{assignment_id}/claim", response_model=AssignmentResponse)
def claim_assignment(
    assignment_id: uuid.UUID,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    """Membro assume a condução (status: pending → in_progress)."""
    assignment = scoped_query(db, GapAssignment, ctx).filter(
        GapAssignment.id == assignment_id
    ).first()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuição não encontrada.")
    if assignment.status != "pending":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Status atual: {assignment.status}. Apenas 'pending' pode ser assumido.",
        )

    assignment.status = "in_progress"
    assignment.claimed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="CLAIM",
        entity_type="gap_assignment",
        entity_id=str(assignment.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _to_response(assignment)


@router.post("/{assignment_id}/submit", response_model=AssignmentResponse)
def submit_assignment(
    assignment_id: uuid.UUID,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    """Condutor declara condução concluída (status: in_progress → submitted)."""
    assignment = scoped_query(db, GapAssignment, ctx).filter(
        GapAssignment.id == assignment_id
    ).first()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuição não encontrada.")
    if assignment.status != "in_progress":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Status atual: {assignment.status}. Apenas 'in_progress' pode ser enviado.",
        )

    assignment.status = "submitted"
    assignment.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="SUBMIT",
        entity_type="gap_assignment",
        entity_id=str(assignment.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _to_response(assignment)


@router.post("/{assignment_id}/cancel", response_model=AssignmentResponse)
def cancel_assignment(
    assignment_id: uuid.UUID,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    """Cancela atribuição (qualquer status não terminal)."""
    assignment = scoped_query(db, GapAssignment, ctx).filter(
        GapAssignment.id == assignment_id
    ).first()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuição não encontrada.")
    if assignment.status in ("cancelled", "submitted"):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Atribuição já em status terminal: {assignment.status}.",
        )

    assignment.status = "cancelled"
    db.commit()
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="CANCEL",
        entity_type="gap_assignment",
        entity_id=str(assignment.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _to_response(assignment)
