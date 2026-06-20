"""Declaracao de Escopo do SGSI (4.3)."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.scope_model import ScopeItem, ScopeStatement
from wtnapp.schemas.context_schema import DocumentApproval, DocumentVersionResponse
from wtnapp.schemas.scope_schema import ScopeItemCreate, ScopeItemResponse, ScopeResponse, ScopeUpdate
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DocType

router = APIRouter(prefix="/context/scope", tags=["context"])


def _get_or_create(db: Session, ctx: OrgContext) -> ScopeStatement:
    item = scoped_query(db, ScopeStatement, ctx).first()
    if item is None:
        item = ScopeStatement(tenant_id=ctx.tenant_id)
        db.add(item)
        db.commit()
        db.refresh(item)
    return item


def _serialize(db: Session, item: ScopeStatement) -> ScopeResponse:
    rows = db.query(ScopeItem).filter(ScopeItem.tenant_id == item.tenant_id, ScopeItem.scope_id == item.id).all()
    current = db.get(DocumentVersion, item.current_version_id) if item.current_version_id else None
    return ScopeResponse(
        id=item.id,
        interfaces_dependencies=item.interfaces_dependencies,
        context_version_ref=item.context_version_ref,
        stakeholder_version_ref=item.stakeholder_version_ref,
        draft_status=item.draft_status,
        current_version_id=item.current_version_id,
        items=rows,
        context_ref_obsolete=cds.is_superseded(db, item.context_version_ref),
        stakeholder_ref_obsolete=cds.is_superseded(db, item.stakeholder_version_ref),
        review_overdue=cds.review_overdue(current),
    )


@router.get("", response_model=ScopeResponse)
def get_scope(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    return _serialize(db, _get_or_create(db, ctx))


@router.put("", response_model=ScopeResponse)
def update_scope(
    payload: ScopeUpdate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    item = _get_or_create(db, ctx)
    item.interfaces_dependencies = payload.interfaces_dependencies
    item.context_version_ref = payload.context_version_ref
    item.stakeholder_version_ref = payload.stakeholder_version_ref
    db.commit()
    db.refresh(item)
    AuditService.log_from_request(
        request=request, operation="SCOPE_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="scope_statement", entity_id=item.id,
    )
    return _serialize(db, item)


@router.post("/items", status_code=status.HTTP_201_CREATED, response_model=ScopeItemResponse)
def create_item(
    payload: ScopeItemCreate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    scope = _get_or_create(db, ctx)
    item = ScopeItem(tenant_id=ctx.tenant_id, scope_id=scope.id, **payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    AuditService.log_from_request(
        request=request, operation="SCOPE_ITEM_CREATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="scope_item", entity_id=item.id,
    )
    return item


@router.post("/submit-review", response_model=ScopeResponse)
def submit_review(
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    item = cds.submit_review(db, _get_or_create(db, ctx))
    AuditService.log_from_request(
        request=request, operation="SCOPE_SUBMIT_REVIEW", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="scope_statement", entity_id=item.id,
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
        db=db, artifact=item, doc_type=DocType.scope_statement, actor_id=ctx.principal.user.id,
        classification=payload.classification, next_review_at=payload.next_review_at,
        change_nature=payload.change_nature, snapshot_factory=lambda: _serialize(db, item).model_dump(mode="json"),
    )
    AuditService.log_from_request(
        request=request, operation="SCOPE_APPROVE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="document_version", entity_id=version.id,
    )
    return version


@router.get("/versions", response_model=list[DocumentVersionResponse])
def versions(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    item = _get_or_create(db, ctx)
    return cds.list_versions(db, ctx.tenant_id, DocType.scope_statement, item.id)
