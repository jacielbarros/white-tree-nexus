"""Autenticação: login (com bloqueio) e logout. Rate limited. Erros genéricos (FR-011)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp import settings
from wtnapp.database.database import get_db
from wtnapp.helpers.tenant_scope import Principal, get_current_principal
from wtnapp.limiter import limiter
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.models.password_reset_model import PasswordResetToken
from wtnapp.models.user_model import User
from wtnapp.schemas.auth_schema import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from wtnapp.services import crypto_service, notification_service, token_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, MembershipStatus, OrgStatus, UserStatus

router = APIRouter(prefix="/auth", tags=["auth"])

_INVALID = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas.")


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_AUTH)
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    now = datetime.now(timezone.utc)

    def audit_fail(reason: str, user_id=None) -> None:
        AuditService.log_from_request(
            request=request, operation="LOGIN_FAILED", outcome=AuditOutcome.denied,
            actor_user_id=user_id, entity_type="user", entity_id=user_id,
            details={"reason": reason},
        )

    # Conta bloqueada (auto-expira quando locked_until < now) — FR-009/FR-009a
    if user is not None:
        locked_until = _aware(user.locked_until)
        if locked_until is not None and locked_until > now:
            audit_fail("locked", user.id)
            raise _INVALID

    # Credencial inválida (e-mail inexistente OU senha errada) — mesma resposta (FR-011)
    if user is None or not crypto_service.verify_password(payload.password, user.password_hash):
        if user is not None:
            user.failed_login_count += 1
            just_locked = user.failed_login_count >= settings.MAX_LOGIN_ATTEMPTS
            if just_locked:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_DURATION_MINUTES)
            db.commit()
            audit_fail("bad_password", user.id)
            if just_locked:
                AuditService.log_from_request(
                    request=request, operation="ACCOUNT_LOCKED", outcome=AuditOutcome.denied,
                    actor_user_id=user.id, entity_type="user", entity_id=user.id,
                )
        else:
            audit_fail("unknown_email")
        raise _INVALID

    if user.status != UserStatus.active:
        audit_fail("inactive", user.id)
        raise _INVALID

    # Organizações utilizáveis (vínculo ativo + org ativa) — suspensão é fail-closed (FR-004)
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == user.id, Membership.status == MembershipStatus.active)
        .all()
    )
    active_tenant_ids = []
    for m in memberships:
        org = db.get(Organization, m.tenant_id)
        if org is not None and org.status == OrgStatus.active:
            active_tenant_ids.append(m.tenant_id)

    if not user.is_platform_super_admin and not active_tenant_ids:
        audit_fail("no_active_org", user.id)
        raise _INVALID

    # Sucesso: zera bloqueio, emite token.
    user.failed_login_count = 0
    user.locked_until = None
    db.commit()

    access_token, _jti, expires_in = token_service.create_access_token(
        user_id=user.id, tenant_ids=active_tenant_ids, super_admin=user.is_platform_super_admin
    )
    AuditService.log_from_request(
        request=request, operation="LOGIN", outcome=AuditOutcome.success,
        actor_user_id=user.id, actor_role="super_admin" if user.is_platform_super_admin else None,
        tenant_id=active_tenant_ids[0] if len(active_tenant_ids) == 1 else None,
        entity_type="user", entity_id=user.id,
    )
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.post("/password/forgot", status_code=status.HTTP_202_ACCEPTED)
@limiter.limit(settings.RATE_LIMIT_PASSWORD_REQUEST)
def forgot_password(
    request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)
) -> dict:
    """Resposta sempre genérica (FR-013) — não revela se o e-mail existe."""
    email = payload.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is not None:
        raw_token = crypto_service.generate_opaque_token()
        db.add(
            PasswordResetToken(
                user_id=user.id,
                token_hash=crypto_service.hash_token(raw_token),
                expires_at=datetime.now(timezone.utc)
                + timedelta(minutes=settings.RESET_TOKEN_EXPIRY_MINUTES),
            )
        )
        db.commit()
        notification_service.send_password_reset_email(to_email=email, token=raw_token)
        AuditService.log_from_request(
            request=request, operation="PWD_RESET_REQUEST", outcome=AuditOutcome.success,
            actor_user_id=user.id, entity_type="user", entity_id=user.id,
        )
    return {"status": "accepted"}


@router.post("/password/reset", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)
) -> Response:
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == crypto_service.hash_token(payload.token))
        .first()
    )
    now = datetime.now(timezone.utc)
    if record is None or record.used_at is not None or _aware(record.expires_at) < now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Token inválido ou expirado.")
    if len(payload.password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Senha não atende à política mínima.")

    user = db.get(User, record.user_id)
    user.password_hash = crypto_service.hash_password(payload.password)
    user.password_changed_at = now  # invalida tokens anteriores (FR-014)
    user.failed_login_count = 0  # reset também limpa bloqueio (FR-009a)
    user.locked_until = None
    record.used_at = now
    db.commit()

    AuditService.log_from_request(
        request=request, operation="PWD_RESET_COMPLETE", outcome=AuditOutcome.success,
        actor_user_id=user.id, entity_type="user", entity_id=user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, principal: Principal = Depends(get_current_principal)) -> Response:
    now_ts = int(datetime.now(timezone.utc).timestamp())
    token_service.revoke_jti(principal.jti, max(principal.exp_ts - now_ts, 1))
    AuditService.log_from_request(
        request=request, operation="LOGOUT", outcome=AuditOutcome.success,
        actor_user_id=principal.user.id, entity_type="user", entity_id=principal.user.id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
