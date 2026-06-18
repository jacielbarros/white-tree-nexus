import { Role } from '@app/core/models';

/** Espelha a matriz de `wtnapp/helpers/permissions.py` (apenas para UX/guards no cliente;
 *  a autorização real é sempre validada no backend). */
const MATRIX: Record<Role, readonly string[]> = {
  super_admin: ['manage_organizations', 'invite_users', 'manage_memberships', 'view_organization'],
  org_admin: ['invite_users', 'manage_memberships', 'view_organization'],
  consultant: ['invite_users', 'view_organization'],
  client: ['view_organization'],
  manager: ['view_organization'],
  process_owner: ['view_organization'],
  control_owner: ['view_organization'],
  internal_auditor: ['view_organization'],
  guest_collaborator: ['view_organization'],
};

export function hasPermission(role: Role | null, permission: string): boolean {
  if (!role) {
    return false;
  }
  return MATRIX[role].includes(permission);
}
