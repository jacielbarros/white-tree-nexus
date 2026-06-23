import { Role } from '@app/core/models';

/** Espelha a matriz de `wtnapp/helpers/permissions.py` (apenas para UX/guards no cliente;
 *  a autorização real é sempre validada no backend). */
const MATRIX: Record<Role, readonly string[]> = {
  super_admin: ['manage_organizations', 'invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document', 'manage_print_templates', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap', 'approve_gap_baseline', 'view_soa', 'manage_soa', 'approve_soa', 'view_dashboard'],
  org_admin: ['invite_users', 'manage_memberships', 'view_organization', 'view_context', 'manage_context', 'approve_context_document', 'manage_print_templates', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap', 'approve_gap_baseline', 'view_soa', 'manage_soa', 'approve_soa', 'view_dashboard'],
  consultant: ['invite_users', 'view_organization', 'view_context', 'manage_context', 'assign_form', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'manage_gap', 'view_soa', 'manage_soa', 'view_dashboard'],
  client: ['view_organization', 'view_context', 'fill_form', 'sign_form', 'view_form', 'view_gap', 'view_soa', 'view_dashboard'],
  manager: ['view_organization', 'view_context', 'manage_context', 'view_form', 'view_gap', 'view_soa', 'view_dashboard'],
  process_owner: ['view_organization', 'view_context', 'manage_context', 'view_form', 'view_gap', 'view_soa', 'view_dashboard'],
  control_owner: ['view_organization', 'view_context', 'view_form', 'view_gap', 'view_soa', 'view_dashboard'],
  internal_auditor: ['view_organization', 'view_context', 'view_form', 'view_gap', 'view_soa', 'view_dashboard'],
  guest_collaborator: ['view_organization', 'view_context'],
};

export function hasPermission(role: Role | null, permission: string): boolean {
  if (!role) {
    return false;
  }
  return MATRIX[role].includes(permission);
}
