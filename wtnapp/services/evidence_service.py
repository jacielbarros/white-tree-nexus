"""Lógica do repositório transversal de evidências (Feature 014).

Resolução de alvo polimórfico, cadeia de custódia e regras de acesso por classificação.
O conteúdo de arquivo e o `storage_key` nunca saem deste serviço para a API/audit.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp.helpers.permissions import has_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.asset_item_model import AssetItem
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink, EvidenceVersion
from wtnapp.models.gap_assessment_model import GapAssessmentItem
from wtnapp.models.risk_model import Risk
from wtnapp.models.soa_model import SoaItem
from wtnapp.settings import (
    AuditOutcome,
    Classification,
    EvidenceEventType,
    EvidenceStatus,
    SgsiArtifactType,
)

# Mapa alvo → modelo tenant-scoped. `audit_finding` é registrado quando o domínio de
# auditoria interna existir (US5); até lá é resolvido por `_AUDIT_FINDING_RESOLVER`.
_TARGET_MODELS: dict[SgsiArtifactType, type] = {
    SgsiArtifactType.soa_item: SoaItem,
    SgsiArtifactType.gap_item: GapAssessmentItem,
    SgsiArtifactType.risk: Risk,
    SgsiArtifactType.asset: AssetItem,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def target_exists(db: Session, ctx: OrgContext, target_type: SgsiArtifactType, target_id: uuid.UUID) -> bool:
    """True se o alvo existe no tenant do contexto."""
    model = _TARGET_MODELS.get(target_type)
    if model is None:
        if target_type is SgsiArtifactType.audit_finding:
            try:
                from wtnapp.models.internal_audit_model import InternalAuditFinding  # noqa: PLC0415
            except ModuleNotFoundError:
                # Domínio de auditoria interna ainda não implementado (US5).
                return False
            model = InternalAuditFinding
        else:
            return False
    return scoped_query(db, model, ctx).filter(model.id == target_id).first() is not None


def can_download(ctx: OrgContext, classification: Classification) -> bool:
    if classification in {Classification.publico, Classification.uso_interno}:
        return has_permission(ctx.role, "view_evidence")
    return has_permission(ctx.role, "manage_evidence")


def current_version(db: Session, evidence: Evidence) -> EvidenceVersion | None:
    if evidence.current_version_id is None:
        return None
    version = db.get(EvidenceVersion, evidence.current_version_id)
    if version is None or version.tenant_id != evidence.tenant_id or version.evidence_id != evidence.id:
        return None
    return version


def active_links(db: Session, ctx: OrgContext, evidence_id: uuid.UUID) -> list[EvidenceLink]:
    return (
        scoped_query(db, EvidenceLink, ctx)
        .filter(EvidenceLink.evidence_id == evidence_id, EvidenceLink.active.is_(True))
        .order_by(EvidenceLink.created_at.asc())
        .all()
    )


def next_version_number(db: Session, ctx: OrgContext, evidence_id: uuid.UUID) -> int:
    return (
        db.query(func.max(EvidenceVersion.version_number))
        .filter(EvidenceVersion.tenant_id == ctx.tenant_id, EvidenceVersion.evidence_id == evidence_id)
        .scalar()
        or 0
    ) + 1


def log_event(
    db: Session,
    *,
    ctx: OrgContext,
    event_type: EvidenceEventType,
    outcome: AuditOutcome = AuditOutcome.success,
    evidence_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    link_id: uuid.UUID | None = None,
    target_type: SgsiArtifactType | None = None,
    target_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        EvidenceEvent(
            tenant_id=ctx.tenant_id,
            evidence_id=evidence_id,
            version_id=version_id,
            link_id=link_id,
            target_type=target_type,
            target_id=target_id,
            event_type=event_type.value,
            outcome=outcome.value,
            actor_id=ctx.principal.user.id,
            details=details or {},
        )
    )


def get_evidence(
    db: Session,
    ctx: OrgContext,
    evidence_id: uuid.UUID,
    *,
    include_inactive: bool = False,
) -> Evidence | None:
    query = scoped_query(db, Evidence, ctx).filter(Evidence.id == evidence_id)
    if not include_inactive:
        query = query.filter(Evidence.status == EvidenceStatus.active)
    return query.first()


def safe_title(title: str | None, filename: str) -> str:
    value = (title or filename).strip()
    return value[:255] or filename[:255]


def safe_text(value: str | None, limit: int = 1000) -> str | None:
    cleaned = (value or "").strip()
    return cleaned[:limit] or None
