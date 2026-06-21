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

// --- Gap Analysis (Feature 004) ---

export type GapStatus =
  | 'not_filled'
  | 'meets'
  | 'partial'
  | 'not_meet'
  | 'not_applicable';

export type GapPriority = 'critical' | 'high' | 'medium' | 'low';
export type GapDimension = 'clause' | 'annex_a';
export type GapTheme = 'organizational' | 'people' | 'physical' | 'technological';

export interface GapCatalogItem {
  id: string;
  dimension: GapDimension;
  ref_code: string;
  name: string;
  theme: GapTheme | null;
  objective: string | null;
  order: number;
  is_custom: boolean;
  is_discontinued: boolean;
}

export interface GapAssessmentItem {
  id: string;
  catalog_item_id: string;
  ref_code: string;
  dimension: GapDimension;
  theme: GapTheme | null;
  name: string;
  status: GapStatus;
  findings: string | null;
  actions: string | null;
  priority: GapPriority | null;
  responsible: string | null;
  deadline: string | null;
  evidence_ref: string | null;
  notes: string | null;
  exclusion_justification: string | null;
  maturity_level: number | null;
  effort_estimate: string | null;
  soa_ref: string | null;
}

export interface GapAssessment {
  id: string;
  draft_status: string;
  current_version_id: string | null;
  items: GapAssessmentItem[];
}

export interface GapDashboard {
  overall_adherence: number | null;
  by_dimension: Record<string, number | null>;
  by_clause: Record<string, number | null>;
  by_theme: Record<string, number | null>;
  status_distribution: Record<string, number>;
  completeness: number;
}

export interface GapBaseline {
  id: string;
  version_number: number;
  status: string;
  classification: string;
  emitted_at: string;
  overall_adherence: number | null;
}

export interface GapBaselineComparison {
  from_baseline: GapBaseline;
  to_baseline: GapBaseline;
  overall_delta: number | null;
  by_dimension_delta: Record<string, number | null>;
}

export interface GapAssignmentItem {
  id: string;
  assessment_id: string;
  scope: string;
  scope_theme: string | null;
  status: string;
  respondent_user_id: string | null;
  respondent_email: string | null;
  deadline_at: string | null;
  instructions: string | null;
  claimed_at: string | null;
  submitted_at: string | null;
  signed_at: string | null;
  created_at: string;
  token?: string | null;
}
