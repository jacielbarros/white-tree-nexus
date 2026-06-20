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

# --- Headers de segurança ---
CSP_ENABLED = _bool("CSP_ENABLED", "true")
HSTS_ENABLED = _bool("HSTS_ENABLED", "false")  # opt-in — só ligar em produção HTTPS
HSTS_MAX_AGE = _int("HSTS_MAX_AGE", 31536000)

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
