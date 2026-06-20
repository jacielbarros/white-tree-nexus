"""CRUD de FormTemplate — visivel apenas ao tenant (T012)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.form_template_model import FormTemplate
from wtnapp.schemas.form_template_schema import (
    FormTemplateCreate,
    FormTemplateResponse,
    FormTemplateUpdate,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/form-templates", tags=["form-templates"])

db_dep = Annotated[Session, Depends(get_db)]
manage_dep = Annotated[OrgContext, Depends(require_permission("assign_form"))]
view_dep = Annotated[OrgContext, Depends(require_permission("view_form"))]


@router.post("", response_model=FormTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    body: FormTemplateCreate,
    ctx: manage_dep,
    db: db_dep,
    request: Request,
):
    tpl = FormTemplate(
        tenant_id=ctx.tenant_id,
        kind=body.kind,
        title=body.title,
        schema=body.schema,
        created_by=ctx.principal.user.id,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    AuditService.log_from_request(
        request=request, operation="CREATE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
        entity_type="form_template", entity_id=str(tpl.id),
    )
    return tpl


@router.get("", response_model=list[FormTemplateResponse])
def list_templates(ctx: view_dep, db: db_dep):
    return scoped_query(db, FormTemplate, ctx).all()


@router.get("/{template_id}", response_model=FormTemplateResponse)
def get_template(template_id: uuid.UUID, ctx: view_dep, db: db_dep):
    tpl = scoped_query(db, FormTemplate, ctx).filter(FormTemplate.id == template_id).first()
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template nao encontrado.")
    return tpl


@router.patch("/{template_id}", response_model=FormTemplateResponse)
def update_template(
    template_id: uuid.UUID,
    body: FormTemplateUpdate,
    ctx: manage_dep,
    db: db_dep,
    request: Request,
):
    tpl = scoped_query(db, FormTemplate, ctx).filter(FormTemplate.id == template_id).first()
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template nao encontrado.")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    AuditService.log_from_request(
        request=request, operation="UPDATE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
        entity_type="form_template", entity_id=str(tpl.id),
    )
    return tpl


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_template(
    template_id: uuid.UUID,
    ctx: manage_dep,
    db: db_dep,
    request: Request,
):
    tpl = scoped_query(db, FormTemplate, ctx).filter(FormTemplate.id == template_id).first()
    if tpl is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Template nao encontrado.")
    db.delete(tpl)
    db.commit()
    AuditService.log_from_request(
        request=request, operation="DELETE",
        outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
        entity_type="form_template", entity_id=str(template_id),
    )
