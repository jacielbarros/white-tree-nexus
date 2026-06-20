"""Escopo de tenant central e não-contornável (FR-027/FR-028/FR-029).

- `get_current_principal`: resolve o usuário autenticado a partir do JWT (revogação + troca de senha).
- `get_org_context`: resolve/valida a organização-alvo (header `X-Org-Context`), fail-closed em
  org suspensa, audita acesso cross-tenant negado, e aplica `SET LOCAL app.tenant_id` (RLS no PG).
- `scoped_query`: toda query de domínio passa por aqui — filtra por `tenant_id` do contexto.

Cross-tenant por id ⇒ 404 genérico (não revela existência). Auth inválida ⇒ 401 genérico.
"""

import uuid
from dataclasses import dataclass
from datetime import timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session

from wtnapp import settings
from wtnapp.database.database import get_db
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.models.user_model import User
from wtnapp.services import token_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, MembershipStatus, OrgStatus, Role

_bearer = HTTPBearer(auto_error=False)

_UNAUTH = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado.")


@dataclass
class Principal:
    user: User
    jti: str
    exp_ts: int
    tenant_ids: list[uuid.UUID]
    is_super_admin: bool


@dataclass
class OrgContext:
    principal: Principal
    tenant_id: uuid.UUID
    role: Role
    is_super_admin: bool
    membership: Membership | None


def get_current_principal(
    request: Request,
    db: Session = Depends(get_db),
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> Principal:
    if creds is None or not creds.credentials:
        raise _UNAUTH
    claims = token_service.decode_token(creds.credentials)
    if not claims:
        raise _UNAUTH
    jti = claims.get("jti")
    if not jti or token_service.is_jti_revoked(jti):
        raise _UNAUTH
    try:
        user = db.get(User, uuid.UUID(str(claims.get("sub"))))
    except (ValueError, TypeError):
        raise _UNAUTH
    if user is None or user.status.value != "active":
        raise _UNAUTH

    # Tokens emitidos antes da última troca de senha são inválidos (R3).
    pca = user.password_changed_at
    if pca is not None:
        if pca.tzinfo is None:
            pca = pca.replace(tzinfo=timezone.utc)
        if int(claims.get("iat", 0)) < int(pca.timestamp()):
            raise _UNAUTH

    tenant_ids = [uuid.UUID(t) for t in claims.get("tenant_ids", [])]
    return Principal(
        user=user,
        jti=jti,
        exp_ts=int(claims.get("exp", 0)),
        tenant_ids=tenant_ids,
        is_super_admin=bool(claims.get("sa")),
    )


def _set_tenant_guc(db: Session, tenant_id: uuid.UUID) -> None:
    """Defesa em profundidade: seta `app.tenant_id` para as policies RLS (apenas PostgreSQL).

    Usa `set_config(..., is_local=true)` (equivalente a SET LOCAL, escopo de transação) porque o
    comando `SET` do PostgreSQL NÃO aceita bind parameters — `SET LOCAL app.tenant_id = :tid` falha
    com "syntax error at or near $1".
    """
    if db.bind is not None and db.bind.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})


def get_org_context(
    request: Request,
    db: Session = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> OrgContext:
    raw = request.headers.get(settings.ORG_CONTEXT_HEADER)

    def _audit_cross_tenant(target: str | None) -> None:
        AuditService.log_from_request(
            request=request,
            operation="CROSS_TENANT_DENIED",
            outcome=AuditOutcome.denied,
            actor_user_id=principal.user.id,
            actor_role="super_admin" if principal.is_super_admin else None,
            entity_type="organization",
            entity_id=target,
        )

    # --- Super Admin: único papel cross-tenant; opera 1 tenant por vez (R8/R10) ---
    if principal.is_super_admin:
        if not raw:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contexto de organização obrigatório.")
        try:
            target = uuid.UUID(raw)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contexto de organização inválido.")
        org = db.get(Organization, target)
        if org is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
        _set_tenant_guc(db, org.id)
        return OrgContext(
            principal=principal, tenant_id=org.id, role=Role.super_admin,
            is_super_admin=True, membership=None,
        )

    # --- Demais papéis: restrito aos vínculos ativos ---
    memberships = (
        db.query(Membership)
        .filter(Membership.user_id == principal.user.id, Membership.status == MembershipStatus.active)
        .all()
    )
    by_tenant = {m.tenant_id: m for m in memberships}

    if raw:
        try:
            chosen = uuid.UUID(raw)
        except ValueError:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contexto de organização inválido.")
        if chosen not in by_tenant:
            # Cross-tenant: não revela existência (404 genérico) + audit.
            _audit_cross_tenant(str(chosen))
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    elif len(by_tenant) == 1:
        chosen = next(iter(by_tenant))
    else:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contexto de organização obrigatório.")

    membership = by_tenant[chosen]
    org = db.get(Organization, chosen)
    if org is None or org.status == OrgStatus.suspended:
        # Suspensão é fail-closed (FR-004) — membro, mas org bloqueada.
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organização indisponível.")

    _set_tenant_guc(db, chosen)
    return OrgContext(
        principal=principal, tenant_id=chosen, role=membership.role,
        is_super_admin=False, membership=membership,
    )


def scoped_query(db: Session, model, ctx: OrgContext):
    """Query filtrada pelo tenant do contexto. Mesmo o Super Admin opera 1 tenant por vez."""
    return db.query(model).filter(model.tenant_id == ctx.tenant_id)
