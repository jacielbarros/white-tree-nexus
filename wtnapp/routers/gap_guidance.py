"""Orientação de Avaliação por Item (Feature 007).

Leitura por usuário da organização (`view_gap`) — conteúdo de plataforma compartilhado.
Edição exclusiva do Super Admin da plataforma (`require_super_admin`, sem contexto de org), com
trilha append-only + audit. A leitura NÃO gera audit log; tentativas de edição não autorizadas são
auditadas pelas dependencies centrais.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission, require_super_admin
from wtnapp.helpers.tenant_scope import OrgContext, Principal
from wtnapp.schemas.gap_guidance_schema import (
    GuidanceEvent,
    GuidanceResponse,
    ItemGuidance,
    ItemGuidanceUpdate,
    LegendEntry,
    LegendEntryUpdate,
)
from wtnapp.services import gap_guidance_service as svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/gap/guidance", tags=["gap-guidance"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
admin_dep = Annotated[Principal, Depends(require_super_admin())]


@router.get("", response_model=GuidanceResponse)
def get_guidance(db: db_dep, ctx: view_dep) -> GuidanceResponse:
    return svc.get_guidance(db)


@router.put("/items/{seed_item_id}", response_model=ItemGuidance)
def update_item(
    seed_item_id: uuid.UUID, patch: ItemGuidanceUpdate, request: Request, db: db_dep, principal: admin_dep
) -> ItemGuidance:
    item = svc.update_item_guidance(db, seed_item_id, patch, principal.user.id)
    AuditService.log_from_request(
        request=request, operation="GAP_GUIDANCE_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=principal.user.id, entity_type="gap_seed_item", entity_id=str(seed_item_id),
    )
    return ItemGuidance(
        seed_item_id=item.id, ref_code=item.ref_code, referencia=item.referencia or "",
        objetivo=item.objective or "", como_avaliar=list(item.como_avaliar or []),
        evidencias_esperadas=list(item.evidencias_esperadas or []), nota=item.nota,
    )


@router.put("/legend/{entry_id}", response_model=LegendEntry)
def update_legend(
    entry_id: uuid.UUID, patch: LegendEntryUpdate, request: Request, db: db_dep, principal: admin_dep
) -> LegendEntry:
    entry = svc.update_legend(db, entry_id, patch, principal.user.id)
    AuditService.log_from_request(
        request=request, operation="GAP_LEGEND_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=principal.user.id, entity_type="gap_legend_entry", entity_id=str(entry_id),
    )
    return LegendEntry.model_validate(entry)


@router.get("/events", response_model=list[GuidanceEvent])
def list_events(db: db_dep, principal: admin_dep) -> list[GuidanceEvent]:
    return [GuidanceEvent.model_validate(e) for e in svc.list_events(db)]
