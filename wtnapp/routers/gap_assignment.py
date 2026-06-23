"""Gap Assignment router — condutor de análise gap atribuível (US5)."""

import hashlib
import json
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import has_permission, require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_assignment_model import GapAssignment
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.schemas.gap_assessment_schema import BaselineResponse
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.audit_service import AuditService
from wtnapp.services.gap_metrics_service import compute_dashboard
from wtnapp.settings import Classification, DocStatus, DocType

router = APIRouter(prefix="/gap/assignments", tags=["gap-assignments"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_gap"))]
sign_dep = Annotated[OrgContext, Depends(require_permission("sign_form"))]

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


class AssignmentSignResponse(BaseModel):
    assignment: AssignmentResponse
    baseline: BaselineResponse
    content_hash: str
    hash_algorithm: str = "sha256"
    signed_at: datetime


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


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _date_value(value):
    return value.isoformat() if value is not None else None


def _canonicalize(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def _content_hash(payload: dict) -> str:
    return hashlib.sha256(_canonicalize(payload).encode("utf-8")).hexdigest()


def _baseline_response(version: DocumentVersion) -> BaselineResponse:
    dashboard = version.content_snapshot.get("dashboard", {}) if version.content_snapshot else {}
    return BaselineResponse(
        id=version.id,
        version_number=version.version_number,
        status=version.status.value,
        classification=version.classification.value,
        emitted_at=version.created_at,
        overall_adherence=dashboard.get("overall_adherence"),
    )


def _signed_content(
    db: Session,
    assignment: GapAssignment,
    assessment: GapAssessment,
    signed_at: datetime,
) -> dict:
    rows = (
        db.query(GapAssessmentItem, GapCatalogItem)
        .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
        .filter(GapAssessmentItem.assessment_id == assessment.id)
        .order_by(GapCatalogItem.order)
        .all()
    )
    items = []
    for item, catalog_item in rows:
        items.append({
            "id": str(item.id),
            "catalog_item_id": str(item.catalog_item_id),
            "ref_code": catalog_item.ref_code,
            "dimension": _enum_value(catalog_item.dimension),
            "theme": _enum_value(catalog_item.theme) if catalog_item.theme else None,
            "name": catalog_item.name,
            "status": _enum_value(item.status),
            "priority": _enum_value(item.priority) if item.priority else None,
            "findings": item.findings,
            "actions": item.actions,
            "responsible": item.responsible,
            "deadline": _date_value(item.deadline),
            "evidence_ref": item.evidence_ref,
            "notes": item.notes,
            "exclusion_justification": item.exclusion_justification,
            "maturity_level": item.maturity_level,
            "effort_estimate": item.effort_estimate,
            "soa_ref": item.soa_ref,
        })

    return {
        "assessment_id": str(assessment.id),
        "assignment": {
            "id": str(assignment.id),
            "scope": assignment.scope,
            "scope_theme": assignment.scope_theme,
            "respondent_user_id": str(assignment.respondent_user_id) if assignment.respondent_user_id else None,
            "respondent_email": assignment.respondent_email,
            "submitted_at": _date_value(assignment.submitted_at),
            "signed_at": _date_value(signed_at),
        },
        "dashboard": compute_dashboard(db, assessment.tenant_id, assessment.id),
        "items": items,
    }


def _assert_can_sign(assignment: GapAssignment, ctx: OrgContext) -> None:
    if assignment.respondent_user_id == ctx.principal.user.id:
        return
    if has_permission(ctx.role, "manage_gap"):
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Apenas o responsavel atribuido pode assinar esta conducao.")


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


@router.post("/{assignment_id}/sign", response_model=AssignmentSignResponse)
def sign_assignment(
    assignment_id: uuid.UUID,
    db: db_dep,
    ctx: sign_dep,
    request: Request,
):
    """Assina a conducao submetida e congela uma baseline versionada do Gap Analysis."""
    assignment = scoped_query(db, GapAssignment, ctx).filter(
        GapAssignment.id == assignment_id
    ).first()
    if assignment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuicao nao encontrada.")
    if assignment.status == "signed":
        raise HTTPException(status.HTTP_409_CONFLICT, "Conducao ja assinada.")
    if assignment.status != "submitted":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Status atual: {assignment.status}. Apenas 'submitted' pode ser assinado.",
        )
    _assert_can_sign(assignment, ctx)

    assessment = _get_assessment(db, ctx.tenant_id)
    if assignment.assessment_id != assessment.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Atribuicao nao encontrada.")

    signed_at = datetime.now(timezone.utc)
    signed_content = _signed_content(db, assignment, assessment, signed_at)
    content_hash = _content_hash(signed_content)
    signer_name = ctx.principal.user.full_name or str(ctx.principal.user.id)
    snapshot = {
        "dashboard": signed_content["dashboard"],
        "items": signed_content["items"],
        "assignment": signed_content["assignment"],
        "signed_content": signed_content,
        "signature": {
            "signer_user_id": str(ctx.principal.user.id),
            "signer_name": signer_name,
            "signer_email": ctx.principal.user.email,
            "signed_at": signed_at.isoformat(),
            "content_hash": content_hash,
            "hash_algorithm": "sha256",
            "level": "advanced",
        },
    }

    if assessment.draft_status != DocStatus.in_review:
        cds.submit_review(db, assessment)

    assignment.status = "signed"
    assignment.signed_at = signed_at
    version = cds.approve_document(
        db=db,
        artifact=assessment,
        doc_type=DocType.gap_baseline,
        actor_id=ctx.principal.user.id,
        classification=Classification.uso_interno,
        next_review_at=None,
        change_nature="Assinatura da conducao do Gap Analysis",
        snapshot_factory=lambda: snapshot,
    )
    db.refresh(assignment)

    AuditService.log_from_request(
        request=request,
        operation="SIGN",
        entity_type="gap_assignment",
        entity_id=str(assignment.id),
        details={"baseline_version_number": version.version_number},
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return AssignmentSignResponse(
        assignment=_to_response(assignment),
        baseline=_baseline_response(version),
        content_hash=content_hash,
        signed_at=signed_at,
    )


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
    if assignment.status in ("cancelled", "submitted", "signed"):
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
