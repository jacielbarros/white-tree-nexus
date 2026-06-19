"""RBAC granular (FR-024/FR-026). `require_permission(...)` é o ponto único de verificação.

Negação ⇒ 403 + audit. Super Admin tem todas as permissões da fundação, mas é auditado.
"""

from fastapi import Depends, HTTPException, Request, status

from wtnapp.helpers.tenant_scope import OrgContext, Principal, get_current_principal, get_org_context
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, Role

# Matriz papel → permissões (ver data-model.md §Papéis & Permissões).
PERMISSIONS: dict[Role, set[str]] = {
    Role.super_admin: {"manage_organizations", "invite_users", "manage_memberships", "view_organization"},
    Role.org_admin: {"invite_users", "manage_memberships", "view_organization"},
    Role.consultant: {"invite_users", "view_organization"},
    Role.client: {"view_organization"},
    Role.manager: {"view_organization"},
    Role.process_owner: {"view_organization"},
    Role.control_owner: {"view_organization"},
    Role.internal_auditor: {"view_organization"},
    Role.guest_collaborator: {"view_organization"},
}


def has_permission(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, set())


def require_permission(permission: str):
    """Factory de dependency. Retorna o `OrgContext` quando autorizado; 403 + audit se não."""

    def _dependency(
        request: Request,
        ctx: OrgContext = Depends(get_org_context),
    ) -> OrgContext:
        if not has_permission(ctx.role, permission):
            AuditService.log_from_request(
                request=request,
                operation="PERMISSION_DENIED",
                outcome=AuditOutcome.denied,
                actor_user_id=ctx.principal.user.id,
                actor_role=ctx.role.value,
                tenant_id=ctx.tenant_id,
                entity_type="permission",
                entity_id=permission,
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente.")
        return ctx

    return _dependency


def require_super_admin():
    """Dependency para ações de PLATAFORMA (sem contexto de org): só o Super Admin.

    Usada por bootstrap e ciclo de vida de organização, onde ainda não há `X-Org-Context`.
    """

    def _dependency(
        request: Request,
        principal: Principal = Depends(get_current_principal),
    ) -> Principal:
        if not principal.user.is_platform_super_admin:
            AuditService.log_from_request(
                request=request,
                operation="PERMISSION_DENIED",
                outcome=AuditOutcome.denied,
                actor_user_id=principal.user.id,
                entity_type="permission",
                entity_id="platform_super_admin",
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissão insuficiente.")
        return principal

    return _dependency
