"""Melhoria Contínua / PDCA (cláusula 10.1) — Feature 015 / 5b."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import has_permission, require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.schemas.improvement_schema import ImprovementRequest, ImprovementSummary, PdcaEntry
from wtnapp.services import improvement_service as svc
from wtnapp.services import pdca_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, ImprovementOrigin, ImprovementStatus, SgsiArtifactType

router = APIRouter(prefix="/improvements", tags=["improvement"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_nonconformity"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_nonconformity"))]


def _audit(request: Request, ctx: OrgContext, operation: str, *, entity_id=None, details=None):
    AuditService.log_from_request(
        request=request, operation=operation, outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="improvement", entity_id=str(entity_id) if entity_id else None, details=details or {},
    )


@router.get("", response_model=list[ImprovementSummary])
def list_improvements(
    db: db_dep, ctx: view_dep,
    status_filter: ImprovementStatus | None = Query(default=None, alias="status"),
    origin: ImprovementOrigin | None = None,
):
    rows = svc.list_improvements(db, ctx, status_filter=status_filter, origin=origin)
    return [ImprovementSummary.model_validate(i) for i in rows]


@router.post("", response_model=ImprovementSummary, status_code=status.HTTP_201_CREATED)
def create_improvement(request: Request, db: db_dep, ctx: manage_dep, body: ImprovementRequest):
    imp = svc.create_improvement(db, ctx, body)
    db.commit()
    db.refresh(imp)
    _audit(request, ctx, "CREATE_IMPROVEMENT", entity_id=imp.id, details={"code": imp.code, "origin": imp.origin.value})
    return ImprovementSummary.model_validate(imp)


@router.put("/{improvement_id}", response_model=ImprovementSummary)
def update_improvement(improvement_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ImprovementRequest):
    imp = svc.get_improvement(db, ctx, improvement_id)
    svc.update_improvement(db, ctx, imp, body)
    db.commit()
    db.refresh(imp)
    _audit(request, ctx, "UPDATE_IMPROVEMENT", entity_id=imp.id)
    return ImprovementSummary.model_validate(imp)


@router.get("/pdca", response_model=list[PdcaEntry])
def pdca_cycle(
    db: db_dep, ctx: view_dep,
    target_type: SgsiArtifactType | None = None,
    target_id: uuid.UUID | None = None,
):
    # RBAC composto: constatações só com view_internal_audit; atas só com view_management_review.
    entries = pdca_service.build_cycle(
        db, ctx, target_type, target_id,
        include_findings=has_permission(ctx.role, "view_internal_audit"),
        include_reviews=has_permission(ctx.role, "view_management_review"),
    )
    return [PdcaEntry(occurred_at=e.occurred_at, phase=e.phase, kind=e.kind, ref_id=e.ref_id, label=e.label, detail=e.detail) for e in entries]
