"""Modelos ORM. Importados aqui para registrar em `Base.metadata` (create_all / Alembic)."""

from wtnapp.models.asset_item_model import AssetGapLink, AssetItem, AssetItemEvent, AssetRelationship
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.base import Base
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.models.context_analysis_model import ContextAnalysis, ContextIssue
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.document_version_model import DocumentVersion
# Evidências transversais (Feature 014)
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink, EvidenceVersion
# Auditoria Interna (Feature 014, Fase 2)
from wtnapp.models.internal_audit_model import (
    InternalAudit,
    InternalAuditChecklistItem,
    InternalAuditEvent,
    InternalAuditFinding,
    InternalAuditProgram,
)
from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.models.form_signature_model import FormSignature, FormSignatureOTP
from wtnapp.models.form_signature_policy_model import FormSignaturePolicy
from wtnapp.models.form_template_model import FormTemplate
# Gap Analysis (Feature 004)
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem, GapAssessmentItemEvent
from wtnapp.models.gap_assignment_model import GapAssignment
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.gap_guidance_event_model import GapGuidanceEvent
from wtnapp.models.gap_legend_model import GapLegendEntry
from wtnapp.models.gap_seed_model import GapSeedItem, GapSeedVersion
from wtnapp.models.invitation_model import Invitation
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.models.password_reset_model import PasswordResetToken
from wtnapp.models.print_document_model import (
    DocumentAccessEvent,
    DocumentPreview,
    DocumentSignature,
    DocumentSignaturePlacement,
    PrintTemplate,
    PrintTemplateVariable,
    PrintTemplateVersion,
    SignedDocument,
    SignedDocumentSignaturePlacement,
    SignedDocumentSnapshot,
)
from wtnapp.models.scope_model import ScopeItem, ScopeStatement
# Gestão de Riscos (Feature 012)
from wtnapp.models.risk_catalog_model import (
    AssetThreatLink,
    AssetVulnerabilityLink,
    OrgThreat,
    OrgVulnerability,
    ThreatSeedItem,
    VulnerabilitySeedItem,
)
from wtnapp.models.risk_methodology_model import RiskMethodology
from wtnapp.models.risk_model import Risk, RiskAssetLink, RiskEvent, RiskPlan, RiskTreatmentControl
# SoA (Feature 005)
from wtnapp.models.soa_model import Soa, SoaItem, SoaItemEvent
from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement
from wtnapp.models.user_model import User

__all__ = [
    "Base",
    "AssetItem",
    "AssetRelationship",
    "AssetGapLink",
    "AssetItemEvent",
    "AuditLog",
    "ClassificationAccessPolicy",
    "ContextAnalysis",
    "ContextIssue",
    "Diagnostic",
    "DocumentVersion",
    "Evidence",
    "EvidenceVersion",
    "EvidenceLink",
    "EvidenceEvent",
    "InternalAuditProgram",
    "InternalAudit",
    "InternalAuditChecklistItem",
    "InternalAuditFinding",
    "InternalAuditEvent",
    "FormAssignment",
    "FormAssignmentEvent",
    "FormSignature",
    "FormSignatureOTP",
    "FormSignaturePolicy",
    "FormTemplate",
    "GapAssessment",
    "GapAssessmentItem",
    "GapAssessmentItemEvent",
    "GapAssignment",
    "GapCatalogItem",
    "GapGuidanceEvent",
    "GapLegendEntry",
    "GapSeedItem",
    "GapSeedVersion",
    "Invitation",
    "Membership",
    "Organization",
    "PasswordResetToken",
    "DocumentAccessEvent",
    "DocumentPreview",
    "DocumentSignature",
    "DocumentSignaturePlacement",
    "PrintTemplate",
    "PrintTemplateVariable",
    "PrintTemplateVersion",
    "SignedDocument",
    "SignedDocumentSignaturePlacement",
    "SignedDocumentSnapshot",
    "ScopeItem",
    "ScopeStatement",
    "ThreatSeedItem",
    "VulnerabilitySeedItem",
    "OrgThreat",
    "OrgVulnerability",
    "AssetThreatLink",
    "AssetVulnerabilityLink",
    "RiskMethodology",
    "Risk",
    "RiskAssetLink",
    "RiskTreatmentControl",
    "RiskPlan",
    "RiskEvent",
    "Soa",
    "SoaItem",
    "SoaItemEvent",
    "Stakeholder",
    "StakeholderMap",
    "StakeholderRequirement",
    "User",
]
