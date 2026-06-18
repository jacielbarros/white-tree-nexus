"""Convites: criar/listar/revogar/reenviar (papéis autorizados) e aceitar (público).

Token só por e-mail (apenas hash persistido). Aceite ativa o vínculo e define a senha,
respeitando a invariante FR-020 (só Consultor é multi-org).
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp import settings
from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.invitation_model import Invitation
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.models.user_model import User
from wtnapp.schemas.auth_schema import TokenResponse
from wtnapp.schemas.invitation_schema import (
    AcceptInviteRequest,
    InvitationCreate,
    InvitationResponse,
)
from wtnapp.services import crypto_service, notification_service, token_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, InviteStatus, MembershipStatus, OrgStatus, Role, UserStatus

router = APIRouter(prefix="/invitations", tags=["invitations"])

_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
_BAD_INVITE = HTTPException(status.HTTP_400_BAD_REQUEST, "Convite inválido.")


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _check_fr020(db: Session, user: User, new_role: Role) -> None:
    """FR-020: só Consultor admite múltiplos vínculos; qualquer outro papel ⇒ vínculo único."""
    existing = db.query(Membership).filter(Membership.user_id == user.id).all()
    if not existing:
        return
    if new_role != Role.consultant:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")
    # novo papel é Consultor: só permitido se TODOS os vínculos existentes também forem Consultor
    if any(m.role != Role.consultant for m in existing):
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")


@router.post("", status_code=status.HTTP_201_CREATED, response_model=InvitationResponse)
def create_invitation(
    request: Request,
    payload: InvitationCreate,
    ctx: OrgContext = Depends(require_permission("invite_users")),
    db: Session = Depends(get_db),
) -> Invitation:
    email = payload.email.strip().lower()

    # Já é membro ativo desta organização?
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user is not None:
        already = (
            db.query(Membership)
            .filter(
                Membership.user_id == existing_user.id,
                Membership.tenant_id == ctx.tenant_id,
                Membership.status == MembershipStatus.active,
            )
            .first()
        )
        if already is not None:
            raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")

    # Já existe convite pendente para (tenant, email)?
    pending = (
        db.query(Invitation)
        .filter(
            Invitation.tenant_id == ctx.tenant_id,
            Invitation.email == email,
            Invitation.status == InviteStatus.pending,
        )
        .first()
    )
    if pending is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")

    raw_token = crypto_service.generate_opaque_token()
    invite = Invitation(
        tenant_id=ctx.tenant_id,
        email=email,
        role=payload.role,
        invited_by=ctx.principal.user.id,
        token_hash=crypto_service.hash_token(raw_token),
        status=InviteStatus.pending,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_EXPIRY_HOURS),
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    org = db.get(Organization, ctx.tenant_id)
    notification_service.send_invite_email(
        to_email=email, token=raw_token, org_name=org.name if org else "", role=payload.role.value
    )

    AuditService.log_from_request(
        request=request, operation="USER_INVITE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="invitation", entity_id=invite.id,
    )
    return invite


@router.get("", response_model=list[InvitationResponse])
def list_invitations(
    ctx: OrgContext = Depends(require_permission("invite_users")),
    db: Session = Depends(get_db),
) -> list[Invitation]:
    return db.query(Invitation).filter(Invitation.tenant_id == ctx.tenant_id).all()


@router.post("/accept", response_model=TokenResponse)
def accept_invitation(
    request: Request, payload: AcceptInviteRequest, db: Session = Depends(get_db)
) -> TokenResponse:
    invite = (
        db.query(Invitation)
        .filter(Invitation.token_hash == crypto_service.hash_token(payload.token))
        .first()
    )
    if invite is None or invite.status != InviteStatus.pending:
        AuditService.log_from_request(
            request=request, operation="INVITE_ACCEPT", outcome=AuditOutcome.denied,
            entity_type="invitation", details={"reason": "invalid_or_used"},
        )
        raise _BAD_INVITE

    if _aware(invite.expires_at) < datetime.now(timezone.utc):
        invite.status = InviteStatus.expired
        db.commit()
        AuditService.log_from_request(
            request=request, operation="INVITE_ACCEPT", outcome=AuditOutcome.denied,
            tenant_id=invite.tenant_id, entity_type="invitation", entity_id=invite.id,
            details={"reason": "expired"},
        )
        raise _BAD_INVITE

    if len(payload.password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Senha não atende à política mínima.")

    now = datetime.now(timezone.utc)
    user = db.query(User).filter(User.email == invite.email).first()
    if user is None:
        user = User(
            email=invite.email, full_name=payload.full_name,
            password_hash=crypto_service.hash_password(payload.password),
            status=UserStatus.active, password_changed_at=now,
        )
        db.add(user)
        db.flush()  # garante user.id
    else:
        _check_fr020(db, user, invite.role)
        user.full_name = payload.full_name
        user.password_hash = crypto_service.hash_password(payload.password)
        user.status = UserStatus.active
        user.password_changed_at = now

    db.add(
        Membership(
            tenant_id=invite.tenant_id, user_id=user.id, role=invite.role,
            status=MembershipStatus.active, invited_by=invite.invited_by,
        )
    )
    invite.status = InviteStatus.accepted
    invite.accepted_at = now
    db.commit()
    db.refresh(user)

    AuditService.log_from_request(
        request=request, operation="INVITE_ACCEPT", outcome=AuditOutcome.success,
        actor_user_id=user.id, tenant_id=invite.tenant_id,
        entity_type="invitation", entity_id=invite.id,
    )

    # Auto-login: token com as orgs ativas do usuário.
    active_tenant_ids = []
    for m in db.query(Membership).filter(
        Membership.user_id == user.id, Membership.status == MembershipStatus.active
    ).all():
        org = db.get(Organization, m.tenant_id)
        if org is not None and org.status == OrgStatus.active:
            active_tenant_ids.append(m.tenant_id)

    access_token, _jti, expires_in = token_service.create_access_token(
        user_id=user.id, tenant_ids=active_tenant_ids, super_admin=user.is_platform_super_admin
    )
    return TokenResponse(access_token=access_token, expires_in=expires_in)


def _load_pending_in_context(db: Session, invitation_id: uuid.UUID, ctx: OrgContext) -> Invitation:
    invite = db.get(Invitation, invitation_id)
    if invite is None or invite.tenant_id != ctx.tenant_id:
        raise _NOT_FOUND  # cross-tenant: não revela existência
    return invite


@router.post("/{invitation_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_permission("invite_users")),
    db: Session = Depends(get_db),
) -> Response:
    invite = _load_pending_in_context(db, invitation_id, ctx)
    if invite.status == InviteStatus.pending:
        invite.status = InviteStatus.revoked
        db.commit()
    AuditService.log_from_request(
        request=request, operation="INVITE_REVOKE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="invitation", entity_id=invite.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{invitation_id}/resend", status_code=status.HTTP_202_ACCEPTED)
def resend_invitation(
    invitation_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_permission("invite_users")),
    db: Session = Depends(get_db),
) -> dict:
    invite = _load_pending_in_context(db, invitation_id, ctx)
    if invite.status != InviteStatus.pending:
        raise _BAD_INVITE

    # Novo token (o anterior não é recuperável) + nova validade.
    raw_token = crypto_service.generate_opaque_token()
    invite.token_hash = crypto_service.hash_token(raw_token)
    invite.expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.INVITE_EXPIRY_HOURS)
    db.commit()

    org = db.get(Organization, ctx.tenant_id)
    notification_service.send_invite_email(
        to_email=invite.email, token=raw_token, org_name=org.name if org else "", role=invite.role.value
    )
    AuditService.log_from_request(
        request=request, operation="USER_INVITE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type="invitation", entity_id=invite.id,
        details={"action": "resend"},
    )
    return {"status": "accepted"}
