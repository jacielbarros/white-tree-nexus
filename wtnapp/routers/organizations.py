"""Organizações: criação e ciclo de vida (Super Admin) + listagem/consulta escopada (FR-002..005)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_super_admin
from wtnapp.helpers.tenant_scope import Principal, get_current_principal
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.schemas.organization_schema import (
    OrganizationCreate,
    OrganizationResponse,
    OrgStatusChange,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, MembershipStatus, OrgStatus

router = APIRouter(prefix="/organizations", tags=["organizations"])

_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=OrganizationResponse)
def create_organization(
    request: Request,
    payload: OrganizationCreate,
    principal: Principal = Depends(require_super_admin()),
    db: Session = Depends(get_db),
) -> Organization:
    if db.query(Organization).filter(Organization.slug == payload.slug).first() is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")

    org = Organization(
        name=payload.name, slug=payload.slug, status=OrgStatus.active, created_by=principal.user.id
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    AuditService.log_from_request(
        request=request, operation="ORG_CREATE", outcome=AuditOutcome.success,
        actor_user_id=principal.user.id, actor_role="super_admin",
        tenant_id=org.id, entity_type="organization", entity_id=org.id,
    )
    return org


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> list[Organization]:
    # Super Admin vê todas; demais veem apenas as suas (FR-005).
    if principal.user.is_platform_super_admin:
        return db.query(Organization).order_by(Organization.created_at).all()

    org_ids = [
        m.tenant_id
        for m in db.query(Membership)
        .filter(Membership.user_id == principal.user.id, Membership.status == MembershipStatus.active)
        .all()
    ]
    if not org_ids:
        return []
    return db.query(Organization).filter(Organization.id.in_(org_ids)).all()


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: uuid.UUID,
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise _NOT_FOUND
    if not principal.user.is_platform_super_admin:
        is_member = (
            db.query(Membership)
            .filter(
                Membership.user_id == principal.user.id,
                Membership.tenant_id == org_id,
                Membership.status == MembershipStatus.active,
            )
            .first()
        )
        if is_member is None:
            raise _NOT_FOUND  # cross-tenant: não revela existência
    return org


@router.patch("/{org_id}/status", response_model=OrganizationResponse)
def change_organization_status(
    org_id: uuid.UUID,
    payload: OrgStatusChange,
    request: Request,
    principal: Principal = Depends(require_super_admin()),
    db: Session = Depends(get_db),
) -> Organization:
    org = db.get(Organization, org_id)
    if org is None:
        raise _NOT_FOUND

    org.status = OrgStatus.suspended if payload.action == "suspend" else OrgStatus.active
    db.commit()
    db.refresh(org)

    AuditService.log_from_request(
        request=request, operation="ORG_STATUS_CHANGE", outcome=AuditOutcome.success,
        actor_user_id=principal.user.id, actor_role="super_admin",
        tenant_id=org.id, entity_type="organization", entity_id=org.id,
        details={"action": payload.action},
    )
    return org
