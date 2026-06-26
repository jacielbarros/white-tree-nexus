"""RBAC granular (FR-024/FR-026). `require_permission(...)` é o ponto único de verificação.

Negação ⇒ 403 + audit. Super Admin tem todas as permissões da fundação, mas é auditado.
"""

from fastapi import Depends, HTTPException, Request, status

from wtnapp.helpers.tenant_scope import OrgContext, Principal, get_current_principal, get_org_context
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, Role

# Matriz papel → permissões (ver data-model.md §Papéis & Permissões).
PERMISSIONS: dict[Role, set[str]] = {
    Role.super_admin: {
        "manage_organizations",
        "invite_users",
        "manage_memberships",
        "view_organization",
        "view_context",
        "manage_context",
        "approve_context_document",
        # Documentos imprimiveis/assinaveis (Feature 009)
        "manage_print_templates",
        # Motor de Workflow (Feature 003)
        "assign_form",
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        "manage_gap",
        "approve_gap_baseline",
        # SoA (Feature 005)
        "view_soa",
        "manage_soa",
        "approve_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
        "manage_asset",
    },
    Role.org_admin: {
        "invite_users",
        "manage_memberships",
        "view_organization",
        "view_context",
        "manage_context",
        "approve_context_document",
        # Documentos imprimiveis/assinaveis (Feature 009)
        "manage_print_templates",
        # Motor de Workflow (Feature 003)
        "assign_form",
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        "manage_gap",
        "approve_gap_baseline",
        # SoA (Feature 005)
        "view_soa",
        "manage_soa",
        "approve_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
        "manage_asset",
    },
    Role.consultant: {
        "invite_users",
        "view_organization",
        "view_context",
        "manage_context",
        # Motor de Workflow (Feature 003)
        "assign_form",
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        "manage_gap",
        # SoA (Feature 005)
        "view_soa",
        "manage_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
        "manage_asset",
    },
    Role.client: {
        "view_organization",
        "view_context",
        # Motor de Workflow (Feature 003) — fill/sign verificados por ownership no router
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        # SoA (Feature 005)
        "view_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
    },
    Role.manager: {
        "view_organization",
        "view_context",
        "manage_context",
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        # SoA (Feature 005)
        "view_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
    },
    Role.process_owner: {
        "view_organization",
        "view_context",
        "manage_context",
        "view_form",
        "fill_form",
        "sign_form",
        # Gap Analysis (Feature 004)
        "view_gap",
        # SoA (Feature 005)
        "view_soa",
        # Ativos / Processos / Escopo (Feature 011)
        "view_asset",
    },
    Role.control_owner: {"view_organization", "view_context", "view_form", "view_gap", "view_soa", "view_asset"},
    Role.internal_auditor: {"view_organization", "view_context", "view_form", "view_gap", "view_soa", "view_asset"},
    Role.guest_collaborator: {"view_organization", "view_context", "view_form"},
}

# Dashboard de Conformidade (Feature 006) — home agregada de leitura. Concedida a todos os papéis
# vinculados à organização, EXCETO Colaborador convidado (default da SEC-002; elevação por tenant
# para o convidado fica deferida — não há override de permissão por org no MVP).
for _role, _perms in PERMISSIONS.items():
    if _role is not Role.guest_collaborator:
        _perms.add("view_dashboard")


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
