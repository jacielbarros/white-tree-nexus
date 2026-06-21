import { Role } from '@app/core/models';

/** Espelha a matriz de `wtnapp/helpers/permissions.py` (apenas para UX/guards no cliente;
 *  a autorização real é sempre validada no backend). */
const MATRIX: Record<Role, readonly string[]> = {
  super_admin: ['manage_organizations', 'invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap', 'approve_gap_baseline'],
  org_admin: ['invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap', 'approve_gap_baseline'],
  consultant: ['invite_users', 'view_organization', 'view_context', 'manage_context', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap'],
  client: ['view_organization', 'view_context', 'fill_form', 'sign_form', 'view_form', 'view_gap'],
  manager: ['view_organization', 'view_context', 'manage_context', 'view_form', 'view_gap'],
  process_owner: ['view_organization', 'view_context', 'manage_context', 'view_form', 'view_gap'],
  control_owner: ['view_organization', 'view_context', 'view_form', 'view_gap'],
  internal_auditor: ['view_organization', 'view_context', 'view_form', 'view_gap'],
  guest_collaborator: ['view_organization', 'view_context'],
};

export function hasPermission(role: Role | null, permission: string): boolean {
  if (!role) {
    return false;
  }
  return MATRIX[role].includes(permission);
}
