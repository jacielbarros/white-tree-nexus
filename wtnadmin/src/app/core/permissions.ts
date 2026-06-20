import { Role } from '@app/core/models';

/** Espelha a matriz de `wtnapp/helpers/permissions.py` (apenas para UX/guards no cliente;
 *  a autorização real é sempre validada no backend). */
const MATRIX: Record<Role, readonly string[]> = {
  super_admin: ['manage_organizations', 'invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document'],
  org_admin: ['invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document'],
  consultant: ['invite_users', 'view_organization', 'view_context', 'manage_context'],
  client: ['view_organization', 'view_context'],
  manager: ['view_organization', 'view_context', 'manage_context'],
  process_owner: ['view_organization', 'view_context', 'manage_context'],
  control_owner: ['view_organization', 'view_context'],
  internal_auditor: ['view_organization', 'view_context'],
  guest_collaborator: ['view_organization', 'view_context'],
};

export function hasPermission(role: Role | null, permission: string): boolean {
  if (!role) {
    return false;
  }
  return MATRIX[role].includes(permission);
}
