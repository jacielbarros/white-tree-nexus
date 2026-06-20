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

export interface InviteLookup {
  org_name: string;
  role: string;
  email: string;
  requires_password: boolean;
}

export type Level = 'alto' | 'medio' | 'baixo';
export type Classification = 'publico' | 'uso_interno' | 'confidencial' | 'restrito';

export interface Diagnostic {
  id?: string;
  status: 'draft' | 'completed';
  sections: Record<string, unknown>;
}

export interface ContextIssue {
  id: string;
  origin: 'internal' | 'external';
  framework: 'pestel' | 'swot';
  category: string;
  description: string;
  impact: Level;
}

export interface ContextAnalysis {
  id: string;
  intended_outcomes: string;
  methodology?: string | null;
  draft_status: string;
  current_version_id?: string | null;
  issues: ContextIssue[];
  review_overdue: boolean;
}

export interface Stakeholder {
  id: string;
  name: string;
  type: 'internal' | 'external';
  power: Level;
  interest: Level;
  strategy: string;
  requirements: { id: string; type: string; description: string; how_addressed: string }[];
}

export interface StakeholderMap {
  id: string;
  draft_status: string;
  current_version_id?: string | null;
  stakeholders: Stakeholder[];
  review_overdue: boolean;
}

export interface ScopeStatement {
  id: string;
  interfaces_dependencies: string;
  context_version_ref?: string | null;
  stakeholder_version_ref?: string | null;
  draft_status: string;
  current_version_id?: string | null;
  items: { id: string; kind: 'inclusion' | 'exclusion'; description: string; justification: string }[];
  context_ref_obsolete: boolean;
  stakeholder_ref_obsolete: boolean;
  review_overdue: boolean;
}

export interface DocumentVersion {
  id: string;
  identifier: string;
  version_number: number;
  status: string;
  classification: Classification;
  emitted_at: string;
  next_review_at?: string | null;
}

export interface Suggestion {
  id: string;
  target: string;
  payload: Record<string, unknown>;
  reason: string;
}

// --- Motor de Workflow de Preenchimento (Feature 003) ---

export type FormKind = 'diagnostic' | 'gap_analysis' | 'generic';
export type TemplateStatus = 'draft' | 'active' | 'archived';
export type AssignmentStatus =
  | 'pending'
  | 'in_progress'
  | 'submitted'
  | 'signed'
  | 'completed'
  | 'cancelled';

export interface FormField {
  label: string;
  key: string;
  type: 'text' | 'textarea' | 'boolean' | 'number' | 'select';
  required?: boolean;
  options?: string[];
  help_text?: string;
  mask?: string;
  section?: string;
  order?: number;
}

export interface FormTemplate {
  id: string;
  kind: FormKind;
  title: string;
  schema: FormField[];
  status: TemplateStatus;
  created_at: string;
  updated_at: string;
}

export interface FormAssignment {
  id: string;
  template_id: string;
  kind: FormKind;
  title: string;
  fields_snapshot: FormField[];
  status: AssignmentStatus;
  respondent_user_id: string | null;
  respondent_email: string | null;
  deadline_at: string | null;
  overdue: boolean;
  answers: Record<string, unknown>;
  current_version_id: string | null;
  claimed_at: string | null;
  submitted_at: string | null;
  signed_at: string | null;
  instructions: string | null;
}

export interface AssignmentEvent {
  id: string;
  event: string;
  actor_label: string | null;
  note: string | null;
  created_at: string;
}

export interface FormSignature {
  id: string;
  signer_role: 'filler' | 'assigner';
  signer_name: string;
  signed_at: string;
  content_hash: string;
  level: string;
  otp_verified: boolean;
}

export interface SignaturePolicy {
  require_assigner_countersignature: boolean;
}
