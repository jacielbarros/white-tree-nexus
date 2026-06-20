"""Diagnostico incremental de contexto."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.schemas.diagnostic_schema import DiagnosticBase, DiagnosticResponse
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/context/diagnostic", tags=["context"])


@router.get("", response_model=DiagnosticResponse)
def get_diagnostic(
    ctx: OrgContext = Depends(require_permission("view_context")),
    db: Session = Depends(get_db),
) -> DiagnosticResponse:
    diagnostic = scoped_query(db, Diagnostic, ctx).first()
    if diagnostic is None:
        return DiagnosticResponse(status="draft", sections={})
    return diagnostic


@router.put("", response_model=DiagnosticResponse)
def save_diagnostic(
    payload: DiagnosticBase,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
) -> Diagnostic:
    diagnostic = scoped_query(db, Diagnostic, ctx).first()
    if diagnostic is None:
        diagnostic = Diagnostic(tenant_id=ctx.tenant_id)
        db.add(diagnostic)
    diagnostic.status = payload.status
    diagnostic.sections = payload.sections
    diagnostic.updated_by = ctx.principal.user.id
    db.commit()
    db.refresh(diagnostic)
    AuditService.log_from_request(
        request=request,
        operation="DIAGNOSTIC_SAVE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id,
        entity_type="diagnostic",
        entity_id=diagnostic.id,
    )
    return diagnostic
