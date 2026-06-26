"""Gestão de Ativos / Processos / Escopo (Feature 011).

CRUD + arquivamento lógico de itens, relacionamentos flexíveis, vínculo a gaps do catálogo da org,
histórico append-only, cards de resumo, dashboard e fontes de contexto. Tudo tenant-scoped + audit.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.asset_item_model import AssetGapLink, AssetItem, AssetItemEvent, AssetRelationship
from wtnapp.models.context_analysis_model import ContextIssue
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.scope_model import ScopeItem
from wtnapp.models.stakeholder_model import Stakeholder
from wtnapp.schemas.asset_schema import (
    AssetArchiveRequest,
    AssetDashboardResponse,
    AssetItemCreate,
    AssetItemDetail,
    AssetItemEventResponse,
    AssetItemResponse,
    AssetItemUpdate,
    AssetSummaryResponse,
    ContextSourceResponse,
    GapLinkCreate,
    GapLinkResponse,
    RelationshipCreate,
    RelationshipResponse,
)
from wtnapp.services import asset_metrics_service, asset_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import (
    AssetItemEventType,
    AssetRecordStatus,
    AssetReviewStatus,
    AssetScopeStatus,
    AssetType,
    CiaLevel,
    AuditOutcome,
    ScopeItemKind,
)

router = APIRouter(prefix="/assets", tags=["assets"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_asset"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_asset"))]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit(
    request: Request,
    ctx: OrgContext,
    operation: str,
    *,
    outcome: AuditOutcome = AuditOutcome.success,
    entity_id: uuid.UUID | str | None = None,
    entity_type: str = "asset_item",
    details: dict | None = None,
) -> None:
    AuditService.log_from_request(
        request=request,
        operation=operation,
        outcome=outcome,
        actor_user_id=ctx.principal.user.id,
        actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        details=details or {},
    )


def _get_item(db: Session, ctx: OrgContext, item_id: uuid.UUID, request: Request | None = None) -> AssetItem:
    item = scoped_query(db, AssetItem, ctx).filter(AssetItem.id == item_id).first()
    if item is None:
        if request is not None:
            _audit(request, ctx, "ASSET_ACCESS_DENIED", outcome=AuditOutcome.denied, entity_id=item_id,
                   details={"reason": "not_found_or_not_in_tenant"})
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    return item


def _resolve_criticality(payload) -> tuple[CiaLevel | None, bool]:
    if payload.criticality_is_manual and payload.criticality is not None:
        return payload.criticality, True
    return asset_service.compute_criticality(payload.confidentiality, payload.integrity, payload.availability), False


# --- Listagem -------------------------------------------------------------------

@router.get("", response_model=list[AssetItemResponse])
def list_assets(
    db: db_dep,
    ctx: view_dep,
    item_type: AssetType | None = None,
    record_status: AssetRecordStatus | None = None,
    scope_status: AssetScopeStatus | None = None,
    responsible_user_id: uuid.UUID | None = None,
    criticality: CiaLevel | None = None,
    confidentiality: CiaLevel | None = None,
    integrity: CiaLevel | None = None,
    availability: CiaLevel | None = None,
    has_personal_data: bool | None = None,
    has_sensitive_data: bool | None = None,
    review_status: AssetReviewStatus | None = None,
    without_responsible: bool | None = None,
    cia_incomplete: bool | None = None,
    linked_gap: bool | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 50,
):
    query = scoped_query(db, AssetItem, ctx)
    if item_type is not None:
        query = query.filter(AssetItem.item_type == item_type)
    if record_status is not None:
        query = query.filter(AssetItem.record_status == record_status)
    if scope_status is not None:
        query = query.filter(AssetItem.scope_status == scope_status)
    if responsible_user_id is not None:
        query = query.filter(AssetItem.responsible_user_id == responsible_user_id)
    if criticality is not None:
        query = query.filter(AssetItem.criticality == criticality)
    if confidentiality is not None:
        query = query.filter(AssetItem.confidentiality == confidentiality)
    if integrity is not None:
        query = query.filter(AssetItem.integrity == integrity)
    if availability is not None:
        query = query.filter(AssetItem.availability == availability)
    if has_personal_data is not None:
        query = query.filter(AssetItem.has_personal_data == has_personal_data)
    if has_sensitive_data is not None:
        query = query.filter(AssetItem.has_sensitive_data == has_sensitive_data)
    if without_responsible:
        query = query.filter(AssetItem.responsible_user_id.is_(None))
    if cia_incomplete:
        query = query.filter(
            or_(
                AssetItem.confidentiality.is_(None),
                AssetItem.integrity.is_(None),
                AssetItem.availability.is_(None),
            )
        )
    if linked_gap:
        linked_ids = {row.item_id for row in scoped_query(db, AssetGapLink, ctx).all()}
        query = query.filter(AssetItem.id.in_(linked_ids or [uuid.uuid4()]))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                AssetItem.name.ilike(like),
                AssetItem.description.ilike(like),
                AssetItem.business_unit.ilike(like),
                AssetItem.compliance_notes.ilike(like),
            )
        )

    items = query.order_by(AssetItem.created_at.desc()).all()

    # Filtro por situação de revisão (derivada, não é coluna).
    if review_status is not None:
        items = [it for it in items if asset_service.derive_review_status(it.next_review_at) == review_status]

    start = max(page - 1, 0) * page_size
    return [asset_service.build_response(it) for it in items[start:start + page_size]]


# --- Métricas (rotas literais antes de /{id}) -----------------------------------

@router.get("/summary", response_model=AssetSummaryResponse)
def assets_summary(db: db_dep, ctx: view_dep):
    return asset_metrics_service.summary(db, ctx)


@router.get("/dashboard", response_model=AssetDashboardResponse)
def assets_dashboard(db: db_dep, ctx: view_dep):
    return asset_metrics_service.dashboard(db, ctx)


@router.get("/context-sources", response_model=list[ContextSourceResponse])
def context_sources(db: db_dep, ctx: view_dep):
    """Elementos da Análise de Contexto (002) como ponto de partida para novos itens (US5)."""
    sources: list[ContextSourceResponse] = []
    for s in scoped_query(db, Stakeholder, ctx).all():
        suggested = AssetType.supplier if s.type == "external" else AssetType.person_team
        sources.append(ContextSourceResponse(
            origin_type="stakeholder", origin_id=s.id, label=s.name,
            description=f"Parte interessada ({s.type})", suggested_item_type=suggested,
        ))
    for si in scoped_query(db, ScopeItem, ctx).filter(ScopeItem.kind == ScopeItemKind.inclusion).all():
        sources.append(ContextSourceResponse(
            origin_type="scope", origin_id=si.id, label=si.description[:120],
            description="Inclusão do escopo preliminar", suggested_item_type=AssetType.business_process,
        ))
    for ci in scoped_query(db, ContextIssue, ctx).all():
        sources.append(ContextSourceResponse(
            origin_type="context_issue", origin_id=ci.id, label=ci.category,
            description=ci.description[:200], suggested_item_type=AssetType.other,
        ))
    return sources


# --- Criação --------------------------------------------------------------------

@router.post("", response_model=AssetItemResponse, status_code=status.HTTP_201_CREATED)
def create_asset(body: AssetItemCreate, db: db_dep, ctx: manage_dep, request: Request):
    asset_service.validate_members(db, ctx, [body.responsible_user_id, body.owner_user_id, body.custodian_user_id])
    asset_service.validate_related_items(db, ctx, [body.related_system_id, body.related_process_id, body.related_supplier_id])
    asset_service.validate_scope(
        body, responsible_user_id=body.responsible_user_id,
        c=body.confidentiality, i=body.integrity, a=body.availability,
        scope_justification=body.scope_justification,
    )
    asset_service.check_duplicate(
        db, ctx, name=body.name, item_type=body.item_type,
        allow_duplicate=body.allow_duplicate, reason=body.reason,
    )
    criticality, is_manual = _resolve_criticality(body)
    item = AssetItem(
        tenant_id=ctx.tenant_id,
        code=asset_service.generate_code(db, ctx.tenant_id, body.item_type),
        item_type=body.item_type,
        name=body.name,
        description=body.description,
        business_unit=body.business_unit,
        responsible_user_id=body.responsible_user_id,
        owner_user_id=body.owner_user_id,
        custodian_user_id=body.custodian_user_id,
        record_status=body.record_status,
        scope_status=body.scope_status,
        scope_justification=body.scope_justification,
        location=body.location,
        related_system_id=body.related_system_id,
        related_process_id=body.related_process_id,
        related_supplier_id=body.related_supplier_id,
        has_personal_data=body.has_personal_data,
        has_sensitive_data=body.has_sensitive_data,
        compliance_notes=body.compliance_notes,
        confidentiality=body.confidentiality,
        integrity=body.integrity,
        availability=body.availability,
        criticality=criticality,
        criticality_is_manual=is_manual,
        last_review_at=body.last_review_at,
        next_review_at=body.next_review_at,
        context_origin_type=body.context_origin_type,
        context_origin_id=body.context_origin_id,
        created_by=ctx.principal.user.id,
    )
    db.add(item)
    db.flush()
    asset_service.log_event(
        db, ctx, item.id, AssetItemEventType.created,
        new_value=item.code, details={"item_type": item.item_type.value, "scope_status": item.scope_status.value},
    )
    db.commit()
    db.refresh(item)
    _audit(request, ctx, "CREATE_ASSET", entity_id=item.id,
           details={"code": item.code, "item_type": item.item_type.value})
    return asset_service.build_response(item)


# --- Detalhe / atualização / arquivamento ---------------------------------------

@router.get("/{item_id}", response_model=AssetItemDetail)
def get_asset(item_id: uuid.UUID, db: db_dep, ctx: view_dep, request: Request):
    item = _get_item(db, ctx, item_id, request)
    return AssetItemDetail(
        item=asset_service.build_response(item),
        relationships=_relationships_for(db, ctx, item.id),
        gap_links=_gap_links_for(db, ctx, item.id),
    )


@router.put("/{item_id}", response_model=AssetItemResponse)
def update_asset(item_id: uuid.UUID, body: AssetItemUpdate, db: db_dep, ctx: manage_dep, request: Request):
    item = _get_item(db, ctx, item_id, request)
    asset_service.validate_members(db, ctx, [body.responsible_user_id, body.owner_user_id, body.custodian_user_id])
    asset_service.validate_related_items(db, ctx, [body.related_system_id, body.related_process_id, body.related_supplier_id])
    asset_service.validate_scope(
        body, responsible_user_id=body.responsible_user_id,
        c=body.confidentiality, i=body.integrity, a=body.availability,
        scope_justification=body.scope_justification,
    )
    asset_service.check_duplicate(
        db, ctx, name=body.name, item_type=body.item_type,
        allow_duplicate=body.allow_duplicate, reason=body.reason, exclude_id=item.id,
    )

    before = asset_service.snapshot(item)

    item.name = body.name
    item.item_type = body.item_type  # tipo pode mudar; código permanece imutável
    item.description = body.description
    item.business_unit = body.business_unit
    item.responsible_user_id = body.responsible_user_id
    item.owner_user_id = body.owner_user_id
    item.custodian_user_id = body.custodian_user_id
    item.record_status = body.record_status
    item.scope_status = body.scope_status
    item.scope_justification = body.scope_justification
    item.location = body.location
    item.related_system_id = body.related_system_id
    item.related_process_id = body.related_process_id
    item.related_supplier_id = body.related_supplier_id
    item.has_personal_data = body.has_personal_data
    item.has_sensitive_data = body.has_sensitive_data
    item.compliance_notes = body.compliance_notes
    item.confidentiality = body.confidentiality
    item.integrity = body.integrity
    item.availability = body.availability
    criticality, is_manual = _resolve_criticality(body)
    item.criticality = criticality
    item.criticality_is_manual = is_manual
    item.last_review_at = body.last_review_at
    item.next_review_at = body.next_review_at
    item.updated_by = ctx.principal.user.id

    asset_service.diff_and_log(db, ctx, before, item, body.reason)
    db.commit()
    db.refresh(item)
    _audit(request, ctx, "UPDATE_ASSET", entity_id=item.id, details={"code": item.code})
    return asset_service.build_response(item)


@router.post("/{item_id}/archive", response_model=AssetItemResponse)
def archive_asset(item_id: uuid.UUID, body: AssetArchiveRequest, db: db_dep, ctx: manage_dep, request: Request):
    item = _get_item(db, ctx, item_id, request)
    if not (body.reason or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Arquivamento exige justificativa.")
    item.record_status = AssetRecordStatus.archived
    item.archived_at = _now()
    item.archived_by = ctx.principal.user.id
    item.archive_reason = body.reason.strip()
    item.updated_by = ctx.principal.user.id
    asset_service.log_event(
        db, ctx, item.id, AssetItemEventType.archived,
        field_name="record_status", new_value=AssetRecordStatus.archived.value, reason=body.reason.strip(),
    )
    db.commit()
    db.refresh(item)
    _audit(request, ctx, "ARCHIVE_ASSET", entity_id=item.id, details={"code": item.code})
    return asset_service.build_response(item)


@router.get("/{item_id}/history", response_model=list[AssetItemEventResponse])
def asset_history(item_id: uuid.UUID, db: db_dep, ctx: view_dep, request: Request):
    _get_item(db, ctx, item_id, request)
    events = (
        scoped_query(db, AssetItemEvent, ctx)
        .filter(AssetItemEvent.item_id == item_id)
        .order_by(AssetItemEvent.occurred_at.asc())
        .all()
    )
    return [AssetItemEventResponse.model_validate(e) for e in events]


# --- Relacionamentos ------------------------------------------------------------

def _relationships_for(db: Session, ctx: OrgContext, item_id: uuid.UUID) -> list[RelationshipResponse]:
    rels = (
        scoped_query(db, AssetRelationship, ctx)
        .filter(or_(AssetRelationship.source_item_id == item_id, AssetRelationship.target_item_id == item_id))
        .all()
    )
    item_ids = {r.source_item_id for r in rels} | {r.target_item_id for r in rels}
    items = {it.id: it for it in scoped_query(db, AssetItem, ctx).filter(AssetItem.id.in_(item_ids or [uuid.uuid4()]))}
    out: list[RelationshipResponse] = []
    for r in rels:
        src, tgt = items.get(r.source_item_id), items.get(r.target_item_id)
        out.append(RelationshipResponse(
            id=r.id, source_item_id=r.source_item_id, relationship_type=r.relationship_type,
            target_item_id=r.target_item_id, description=r.description, created_at=r.created_at,
            source_code=src.code if src else None, source_name=src.name if src else None,
            target_code=tgt.code if tgt else None, target_name=tgt.name if tgt else None,
            direction="outgoing" if r.source_item_id == item_id else "incoming",
        ))
    return out


@router.post("/{item_id}/relationships", response_model=RelationshipResponse, status_code=status.HTTP_201_CREATED)
def add_relationship(item_id: uuid.UUID, body: RelationshipCreate, db: db_dep, ctx: manage_dep, request: Request):
    source = _get_item(db, ctx, item_id, request)
    if body.target_item_id == source.id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Um item não pode se relacionar consigo mesmo.")
    target = _get_item(db, ctx, body.target_item_id, request)  # garante mesmo tenant
    exists = db.query(
        scoped_query(db, AssetRelationship, ctx).filter(
            AssetRelationship.source_item_id == source.id,
            AssetRelationship.relationship_type == body.relationship_type,
            AssetRelationship.target_item_id == target.id,
        ).exists()
    ).scalar()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Relacionamento já existe.")
    rel = AssetRelationship(
        tenant_id=ctx.tenant_id, source_item_id=source.id, relationship_type=body.relationship_type,
        target_item_id=target.id, description=body.description, created_by=ctx.principal.user.id,
    )
    db.add(rel)
    asset_service.log_event(
        db, ctx, source.id, AssetItemEventType.relationship_add,
        new_value=f"{body.relationship_type.value} -> {target.code}",
        details={"target_item_id": str(target.id), "type": body.relationship_type.value},
    )
    db.commit()
    db.refresh(rel)
    _audit(request, ctx, "ADD_ASSET_RELATIONSHIP", entity_id=source.id,
           entity_type="asset_relationship", details={"target_item_id": str(target.id)})
    return RelationshipResponse(
        id=rel.id, source_item_id=rel.source_item_id, relationship_type=rel.relationship_type,
        target_item_id=rel.target_item_id, description=rel.description, created_at=rel.created_at,
        source_code=source.code, source_name=source.name, target_code=target.code, target_name=target.name,
        direction="outgoing",
    )


@router.delete("/{item_id}/relationships/{rel_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_relationship(item_id: uuid.UUID, rel_id: uuid.UUID, db: db_dep, ctx: manage_dep, request: Request):
    source = _get_item(db, ctx, item_id, request)
    rel = (
        scoped_query(db, AssetRelationship, ctx)
        .filter(AssetRelationship.id == rel_id, AssetRelationship.source_item_id == source.id)
        .first()
    )
    if rel is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    target_id = rel.target_item_id
    db.delete(rel)
    asset_service.log_event(
        db, ctx, source.id, AssetItemEventType.relationship_remove,
        old_value=str(target_id), details={"target_item_id": str(target_id)},
    )
    db.commit()
    _audit(request, ctx, "REMOVE_ASSET_RELATIONSHIP", entity_id=source.id, entity_type="asset_relationship")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Vínculo com Gap ------------------------------------------------------------

def _gap_links_for(db: Session, ctx: OrgContext, item_id: uuid.UUID) -> list[GapLinkResponse]:
    links = scoped_query(db, AssetGapLink, ctx).filter(AssetGapLink.item_id == item_id).all()
    gap_ids = {lk.gap_catalog_item_id for lk in links}
    gaps = {g.id: g for g in scoped_query(db, GapCatalogItem, ctx).filter(GapCatalogItem.id.in_(gap_ids or [uuid.uuid4()]))}
    out: list[GapLinkResponse] = []
    for lk in links:
        g = gaps.get(lk.gap_catalog_item_id)
        out.append(GapLinkResponse(
            id=lk.id, item_id=lk.item_id, gap_catalog_item_id=lk.gap_catalog_item_id, note=lk.note,
            created_at=lk.created_at,
            gap_ref_code=g.ref_code if g else None, gap_name=g.name if g else None,
            gap_is_discontinued=g.is_discontinued if g else None,
        ))
    return out


@router.post("/{item_id}/gap-links", response_model=GapLinkResponse, status_code=status.HTTP_201_CREATED)
def add_gap_link(item_id: uuid.UUID, body: GapLinkCreate, db: db_dep, ctx: manage_dep, request: Request):
    item = _get_item(db, ctx, item_id, request)
    gap = (
        scoped_query(db, GapCatalogItem, ctx)
        .filter(GapCatalogItem.id == body.gap_catalog_item_id)
        .first()
    )
    if gap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    exists = db.query(
        scoped_query(db, AssetGapLink, ctx).filter(
            AssetGapLink.item_id == item.id, AssetGapLink.gap_catalog_item_id == gap.id
        ).exists()
    ).scalar()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "Vínculo com este gap já existe.")
    link = AssetGapLink(
        tenant_id=ctx.tenant_id, item_id=item.id, gap_catalog_item_id=gap.id,
        note=body.note, created_by=ctx.principal.user.id,
    )
    db.add(link)
    asset_service.log_event(
        db, ctx, item.id, AssetItemEventType.gap_link,
        new_value=gap.ref_code, details={"gap_catalog_item_id": str(gap.id)},
    )
    db.commit()
    db.refresh(link)
    _audit(request, ctx, "LINK_ASSET_GAP", entity_id=item.id, entity_type="asset_gap_link",
           details={"gap_catalog_item_id": str(gap.id)})
    return GapLinkResponse(
        id=link.id, item_id=link.item_id, gap_catalog_item_id=link.gap_catalog_item_id, note=link.note,
        created_at=link.created_at, gap_ref_code=gap.ref_code, gap_name=gap.name,
        gap_is_discontinued=gap.is_discontinued,
    )


@router.delete("/{item_id}/gap-links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_gap_link(item_id: uuid.UUID, link_id: uuid.UUID, db: db_dep, ctx: manage_dep, request: Request):
    item = _get_item(db, ctx, item_id, request)
    link = (
        scoped_query(db, AssetGapLink, ctx)
        .filter(AssetGapLink.id == link_id, AssetGapLink.item_id == item.id)
        .first()
    )
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    gap_id = link.gap_catalog_item_id
    db.delete(link)
    asset_service.log_event(
        db, ctx, item.id, AssetItemEventType.gap_unlink,
        old_value=str(gap_id), details={"gap_catalog_item_id": str(gap_id)},
    )
    db.commit()
    _audit(request, ctx, "UNLINK_ASSET_GAP", entity_id=item.id, entity_type="asset_gap_link")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
