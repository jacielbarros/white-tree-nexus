"""Configuração central — lê `.env` via `load_dotenv()` (NÃO usar pydantic-settings).

Enums de domínio e parâmetros operacionais configuráveis. Ver constitution §Configurabilidade.
"""

import os
from enum import Enum

from dotenv import load_dotenv

load_dotenv()


def _bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    try:
        return int(raw) if raw not in (None, "") else default
    except ValueError:
        return default


# --- Core ---
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-secret-change-me")
JWT_ALGORITHM = "HS512"
JWT_ISSUER = os.getenv("JWT_ISSUER", "white-tree-nexus")
TOKEN_EXPIRY_MINUTES = _int("TOKEN_EXPIRY_MINUTES", 20)
RESET_TOKEN_EXPIRY_MINUTES = _int("RESET_TOKEN_EXPIRY_MINUTES", 30)
REDIS_URL = os.getenv("REDIS_URL", "")
CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:4200").split(",") if o.strip()
]

# --- Autenticação / bloqueio ---
MAX_LOGIN_ATTEMPTS = _int("MAX_LOGIN_ATTEMPTS", 5)
LOCKOUT_DURATION_MINUTES = _int("LOCKOUT_DURATION_MINUTES", 15)
PASSWORD_MIN_LENGTH = _int("PASSWORD_MIN_LENGTH", 12)

# --- Convites / bootstrap ---
INVITE_EXPIRY_HOURS = _int("INVITE_EXPIRY_HOURS", 72)
BOOTSTRAP_TOKEN = os.getenv("BOOTSTRAP_TOKEN", "")

# --- Rate limiting ---
RATE_LIMIT_ENABLED = _bool("RATE_LIMIT_ENABLED", "true")
RATE_LIMIT_AUTH = os.getenv("RATE_LIMIT_AUTH", "5/minute")
RATE_LIMIT_PASSWORD_REQUEST = os.getenv("RATE_LIMIT_PASSWORD_REQUEST", "3/minute")
RATE_LIMIT_FORM_TOKEN = os.getenv("RATE_LIMIT_FORM_TOKEN", "20/minute")
RATE_LIMIT_FORM_OTP = os.getenv("RATE_LIMIT_FORM_OTP", "5/minute")

# --- Headers de segurança ---
CSP_ENABLED = _bool("CSP_ENABLED", "true")
HSTS_ENABLED = _bool("HSTS_ENABLED", "false")  # opt-in — só ligar em produção HTTPS
HSTS_MAX_AGE = _int("HSTS_MAX_AGE", 31536000)

# --- Protecao de dados sensiveis em repouso ---
FIELD_ENCRYPTION_KEY = os.getenv("FIELD_ENCRYPTION_KEY", "")

# --- E-mail (SMTP) — entrega best-effort (fail-soft) ---
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = _int("SMTP_PORT", 587)
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "no-reply@example.com")

# --- Contexto de organização (multi-org / Super Admin) ---
ORG_CONTEXT_HEADER = "X-Org-Context"


class Role(str, Enum):
    """Papéis RBAC (FR-023). `super_admin` é o único cross-tenant."""

    super_admin = "super_admin"
    org_admin = "org_admin"
    consultant = "consultant"
    client = "client"
    manager = "manager"
    process_owner = "process_owner"
    control_owner = "control_owner"
    internal_auditor = "internal_auditor"
    guest_collaborator = "guest_collaborator"


class OrgStatus(str, Enum):
    active = "active"
    suspended = "suspended"


class UserStatus(str, Enum):
    pending = "pending"
    active = "active"
    disabled = "disabled"


class MembershipStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class InviteStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    expired = "expired"
    revoked = "revoked"


class AuditOutcome(str, Enum):
    success = "success"
    denied = "denied"


class DiagnosticStatus(str, Enum):
    draft = "draft"
    completed = "completed"


