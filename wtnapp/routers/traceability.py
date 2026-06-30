"""Rastreabilidade / Timeline (read-only) — Feature 014, US7.

RBAC composto: exige a permissão de visualização do módulo do artefato-alvo **e** `view_evidence`;
constatações só entram com `view_internal_audit` (senão são omitidas sem revelar contagem).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import has_permission
from wtnapp.helpers.tenant_scope import OrgContext, get_org_context
from wtnapp.schemas.traceability_schema import TimelineEntryOut
from wtnapp.services import traceability_service
from wtnapp.services.audit_service import AuditService
from wtnapp.services.evidence_service import target_exists
from wtnapp.settings import AuditOutcome, SgsiArtifactType

router = APIRouter(prefix="/traceability", tags=["traceability"])

db_dep = Annotated[Session, Depends(get_db)]
ctx_dep = Annotated[OrgContext, Depends(get_org_context)]

# Permissão de visualização do módulo de cada tipo de alvo.
_MODULE_PERM = {
    SgsiArtifactType.soa_item: "view_soa",
    SgsiArtifactType.gap_item: "view_gap",
    SgsiArtifactType.risk: "view_risk",
    SgsiArtifactType.asset: "view_asset",
    SgsiArtifactType.audit_finding: "view_internal_audit",
}


@router.get("/timeline", response_model=list[TimelineEntryOut])
def timeline(request: Request, db: db_dep, ctx: ctx_dep, target_type: SgsiArtifactType, target_id: uuid.UUID):
    module_perm = _MODULE_PERM[target_type]
    if not (has_permission(ctx.role, module_perm) and has_permission(ctx.role, "view_evidence")):
        AuditService.log_from_request(
            request=request, operation="TIMELINE_ACCESS_DENIED", outcome=AuditOutcome.denied,
            actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
            entity_type=f"target:{target_type.value}", entity_id=str(target_id),
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")
    if not target_exists(db, ctx, target_type, target_id):
        AuditService.log_from_request(
            request=request, operation="TIMELINE_ACCESS_DENIED", outcome=AuditOutcome.denied,
            actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
            entity_type=f"target:{target_type.value}", entity_id=str(target_id),
            details={"reason": "not_found_or_not_in_tenant"},
        )
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")

    include_findings = has_permission(ctx.role, "view_internal_audit")
    entries = traceability_service.build_timeline(db, ctx, target_type, target_id, include_findings=include_findings)
    return [TimelineEntryOut(occurred_at=e.occurred_at, kind=e.kind, ref_id=e.ref_id, label=e.label, detail=e.detail) for e in entries]
