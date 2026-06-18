"""Bootstrap do 1º Super Admin (FR-001) — uma única vez, guardado por BOOTSTRAP_TOKEN (R8)."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp import settings
from wtnapp.database.database import get_db
from wtnapp.models.user_model import User
from wtnapp.schemas.auth_schema import MeResponse
from wtnapp.schemas.organization_schema import BootstrapRequest
from wtnapp.services import crypto_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, UserStatus

router = APIRouter(prefix="/bootstrap", tags=["bootstrap"])


@router.post("/super-admin", status_code=status.HTTP_201_CREATED, response_model=MeResponse)
def bootstrap_super_admin(
    request: Request, payload: BootstrapRequest, db: Session = Depends(get_db)
) -> MeResponse:
    # Duplo gate: segredo correto + nenhum Super Admin existente (R8).
    if not settings.BOOTSTRAP_TOKEN or payload.bootstrap_token != settings.BOOTSTRAP_TOKEN:
        AuditService.log_from_request(
            request=request, operation="BOOTSTRAP", outcome=AuditOutcome.denied,
            entity_type="user", details={"reason": "bad_token"},
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Não autorizado.")

    if db.query(User).filter(User.is_platform_super_admin.is_(True)).first() is not None:
        AuditService.log_from_request(
            request=request, operation="BOOTSTRAP", outcome=AuditOutcome.denied,
            entity_type="user", details={"reason": "already_exists"},
        )
        raise HTTPException(status.HTTP_409_CONFLICT, "Conflito de dados.")

    if len(payload.password) < settings.PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, "Senha não atende à política mínima."
        )

    user = User(
        email=payload.email.strip().lower(),
        full_name=payload.full_name,
        password_hash=crypto_service.hash_password(payload.password),
        status=UserStatus.active,
        is_platform_super_admin=True,
        password_changed_at=datetime.now(timezone.utc),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    AuditService.log_from_request(
        request=request, operation="BOOTSTRAP", outcome=AuditOutcome.success,
        actor_user_id=user.id, actor_role="super_admin", entity_type="user", entity_id=user.id,
    )
    return MeResponse(
        user_id=user.id, email=user.email, full_name=user.full_name,
        is_super_admin=True, memberships=[],
    )
