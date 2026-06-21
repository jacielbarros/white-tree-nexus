"""Gap Catalog router — catálogo da org (GET + adotar seed + CRUD próprio)."""

from typing import Annotated

import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.schemas.gap_catalog_schema import (
    CatalogAdoptRequest,
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.services.gap_seed_service import adopt_seed

router = APIRouter(prefix="/gap/catalog", tags=["gap-catalog"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_gap"))]


@router.get("", response_model=list[CatalogItemResponse])
def list_catalog(
    db: db_dep,
    ctx: view_dep,
    dimension: str | None = None,
    theme: str | None = None,
):
    q = db.query(GapCatalogItem).filter(GapCatalogItem.tenant_id == ctx.tenant_id)
    if dimension:
        q = q.filter(GapCatalogItem.dimension == dimension)
    if theme:
        q = q.filter(GapCatalogItem.theme == theme)
    return q.order_by(GapCatalogItem.order).all()


@router.post("/adopt")
def adopt_catalog(
    body: CatalogAdoptRequest,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    result = adopt_seed(db, ctx.tenant_id, body.seed_version)
    AuditService.log_from_request(
        request=request,
        operation="ADOPT_GAP_SEED",
        entity_type="gap_catalog",
        entity_id=str(ctx.tenant_id),
        details={"seed_version": body.seed_version, **result},
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return result


@router.post("/items", response_model=CatalogItemResponse, status_code=201)
def create_catalog_item(
    body: CatalogItemCreate,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    item = GapCatalogItem(
        tenant_id=ctx.tenant_id,
        is_custom=True,
        **body.model_dump(),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    AuditService.log_from_request(
        request=request,
        operation="CREATE",
        entity_type="gap_catalog_item",
        entity_id=str(item.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return item


@router.patch("/items/{item_id}", response_model=CatalogItemResponse)
def update_catalog_item(
    item_id: uuid.UUID,
    body: CatalogItemUpdate,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    from wtnapp.helpers.tenant_scope import scoped_query
    item = scoped_query(db, GapCatalogItem, ctx).filter(GapCatalogItem.id == item_id).first()
    if item is None:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado.")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    AuditService.log_from_request(
        request=request,
        operation="UPDATE",
        entity_type="gap_catalog_item",
        entity_id=str(item.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return item
