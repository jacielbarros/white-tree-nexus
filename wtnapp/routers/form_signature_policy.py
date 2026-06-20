"""Politica de assinatura por organizacao (T023)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.schemas.form_assignment_schema import SignaturePolicyResponse, SignaturePolicyUpdate
from wtnapp.services import signature_service as sig_svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/form-signature-policy", tags=["form-signature-policy"])

db_dep = Annotated[Session, Depends(get_db)]
admin_dep = Annotated[OrgContext, Depends(require_permission("manage_org"))]
view_dep = Annotated[OrgContext, Depends(require_permission("view_form"))]


@router.get("", response_model=SignaturePolicyResponse)
def get_policy(ctx: view_dep, db: db_dep):
    return sig_svc.get_policy(db, ctx.tenant_id)


@router.put("", response_model=SignaturePolicyResponse)
def update_policy(
    body: SignaturePolicyUpdate,
    ctx: admin_dep,
    db: db_dep,
    request: Request,
):
    policy = sig_svc.update_policy(
        db, ctx.tenant_id, body.require_assigner_countersignature
    )
    AuditService.log_from_request(
        request=request, operation="UPDATE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
        entity_type="form_signature_policy",
        entity_id=str(policy.id),
        details={"require_assigner_countersignature": body.require_assigner_countersignature},
    )
    return policy
