"""Mapa de Partes Interessadas (4.2)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement
from wtnapp.schemas.context_schema import DocumentApproval, DocumentVersionResponse
from wtnapp.schemas.stakeholder_schema import StakeholderCreate, StakeholderMapResponse, StakeholderResponse, StakeholderUpdate
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DocType, EngagementStrategy, Level

router = APIRouter(prefix="/context/stakeholders", tags=["context"])
_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


def derive_strategy(power: Level, interest: Level) -> EngagementStrategy:
    if power == Level.alto and interest == Level.alto:
        return EngagementStrategy.manage_closely
    if power == Level.alto:
        return EngagementStrategy.keep_satisfied
    if interest == Level.alto:
        return EngagementStrategy.keep_informed
    return EngagementStrategy.monitor


def _get_or_create(db: Session, ctx: OrgContext) -> StakeholderMap:
    item = scoped_query(db, StakeholderMap, ctx).first()
    if item is None:
        item = StakeholderMap(tenant_id=ctx.tenant_id)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def _stakeholder_response(db: Session, s: Stakeholder) -> StakeholderResponse:
    reqs = db.query(StakeholderRequirement).filter(StakeholderRequirement.stakeholder_id == s.id).all()
    return StakeholderResponse(
        id=s.id, name=s.name, type=s.type, power=s.power, interest=s.interest, strategy=s.strategy, requirements=reqs
    )


def _serialize(db: Session, item: StakeholderMap) -> StakeholderMapResponse:
    rows = db.query(Stakeholder).filter(Stakeholder.tenant_id == item.tenant_id, Stakeholder.map_id == item.id).all()
    current = db.get(DocumentVersion, item.current_version_id) if item.current_version_id else None
    return StakeholderMapResponse(
        id=item.id,
        draft_status=item.draft_status,
        current_version_id=item.current_version_id,
        stakeholders=[_stakeholder_response(db, row) for row in rows],
        review_overdue=cds.review_overdue(current),
    )


def _replace_requirements(db: Session, stakeholder: Stakeholder, requirements) -> None:
    db.query(StakeholderRequirement).filter(StakeholderRequirement.stakeholder_id == stakeholder.id).delete()
    for req in requirements or []:
        db.add(StakeholderRequirement(tenant_id=stakeholder.tenant_id, stakeholder_id=stakeholder.id, **req.model_dump()))


@router.get("", response_model=StakeholderMapResponse)
def get_map(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    return _serialize(db, _get_or_create(db, ctx))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=StakeholderResponse)
def create_stakeholder(
    payload: StakeholderCreate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    item = _get_or_create(db, ctx)
    stakeholder = Stakeholder(
        tenant_id=ctx.tenant_id,
        map_id=item.id,
        name=payload.name,
        type=payload.type,
        power=payload.power,
        interest=payload.interest,
        strategy=derive_strategy(payload.power, payload.interest),
    )
    db.add(stakeholder)
    db.flush()
    _replace_requirements(db, stakeholder, payload.requirements)
    db.commit()
    db.refresh(stakeholder)
    AuditService.log_from_request(
        request=request, operation="STAKEHOLDER_CREATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="stakeholder", entity_id=stakeholder.id,
    )
    return _stakeholder_response(db, stakeholder)


@router.patch("/{stakeholder_id}", response_model=StakeholderResponse)
def update_stakeholder(
    stakeholder_id: uuid.UUID,
    payload: StakeholderUpdate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    stakeholder = scoped_query(db, Stakeholder, ctx).filter(Stakeholder.id == stakeholder_id).first()
    if stakeholder is None:
        raise _NOT_FOUND
    data = payload.model_dump(exclude_unset=True, exclude={"requirements"})
    for key, value in data.items():
        setattr(stakeholder, key, value)
    stakeholder.strategy = derive_strategy(stakeholder.power, stakeholder.interest)
    if payload.requirements is not None:
        _replace_requirements(db, stakeholder, payload.requirements)
    db.commit()
    db.refresh(stakeholder)
    AuditService.log_from_request(
        request=request, operation="STAKEHOLDER_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="stakeholder", entity_id=stakeholder.id,
    )
    return _stakeholder_response(db, stakeholder)


@router.delete("/{stakeholder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stakeholder(
    stakeholder_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    stakeholder = scoped_query(db, Stakeholder, ctx).filter(Stakeholder.id == stakeholder_id).first()
    if stakeholder is None:
        raise _NOT_FOUND
    db.delete(stakeholder)
    db.commit()
    AuditService.log_from_request(
        request=request, operation="STAKEHOLDER_DELETE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="stakeholder", entity_id=stakeholder_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/submit-review", response_model=StakeholderMapResponse)
def submit_review(
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    item = cds.submit_review(db, _get_or_create(db, ctx))
    AuditService.log_from_request(
        request=request, operation="STAKEHOLDER_MAP_SUBMIT_REVIEW", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="stakeholder_map", entity_id=item.id,
    )
    return _serialize(db, item)


@router.post("/approve", status_code=status.HTTP_201_CREATED, response_model=DocumentVersionResponse)
def approve(
    payload: DocumentApproval,
    request: Request,
    ctx: OrgContext = Depends(require_permission("approve_context_document")),
    db: Session = Depends(get_db),
):
    item = _get_or_create(db, ctx)
    version = cds.approve_document(
        db=db, artifact=item, doc_type=DocType.stakeholder_map, actor_id=ctx.principal.user.id,
        classification=payload.classification, next_review_at=payload.next_review_at,
        change_nature=payload.change_nature, snapshot_factory=lambda: _serialize(db, item).model_dump(mode="json"),
    )
    AuditService.log_from_request(
        request=request, operation="STAKEHOLDER_MAP_APPROVE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="document_version", entity_id=version.id,
    )
    return version


@router.get("/versions", response_model=list[DocumentVersionResponse])
def versions(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    item = _get_or_create(db, ctx)
    return cds.list_versions(db, ctx.tenant_id, DocType.stakeholder_map, item.id)
