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

// --- Repositório transversal de evidências (Feature 014) ---
export type SgsiArtifactType = 'soa_item' | 'gap_item' | 'risk' | 'asset' | 'audit_finding';

export interface EvidenceLink {
  id: string;
  target_type: SgsiArtifactType;
  target_id: string;
  active: boolean;
}

export interface EvidenceSummary {
  id: string;
  title: string;
  description: string | null;
  classification: Classification;
  status: 'active' | 'inactive';
  current_version_id: string;
  file_name: string;
  mime_type: string | null;
  extension: string;
  size_bytes: number;
  content_hash: string;
  hash_algorithm: string;
  uploaded_by: string;
  uploaded_at: string;
  created_at: string;
  can_download: boolean;
  links: EvidenceLink[];
}

// --- Auditoria Interna (Feature 014, Fase 2) ---
export type InternalAuditStatus = 'planned' | 'in_progress' | 'completed' | 'cancelled';
export type AuditFindingType = 'conforme' | 'nc_maior' | 'nc_menor' | 'oportunidade_melhoria' | 'observacao';
export type AuditChecklistResult = 'conforme' | 'nao_conforme' | 'nao_aplicavel' | 'pendente';

export interface AuditProgram {
  id: string;
  name: string;
  objective: string | null;
  period_start: string | null;
  period_end: string | null;
  created_at: string;
}

export interface AuditSummary {
  id: string;
  program_id: string;
  code: string;
  title: string;
  status: InternalAuditStatus;
  auditor_member_id: string;
  period_start: string | null;
  period_end: string | null;
  current_version_id: string | null;
  draft_status: string;
}

export interface AuditReadiness {
  can_approve_report: boolean;
  pending_items: number;
  findings_count: number;
}

export interface AuditDetail extends AuditSummary {
  scope: string;
  criteria: string;
  readiness: AuditReadiness;
}

export interface AuditChecklistItem {
  id: string;
  audit_id: string;
  criterion: string;
  target_type: SgsiArtifactType | null;
  target_id: string | null;
  result: AuditChecklistResult;
  note: string | null;
  order_index: number;
}

export interface AuditFinding {
  id: string;
  audit_id: string;
  finding_type: AuditFindingType;
  title: string;
  description: string;
  checklist_item_id: string | null;
  target_type: SgsiArtifactType | null;
  target_id: string | null;
  promotable: boolean;
  nonconformity_ref: string | null;
  status: 'active' | 'inactive';
  evidence_links: EvidenceLink[];
}

export interface AuditReportVersion {
  id: string;
  version_number: number;
  status: string;
  classification: Classification;
  signed: boolean;
  approved_by: string | null;
  approved_at: string | null;
}

export interface AuditDashboardData {
  evidence_by_status: Record<string, number>;
  evidence_by_classification: Record<string, number>;
  audits_by_status: Record<string, number>;
  findings_by_type: Record<string, number>;
}

export type PrintableDocumentType =
  | 'context_report'
  | 'gap_report'
  | 'soa_report'
  | 'gap_baseline'
  | 'form_response';
export type PrintTemplateScope = 'system' | 'tenant';
export type PrintTemplateStatus = 'draft' | 'active' | 'inactive';
export type DocumentPreviewStatus = 'active' | 'expired' | 'stale' | 'signed';
export type SignedDocumentStatus = 'signed' | 'obsolete';
export type SignatureCoordinateSystem = 'pdf_points_bottom_left';
export type SignaturePlacementOrigin = 'default' | 'user' | 'template';
export type SignatureMethod =
  | 'internal_electronic_signature'
  | 'pades'
  | 'icp_brasil'
  | 'external_certificate_provider';

export interface PdfPageMetric {
  page_number: number;
  width_points: number;
  height_points: number;
  rotation: 0 | 90 | 180 | 270;
}

export interface SignatureBlockedArea {
  page: number | 'all';
  x_points: number;
  y_points: number;
  width_points: number;
  height_points: number;
  reason?: string | null;
}

export interface SignaturePlacementBase {
  page_number: number;
  x_points: number;
  y_points: number;
  width_points: number;
  height_points: number;
  page_width_points: number;
  page_height_points: number;
  coordinate_system: SignatureCoordinateSystem;
  origin: SignaturePlacementOrigin;
}

export interface SignaturePlacement extends SignaturePlacementBase {
  id: string;
  preview_id: string;
  placement_revision: number;
  placement_hash: string;
  created_by: string;
  created_at: string;
}

export interface SignedSignaturePlacement extends SignaturePlacementBase {
  id: string;
  signed_document_id: string;
  placement_id: string;
  placement_hash: string;
  created_at: string;
}