class DocStatus(str, Enum):
    draft = "draft"
    in_review = "in_review"
    in_force = "in_force"
    obsolete = "obsolete"


class DocType(str, Enum):
    context_analysis = "context_analysis"
    stakeholder_map = "stakeholder_map"
    scope_statement = "scope_statement"
    form_response = "form_response"
    gap_baseline = "gap_baseline"
    soa = "soa"


class IssueOrigin(str, Enum):
    internal = "internal"
    external = "external"


class IssueFramework(str, Enum):
    pestel = "pestel"
    swot = "swot"


class Level(str, Enum):
    alto = "alto"
    medio = "medio"
    baixo = "baixo"


ImpactLevel = Level


class EngagementStrategy(str, Enum):
    manage_closely = "manage_closely"
    keep_satisfied = "keep_satisfied"
    keep_informed = "keep_informed"
    monitor = "monitor"


class RequirementType(str, Enum):
    legal = "legal"
    regulatory = "regulatory"
    contractual = "contractual"
    expectation = "expectation"


class ScopeItemKind(str, Enum):
    inclusion = "inclusion"
    exclusion = "exclusion"


class Classification(str, Enum):
    publico = "publico"
    uso_interno = "uso_interno"
    confidencial = "confidencial"
    restrito = "restrito"


# --- Documentos imprimiveis/assinaveis (Feature 009) ---
DOCUMENT_STORAGE_DIR = os.getenv("DOCUMENT_STORAGE_DIR", "./document_store/")
DOCUMENT_PREVIEW_TTL_MINUTES = _int("DOCUMENT_PREVIEW_TTL_MINUTES", 60)
DOCUMENT_MAX_PDF_BYTES = _int("DOCUMENT_MAX_PDF_BYTES", 20 * 1024 * 1024)
DOCUMENT_RENDER_TIMEOUT_SECONDS = _int("DOCUMENT_RENDER_TIMEOUT_SECONDS", 30)


class PrintableDocumentType(str, Enum):
    context_report = "context_report"
    gap_report = "gap_report"
    soa_report = "soa_report"
    gap_baseline = "gap_baseline"
    form_response = "form_response"


class PrintTemplateScope(str, Enum):
    system = "system"
    tenant = "tenant"


class PrintTemplateStatus(str, Enum):
    draft = "draft"
    active = "active"
    inactive = "inactive"


class DocumentPreviewStatus(str, Enum):
    active = "active"
    expired = "expired"
    stale = "stale"
    signed = "signed"


class SignedDocumentStatus(str, Enum):
    signed = "signed"
    obsolete = "obsolete"


class SignatureCoordinateSystem(str, Enum):
    pdf_points_bottom_left = "pdf_points_bottom_left"


class SignaturePlacementOrigin(str, Enum):
    default = "default"
    user = "user"
    template = "template"


class SignatureMethod(str, Enum):
    internal_electronic_signature = "internal_electronic_signature"
    pades = "pades"
    icp_brasil = "icp_brasil"
    external_certificate_provider = "external_certificate_provider"


class DocumentAccessEventType(str, Enum):
    preview_created = "preview_created"
    preview_downloaded = "preview_downloaded"
    preview_inline_viewed = "preview_inline_viewed"
    placement_confirmed = "placement_confirmed"
    signed = "signed"
    signed_downloaded = "signed_downloaded"
    verified = "verified"
    template_created = "template_created"
    template_version_created = "template_version_created"
    template_activated = "template_activated"
    template_deactivated = "template_deactivated"
    access_denied = "access_denied"


