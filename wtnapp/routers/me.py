"""Contexto do usuário autenticado: /me (vínculos) e /me/context (org ativa validada)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.tenant_scope import OrgContext, Principal, get_current_principal, get_org_context
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.schemas.auth_schema import MeResponse, MembershipInfo, OrgContextResponse
from wtnapp.settings import MembershipStatus

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
def get_me(
    principal: Principal = Depends(get_current_principal),
    db: Session = Depends(get_db),
) -> MeResponse:
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == principal.user.id, Membership.status == MembershipStatus.active)
        .all()
    )
    infos = []
    for m in memberships:
        org = db.get(Organization, m.tenant_id)
        infos.append(
            MembershipInfo(tenant_id=m.tenant_id, org_name=org.name if org else "", role=m.role.value)
        )
    return MeResponse(
        user_id=principal.user.id,
        email=principal.user.email,
        full_name=principal.user.full_name,
        is_super_admin=principal.user.is_platform_super_admin,
        memberships=infos,
    )


@router.get("/me/context", response_model=OrgContextResponse)
def get_me_context(ctx: OrgContext = Depends(get_org_context)) -> OrgContextResponse:
    """Resolve a organização ativa (header X-Org-Context). Cross-tenant ⇒ 404 + audit."""
    return OrgContextResponse(
        tenant_id=ctx.tenant_id, role=ctx.role.value, is_super_admin=ctx.is_super_admin
    )
