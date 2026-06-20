"""Modelos ORM. Importados aqui para registrar em `Base.metadata` (create_all / Alembic)."""

from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.base import Base
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.models.context_analysis_model import ContextAnalysis, ContextIssue
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.form_assignment_event_model import FormAssignmentEvent
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.models.form_signature_model import FormSignature, FormSignatureOTP
from wtnapp.models.form_signature_policy_model import FormSignaturePolicy
from wtnapp.models.form_template_model import FormTemplate
from wtnapp.models.invitation_model import Invitation
from wtnapp.models.membership_model import Membership
from wtnapp.models.organization_model import Organization
from wtnapp.models.password_reset_model import PasswordResetToken
from wtnapp.models.scope_model import ScopeItem, ScopeStatement
from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement
from wtnapp.models.user_model import User

__all__ = [
    "Base",
    "AuditLog",
    "ClassificationAccessPolicy",
    "ContextAnalysis",
    "ContextIssue",
    "Diagnostic",
    "DocumentVersion",
    "FormAssignment",
    "FormAssignmentEvent",
    "FormSignature",
    "FormSignatureOTP",
    "FormSignaturePolicy",
    "FormTemplate",
    "Invitation",
    "Membership",
    "Organization",
    "PasswordResetToken",
    "ScopeItem",
    "ScopeStatement",
    "Stakeholder",
    "StakeholderMap",
    "StakeholderRequirement",
    "User",
]