export interface PreviewLayout {
  preview_id: string;
  document_type: PrintableDocumentType;
  snapshot_hash: string;
  page_metrics: PdfPageMetric[];
  blocked_areas: SignatureBlockedArea[];
  default_placement: SignaturePlacementBase;
  latest_placement: SignaturePlacement | null;
}

export interface PrintTemplate {
  id: string;
  tenant_id: string | null;
  scope: PrintTemplateScope;
  document_type: PrintableDocumentType;
  name: string;
  description: string | null;
  status: PrintTemplateStatus;
  default_classification: Classification;
  current_version_id: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface PrintTemplateVersion {
  id: string;
  template_id: string;
  version_number: number;
  renderer: string;
  layout_schema: Record<string, unknown>;
  allowed_variables: Record<string, unknown>;
  required_sections: string[];
  content_hash: string;
  is_current: boolean;
  created_at: string;
}

export interface PrintTemplateVariable {
  id: string;
  tenant_id: string | null;
  scope: PrintTemplateScope;
  document_type: PrintableDocumentType;
  variable_key: string;
  label: string;
  description: string | null;
  value_type: string;
  required_by_default: boolean;
  optional_by_default: boolean;
  status: 'active' | 'inactive';
  sort_order: number;
  created_at: string;
  updated_at: string | null;
}

export interface DocumentPreview {
  id: string;
  document_type: PrintableDocumentType;
  source_artifact_id: string | null;
  template_version_id: string;
  classification: Classification;
  status: DocumentPreviewStatus;
  snapshot_hash: string;
  preview_pdf_hash: string;
  expires_at: string;
  created_at: string;
  warnings: string[];
  pdf_page_metrics: PdfPageMetric[];
  default_signature_placement: SignaturePlacementBase | null;
}

export interface SignedDocument {
  id: string;
  document_type: PrintableDocumentType;
  source_artifact_id: string | null;
  template_version_id: string;
  version_number: number;
  status: SignedDocumentStatus;
  classification: Classification;
  identifier: string;
  pdf_hash: string;
  snapshot_hash: string;
  size_bytes: number;
  signed_by: string;
  signed_at: string;
  signature_method: SignatureMethod;
  visual_signature_present: boolean;
  signature_placement: SignedSignaturePlacement | null;
}

export interface IntegrityVerification {
  valid: boolean;
  identifier: string;
  pdf_hash: string;
  snapshot_hash: string;
  verified_at: string;
}

export interface Diagnostic {
  id?: string;
  status: 'draft' | 'completed';
  sections: Record<string, unknown>;
}

export interface ContextIssue {
  id: string;
  origin: 'internal' | 'external';
  framework: 'pestel' | 'swot';
  nature: 'contextual' | 'strength' | 'weakness' | 'opportunity' | 'threat';
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

export interface GapDimensionMetric {
  conformance: number | null;
  adherence_evaluated: number | null;
  evaluated: number;
  total: number;
}

export interface GapDashboard {
  consolidated_conformance: number | null;
  total_items: number;
  evaluated_items: number;
  dimensions: Record<string, GapDimensionMetric>;
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

export type GapEvidenceStatus = 'active' | 'inactive';
export type GapEvidenceEventType =
  | 'uploaded'
  | 'content_viewed'
  | 'downloaded'
  | 'replaced'
  | 'inactivated'
  | 'access_denied';

export interface GapEvidenceSummary {
  id: string;
  assessment_item_id: string;
  title: string;
  description: string | null;
  classification: Classification;
  status: GapEvidenceStatus;
  current_version_id: string;
  file_name: string;
  mime_type: string | null;
  extension: string;
  size_bytes: number;
  content_hash: string;
  hash_algorithm: string;
  uploaded_by: string;
  uploaded_at: string;
  created_at: string;
  can_download: boolean;
}

export interface GapEvidenceVersionSummary {
  id: string;
  version_number: number;
  classification: Classification;
  file_name: string;
  mime_type: string | null;
  extension: string;
  size_bytes: number;
  content_hash: string;
  hash_algorithm: string;
  uploaded_by: string;
  uploaded_at: string;
  is_current: boolean;
}

export interface GapEvidenceEventSummary {
  id: string;
  event_type: GapEvidenceEventType;
  outcome: string;
  actor_id: string | null;
  occurred_at: string;
  details: Record<string, unknown> | null;
}

export interface GapEvidenceHistory {
  evidence: GapEvidenceSummary;
  versions: GapEvidenceVersionSummary[];
  events: GapEvidenceEventSummary[];
}

// --- Statement of Applicability / SoA (Feature 005) ---

export type SoaImplementationStatus =
  | 'implemented'
  | 'in_progress'
  | 'planned'
  | 'not_started'
  | 'not_applicable';

export type SoaInclusionReason = 'risk_treatment' | 'legal' | 'contractual' | 'best_practice';

export type SoaDivergenceSource = 'gap' | 'risk';
export type SoaKind = 'pre_soa' | 'normative';
export type SoaItemOrigin = 'risk' | 'manual' | 'risk+manual' | 'none';

export interface SoaDivergenceField {
  field: string;
  source: SoaDivergenceSource;
  soa_value: unknown;
  source_value: unknown;
  gap_value: unknown;
}

export interface SoaRiskLink {
  risk_id: string;
  risk_code: string;
}

export interface SoaItem {
  id: string;
  ref_code: string;
  theme: GapTheme | null;
  name: string;
  applicable: boolean;
  inclusion_reasons: SoaInclusionReason[];
  inclusion_note: string | null;
  exclusion_justification: string | null;
  implementation_status: SoaImplementationStatus | null;
  responsible: string | null;
  deadline: string | null;
  risks_treated: string | null;
  risk_links: SoaRiskLink[];
  origin: SoaItemOrigin;
  incomplete: boolean;
  expected_evidence: string | null;
  evidence_refs: string | null;
  observations: string | null;
  gap_assessment_item_id: string | null;
  divergence: SoaDivergenceField[];
}

export interface SoaSummary {
  total: number;
  applicable: number;
  not_applicable: number;
  divergent: number;
  risk_divergent: number;
  incomplete: number;
}

export interface SoaReadiness {
  kind: SoaKind;
  risk_plan_approved: boolean;
  pending_for_normative: string[];
  out_of_scope_risk_notices: string[];
}

export interface Soa {
  id: string;
  draft_status: string;
  current_version_id: string | null;
  gap_assessment_id: string | null;
  items: SoaItem[];
  summary: SoaSummary;
  readiness: SoaReadiness | null;
}

export interface SoaVersion {
  id: string;
  identifier: string;
  version_number: number;
  status: string;
  classification: string;
  next_review_at: string | null;
  change_nature: string;
  approved_by: string | null;
  is_superseded: boolean;
  signed: boolean;
  kind: SoaKind;
  created_at: string;
}

// --- Ativos / Processos / Escopo (Feature 011) ---

export type AssetType =
  | 'information_asset'
  | 'system'
  | 'database'
  | 'business_process'
  | 'infrastructure'
  | 'service'
  | 'supplier'
  | 'document'
  | 'person_team'
  | 'physical_environment'
  | 'other';

export type CiaLevel = 'baixa' | 'media' | 'alta' | 'critica';
export type AssetScopeStatus = 'in_scope' | 'out_of_scope' | 'under_analysis';
export type AssetRecordStatus = 'active' | 'in_review' | 'archived';
export type AssetReviewStatus = 'up_to_date' | 'due_soon' | 'overdue' | 'undefined';
export type AssetRelationshipType =
  | 'depends_on'
  | 'supports'
  | 'uses'
  | 'stores'
  | 'processes'
  | 'responsible_for'
  | 'operated_by'
  | 'regulated_by'
  | 'linked_to'
  | 'replaces'
  | 'other';

export interface AssetItem {
  id: string;
  code: string;
  name: string;
  item_type: AssetType;
  description: string | null;
  business_unit: string | null;
  responsible_user_id: string | null;
  owner_user_id: string | null;
  custodian_user_id: string | null;
  record_status: AssetRecordStatus;
  scope_status: AssetScopeStatus;
  scope_justification: string | null;
  location: string | null;
  related_system_id: string | null;
  related_process_id: string | null;
  related_supplier_id: string | null;
  has_personal_data: boolean;
  has_sensitive_data: boolean;
  compliance_notes: string | null;
  confidentiality: CiaLevel | null;
  integrity: CiaLevel | null;
  availability: CiaLevel | null;
  criticality: CiaLevel | null;
  criticality_is_manual: boolean;
  last_review_at: string | null;
  next_review_at: string | null;
  context_origin_type: string | null;
  context_origin_id: string | null;
  archived_at: string | null;
  archive_reason: string | null;
  created_by: string;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  review_status: AssetReviewStatus;
  criticality_computed: CiaLevel | null;
  criticality_divergent: boolean;
  cia_complete: boolean;
  pending_fields: string[];
}

export interface AssetRelationship {
  id: string;
  source_item_id: string;
  relationship_type: AssetRelationshipType;
  target_item_id: string;
  description: string | null;
  created_at: string;
  source_code: string | null;
  source_name: string | null;
  target_code: string | null;
  target_name: string | null;
  direction: 'outgoing' | 'incoming' | null;
}

export interface AssetGapLink {
  id: string;
  item_id: string;
  gap_catalog_item_id: string;
  note: string | null;
  created_at: string;
  gap_ref_code: string | null;
  gap_name: string | null;
  gap_is_discontinued: boolean | null;
}

export interface AssetItemEvent {
  id: string;
  item_id: string;
  event_type: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  actor_id: string | null;
  occurred_at: string;
  details: Record<string, unknown> | null;
}

export interface AssetItemDetail {
  item: AssetItem;
  relationships: AssetRelationship[];
  gap_links: AssetGapLink[];
}

export interface AssetSummary {
  total: number;
  assets: number;
  processes: number;
  suppliers: number;
  in_scope: number;
  critical: number;
  without_responsible: number;
  cia_incomplete: number;
}

export interface AssetDashboard {
  by_type: Record<string, number>;
  by_criticality: Record<string, number>;
  by_scope: Record<string, number>;
  by_review_status: Record<string, number>;
  with_personal_data: number;
  critical_without_review: number;
  without_responsible: number;
}

export interface AssetContextSource {
  origin_type: string;
  origin_id: string;
  label: string;
  description: string | null;
  suggested_item_type: AssetType | null;
}

// --- Gestão de Riscos (Feature 012) ---
export type RiskStatus = 'identified' | 'assessed' | 'in_treatment' | 'accepted' | 'closed';
export type RiskTreatmentOption = 'mitigate' | 'accept' | 'transfer' | 'avoid';
export type ThreatCategory = 'human' | 'environmental' | 'technical' | 'organizational';
export type ThreatOrigin = 'deliberate' | 'accidental' | 'environmental';
export type VulnerabilityCategory = 'technical' | 'physical' | 'organizational' | 'human' | 'process';

export interface RiskMethodology {
  is_configured: boolean;
  probability_scale: { order: number; label: string }[];
  impact_scale: { order: number; label: string }[];
  risk_levels: { key: string; label: string; severity: number; color: string; order: number }[];
  risk_matrix: Record<string, string>;
  acceptance: Record<string, boolean>;
  cia_impact_map: Record<string, number>;
}

export interface Threat {
  id: string;
  code: string;
  seed_item_id: string | null;
  name: string;
  description: string | null;
  category: ThreatCategory;
  origin: ThreatOrigin | null;
  is_custom: boolean;
  is_archived: boolean;
}

export interface Vulnerability {
  id: string;
  code: string;
  seed_item_id: string | null;
  name: string;
  description: string | null;
  category: VulnerabilityCategory;
  gap_catalog_item_id: string | null;
  is_custom: boolean;
  is_archived: boolean;
}

export interface Risk {
  id: string;
  code: string;
  title: string;
  description: string;
  threat_id: string;
  vulnerability_id: string;
  asset_item_ids: string[];
  probability_level: number | null;
  impact_level: number | null;
  impact_derived_level: number | null;
  impact_is_override: boolean;
  inherent_level_key: string | null;
  above_acceptance: boolean | null;
  owner_user_id: string | null;
  status: RiskStatus;
  treatment_option: RiskTreatmentOption | null;
  residual_probability_level: number | null;
  residual_impact_level: number | null;
  residual_level_key: string | null;
  residual_above_acceptance: boolean | null;
  is_archived: boolean;
}

export interface RiskControl {
  id: string;
  risk_id: string;
  gap_catalog_item_id: string | null;
  custom_control_label: string | null;
  responsible_user_id: string | null;
  due_date: string | null;
  note: string | null;
}

export interface RiskEvent {
  id: string;
  event_type: string;
  field_name: string | null;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  actor_id: string | null;
  occurred_at: string;
}

export interface HeatmapCell {
  probability: number;
  impact: number;
  level_key: string | null;
  count: number;
}

export interface RiskDashboard {
  heatmap: HeatmapCell[];
  by_level: Record<string, number>;
  top_risks: string[];
  without_treatment: number;
  accepted: number;
  residual_pending: number;
  by_owner: Record<string, number>;
  by_asset: Record<string, number>;
  inherent_vs_residual: { inherent_above: number; residual_above: number };
}

export interface SoaFeedItem {
  gap_catalog_item_id: string;
  ref_code: string | null;
  inclusion_reason: string;
  risk_ids: string[];
  risk_codes: string[];
}

export interface RiskPlan {
  id: string;
  draft_status: string;
  current_version_id: string | null;
}
