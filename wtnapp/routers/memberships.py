"""Usuários/vínculos da organização: listar, mudar papel, ativar/desativar, desbloquear conta.

Salvaguardas FR-022 (nunca deixar a org sem admin) e FR-009a (desbloqueio manual auditado).
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.membership_model import Membership
from wtnapp.models.user_model import User
from wtnapp.schemas.invitation_schema import (
    MembershipResponse,
    MembershipStatusChange,
    RoleChangeRequest,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, MembershipStatus, Role

router = APIRouter(tags=["memberships"])

_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
_LAST_ADMIN = HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")


def _membership_in_context(db: Session, membership_id: uuid.UUID, ctx: OrgContext) -> Membership:
    m = db.get(Membership, membership_id)
    if m is None or m.tenant_id != ctx.tenant_id:
        raise _NOT_FOUND  # cross-tenant: não revela existência
    return m


def _active_admin_count(db: Session, tenant_id: uuid.UUID) -> int:
    return (
        db.query(Membership)
        .filter(
            Membership.tenant_id == tenant_id,
            Membership.role == Role.org_admin,
            Membership.status == MembershipStatus.active,
        )
        .count()
    )


def _to_response(m: Membership, user: User) -> MembershipResponse:
    return MembershipResponse(
        id=m.id, user_id=user.id, email=user.email, full_name=user.full_name,
        role=m.role.value, status=m.status.value, locked=user.locked_until is not None,
    )


@router.get("/users", response_model=list[MembershipResponse])
def list_users(
    ctx: OrgContext = Depends(require_permission("view_organization")),
    db: Session = Depends(get_db),
) -> list[MembershipResponse]:
    rows = db.query(Membership).filter(Membership.tenant_id == ctx.tenant_id).all()
    out = []
    for m in rows:
        user = db.get(User, m.user_id)
        if user is not None:
            out.append(_to_response(m, user))
    return out


@router.patch("/memberships/{membership_id}/role", response_model=MembershipResponse)
def change_role(
    membership_id: uuid.UUID,
    payload: RoleChangeRequest,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_memberships")),
    db: Session = Depends(get_db),
) -> MembershipResponse:
    m = _membership_in_context(db, membership_id, ctx)

    # FR-022: não remover o último org_admin ativo.
    removing_last_admin = (
        m.role == Role.org_admin
        and m.status == MembershipStatus.active
        and payload.role != Role.org_admin
        and _active_admin_count(db, ctx.tenant_id) <= 1
    )
    if removing_last_admin:
        raise _LAST_ADMIN

    # FR-020: papel não-Consultor não pode pertencer a usuário com múltiplos vínculos.
    if payload.role != Role.consultant:
        total = db.query(Membership).filter(Membership.user_id == m.user_id).count()
        if total > 1:
            raise _LAST_ADMIN

    m.role = payload.role
    db.commit()
    db.refresh(m)
    AuditService.log_from_request(
        request=request, operation="ROLE_CHANGE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="membership", entity_id=m.id,
        details={"new_role": payload.role.value},
    )
    return _to_response(m, db.get(User, m.user_id))


@router.patch("/memberships/{membership_id}/status", response_model=MembershipResponse)
def change_membership_status(
    membership_id: uuid.UUID,
    payload: MembershipStatusChange,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_memberships")),
    db: Session = Depends(get_db),
) -> MembershipResponse:
    m = _membership_in_context(db, membership_id, ctx)
    new_status = MembershipStatus(payload.status)

    disabling_last_admin = (
        m.role == Role.org_admin
        and m.status == MembershipStatus.active
        and new_status == MembershipStatus.disabled
        and _active_admin_count(db, ctx.tenant_id) <= 1
    )
    if disabling_last_admin:
        raise _LAST_ADMIN

    m.status = new_status
    db.commit()
    db.refresh(m)
    AuditService.log_from_request(
        request=request, operation="MEMBERSHIP_DISABLE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="membership", entity_id=m.id,
        details={"status": payload.status},
    )
    return _to_response(m, db.get(User, m.user_id))


@router.post("/users/{user_id}/unlock", status_code=status.HTTP_204_NO_CONTENT)
def unlock_user(
    user_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_memberships")),
    db: Session = Depends(get_db),
) -> Response:
    # O usuário-alvo precisa ter vínculo nesta organização (senão 404 cross-tenant).
    member = (
        db.query(Membership)
        .filter(Membership.user_id == user_id, Membership.tenant_id == ctx.tenant_id)
        .first()
    )
    if member is None:
        raise _NOT_FOUND
    user = db.get(User, user_id)
    if user is None:
        raise _NOT_FOUND

    user.failed_login_count = 0
    user.locked_until = None
    db.commit()
    AuditService.log_from_request(
        request=request, operation="ACCOUNT_UNLOCKED", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="user", entity_id=user_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
