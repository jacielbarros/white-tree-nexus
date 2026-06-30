"""Não Conformidades & Ações Corretivas (cláusula 10.2) — Feature 015 / 5b."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.nonconformity_model import CorrectiveAction, NonConformity
from wtnapp.schemas.nonconformity_schema import (
    ActionRequest,
    ActionSummary,
    NcDashboard,
    NCDetail,
    NCReadiness,
    NCRequest,
    NCSummary,
    NCTransitionRequest,
    PromoteRequest,
    VerificationRequest,
    VerificationSummary,
)
from wtnapp.services import nc_metrics_service
from wtnapp.services import nonconformity_service as svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, NCSeverity, NCStatus

router = APIRouter(prefix="/nonconformities", tags=["nonconformity"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_nonconformity"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_nonconformity"))]


def _audit(request: Request, ctx: OrgContext, operation: str, *, entity_id=None, outcome=AuditOutcome.success, details=None):
    AuditService.log_from_request(
        request=request, operation=operation, outcome=outcome,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="nonconformity", entity_id=str(entity_id) if entity_id else None, details=details or {},
    )


def _action_summary(db: Session, ctx: OrgContext, a: CorrectiveAction) -> ActionSummary:
    return ActionSummary(
        id=a.id, nonconformity_id=a.nonconformity_id, description=a.description,
        responsible_member_id=a.responsible_member_id, due_date=a.due_date, status=a.status,
        overdue=svc.is_overdue(a),
    )


def _detail(db: Session, ctx: OrgContext, nc: NonConformity) -> NCDetail:
    return NCDetail(
        id=nc.id, code=nc.code, origin=nc.origin, title=nc.title, severity=nc.severity, status=nc.status,
        source_finding_id=nc.source_finding_id, target_type=nc.target_type, target_id=nc.target_id,
        description=nc.description, root_cause=nc.root_cause, root_cause_method=nc.root_cause_method,
        readiness=NCReadiness(
            can_close=svc.can_close(db, ctx, nc),
            has_effective_verification=svc.has_effective_verification(db, ctx, nc.id),
            overdue_actions=svc.overdue_actions(db, ctx, nc.id),
            open_actions=svc.open_actions(db, ctx, nc.id),
        ),
    )


# ───────────────────────────── NC ─────────────────────────────

@router.get("", response_model=list[NCSummary])
def list_ncs(
    db: db_dep, ctx: view_dep,
    status_filter: NCStatus | None = Query(default=None, alias="status"),
    severity: NCSeverity | None = None,
    responsible_member_id: uuid.UUID | None = None,
    overdue: bool | None = None,
):
    query = scoped_query(db, NonConformity, ctx)
    if status_filter is not None:
        query = query.filter(NonConformity.status == status_filter)
    if severity is not None:
        query = query.filter(NonConformity.severity == severity)
    rows = query.order_by(NonConformity.created_at.desc()).all()

    if responsible_member_id is not None or overdue:
        keep: list[NonConformity] = []
        for nc in rows:
            actions = svc.list_actions(db, ctx, nc.id)
            if responsible_member_id is not None and not any(a.responsible_member_id == responsible_member_id for a in actions):
                continue
            if overdue and not any(svc.is_overdue(a) for a in actions):
                continue
            keep.append(nc)
        rows = keep
    return [NCSummary.model_validate(nc) for nc in rows]


@router.post("", response_model=NCSummary, status_code=status.HTTP_201_CREATED)
def create_nc(request: Request, db: db_dep, ctx: manage_dep, body: NCRequest):
    nc = svc.create_nc(db, ctx, body)
    db.commit()
    db.refresh(nc)
    _audit(request, ctx, "CREATE_NONCONFORMITY", entity_id=nc.id, details={"code": nc.code})
    return NCSummary.model_validate(nc)


@router.get("/dashboard", response_model=NcDashboard)
def dashboard(db: db_dep, ctx: view_dep):
    return NcDashboard(**nc_metrics_service.build_metrics(db, ctx))


@router.post("/promote", response_model=NCSummary)
def promote(request: Request, db: db_dep, ctx: manage_dep, body: PromoteRequest, response: Response):
    nc, created = svc.promote_finding(db, ctx, body.finding_id)
    db.commit()
    db.refresh(nc)
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    _audit(request, ctx, "PROMOTE_FINDING_TO_NC", entity_id=nc.id, details={"finding_id": str(body.finding_id), "created": created})
    return NCSummary.model_validate(nc)


@router.get("/{nc_id}", response_model=NCDetail)
def get_nc_detail(nc_id: uuid.UUID, db: db_dep, ctx: view_dep):
    return _detail(db, ctx, svc.get_nc(db, ctx, nc_id))


@router.put("/{nc_id}", response_model=NCSummary)
def update_nc(nc_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: NCRequest):
    nc = svc.get_nc(db, ctx, nc_id)
    svc.update_nc(db, ctx, nc, body)
    db.commit()
    db.refresh(nc)
    _audit(request, ctx, "UPDATE_NONCONFORMITY", entity_id=nc.id)
    return NCSummary.model_validate(nc)


@router.post("/{nc_id}/transition", response_model=NCSummary)
def transition(nc_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: NCTransitionRequest):
    nc = svc.get_nc(db, ctx, nc_id)
    svc.transition(db, ctx, nc, body.action)
    db.commit()
    db.refresh(nc)
    _audit(request, ctx, "TRANSITION_NONCONFORMITY", entity_id=nc.id, details={"action": body.action, "status": nc.status.value})
    return NCSummary.model_validate(nc)


# ───────────────────────────── Ações corretivas ─────────────────────────────

@router.get("/{nc_id}/actions", response_model=list[ActionSummary])
def list_actions(nc_id: uuid.UUID, db: db_dep, ctx: view_dep):
    svc.get_nc(db, ctx, nc_id)
    return [_action_summary(db, ctx, a) for a in svc.list_actions(db, ctx, nc_id)]


@router.post("/{nc_id}/actions", response_model=ActionSummary, status_code=status.HTTP_201_CREATED)
def add_action(nc_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ActionRequest):
    nc = svc.get_nc(db, ctx, nc_id)
    action = svc.add_action(db, ctx, nc, body)
    db.commit()
    db.refresh(action)
    _audit(request, ctx, "ADD_CORRECTIVE_ACTION", entity_id=action.id)
    return _action_summary(db, ctx, action)


@router.put("/actions/{action_id}", response_model=ActionSummary)
def update_action(action_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ActionRequest):
    action = svc.get_action(db, ctx, action_id)
    svc.update_action(db, ctx, action, body)
    db.commit()
    db.refresh(action)
    _audit(request, ctx, "UPDATE_CORRECTIVE_ACTION", entity_id=action.id)
    return _action_summary(db, ctx, action)


@router.delete("/actions/{action_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_action(action_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    action = svc.get_action(db, ctx, action_id)
    svc.inactivate_action(db, ctx, action)
    db.commit()
    _audit(request, ctx, "INACTIVATE_CORRECTIVE_ACTION", entity_id=action.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ───────────────────────────── Verificação de eficácia ─────────────────────────────

@router.get("/{nc_id}/verifications", response_model=list[VerificationSummary])
def list_verifications(nc_id: uuid.UUID, db: db_dep, ctx: view_dep):
    svc.get_nc(db, ctx, nc_id)
    return [VerificationSummary.model_validate(v) for v in svc.list_verifications(db, ctx, nc_id)]


@router.post("/{nc_id}/verifications", response_model=VerificationSummary, status_code=status.HTTP_201_CREATED)
def add_verification(nc_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: VerificationRequest):
    nc = svc.get_nc(db, ctx, nc_id)
    verification = svc.add_verification(db, ctx, nc, body)
    db.commit()
    db.refresh(verification)
    _audit(request, ctx, "ADD_NC_VERIFICATION", entity_id=verification.id, details={"result": body.result.value})
    return VerificationSummary.model_validate(verification)