# --- Storage de evidencias documentais (Feature 008) ---
EVIDENCE_STORAGE_DIR = os.getenv("EVIDENCE_STORAGE_DIR", "./evidence_store/")
EVIDENCE_MAX_FILE_BYTES = _int("EVIDENCE_MAX_FILE_BYTES", 20 * 1024 * 1024)
EVIDENCE_ALLOWED_EXTENSIONS = {
    ext.strip().lower()
    for ext in os.getenv(
        "EVIDENCE_ALLOWED_EXTENSIONS",
        ".pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.7z",
    ).split(",")
    if ext.strip()
}
EVIDENCE_ALLOWED_MIME_TYPES = {
    mime.strip().lower()
    for mime in os.getenv("EVIDENCE_ALLOWED_MIME_TYPES", "").split(",")
    if mime.strip()
}


class GapEvidenceStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class GapEvidenceEventType(str, Enum):
    uploaded = "uploaded"
    content_viewed = "content_viewed"
    downloaded = "downloaded"
    replaced = "replaced"
    inactivated = "inactivated"
    access_denied = "access_denied"


# --- Motor de Workflow de Preenchimento (Feature 003) ---
FORM_TOKEN_EXPIRY_DAYS = _int("FORM_TOKEN_EXPIRY_DAYS", 7)
OTP_EXPIRY_MINUTES = _int("OTP_EXPIRY_MINUTES", 15)
OTP_MAX_ATTEMPTS = _int("OTP_MAX_ATTEMPTS", 3)


class FormKind(str, Enum):
    diagnostic = "diagnostic"
    gap_analysis = "gap_analysis"
    generic = "generic"


class FormFieldType(str, Enum):
    text = "text"
    textarea = "textarea"
    boolean = "boolean"
    number = "number"
    select = "select"


class AssignmentStatus(str, Enum):
    draft = "draft"
    pending = "pending"
    in_progress = "in_progress"
    submitted = "submitted"
    returned = "returned"
    signed = "signed"
    completed = "completed"
    cancelled = "cancelled"


class AssignmentEventType(str, Enum):
    assigned = "assigned"
    notified = "notified"
    claimed = "claimed"
    saved = "saved"
    submitted = "submitted"
    returned = "returned"
    signed = "signed"
    countersigned = "countersigned"
    completed = "completed"
    cancelled = "cancelled"
    reminded = "reminded"
    otp_requested = "otp_requested"


class SignerRole(str, Enum):
    filler = "filler"
    assigner = "assigner"


class TemplateStatus(str, Enum):
    draft = "draft"
    active = "active"
    archived = "archived"


# --- Gap Analysis (Feature 004) ---

class GapStatus(str, Enum):
    not_filled = "not_filled"
    meets = "meets"
    partial = "partial"
    not_meet = "not_meet"
    not_applicable = "not_applicable"


class GapPriority(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class GapDimension(str, Enum):
    clause = "clause"
    annex_a = "annex_a"


class GapTheme(str, Enum):
    organizational = "organizational"
    people = "people"
    physical = "physical"
    technological = "technological"


class GapAssignmentScope(str, Enum):
    whole = "whole"
    theme = "theme"


# --- Statement of Applicability / SoA (Feature 005) ---

class SoaImplementationStatus(str, Enum):
    implemented = "implemented"
    in_progress = "in_progress"
    planned = "planned"
    not_started = "not_started"
    not_applicable = "not_applicable"


class SoaInclusionReason(str, Enum):
    risk_treatment = "risk_treatment"      # resultado do tratamento de riscos
    legal = "legal"                        # requisito legal/regulatório
    contractual = "contractual"            # requisito contratual
    best_practice = "best_practice"        # melhor prática / requisito de negócio


# Mapeamento de status Gap Analysis → status de implementação da SoA (consolidação).
# `not_filled` ⇒ None (não inventa valor; usuário define).
GAP_TO_SOA_STATUS: dict[GapStatus, "SoaImplementationStatus | None"] = {
    GapStatus.meets: SoaImplementationStatus.implemented,
    GapStatus.partial: SoaImplementationStatus.in_progress,
    GapStatus.not_meet: SoaImplementationStatus.not_started,
    GapStatus.not_applicable: SoaImplementationStatus.not_applicable,
    GapStatus.not_filled: None,
}
