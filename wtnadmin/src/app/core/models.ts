export type Role =
  | 'super_admin'
  | 'org_admin'
  | 'consultant'
  | 'client'
  | 'manager'
  | 'process_owner'
  | 'control_owner'
  | 'internal_auditor'
  | 'guest_collaborator';

export const ROLES: Role[] = [
  'super_admin',
  'org_admin',
  'consultant',
  'client',
  'manager',
  'process_owner',
  'control_owner',
  'internal_auditor',
  'guest_collaborator',
];

export interface MembershipInfo {
  tenant_id: string;
  org_name: string;
  role: Role;
}

export interface Me {
  user_id: string;
  email: string;
  full_name: string;
  is_super_admin: boolean;
  memberships: MembershipInfo[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface Organization {
  id: string;
  name: string;
  slug: string;
  status: 'active' | 'suspended';
  created_at: string;
}

export interface MembershipRow {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  status: 'active' | 'disabled';
  locked: boolean;
}

export interface Invitation {
  id: string;
  email: string;
  role: Role;
  status: string;
  expires_at: string;
}
