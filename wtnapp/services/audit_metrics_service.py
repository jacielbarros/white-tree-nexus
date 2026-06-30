"""Indicadores simples do módulo de Evidências + Auditoria Interna (Feature 014, US8).

Contagens/agrupamentos tenant-scoped — sem motor de KPIs (9.1 fora de escopo).
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.evidence_model import Evidence
from wtnapp.models.internal_audit_model import InternalAudit, InternalAuditFinding
from wtnapp.settings import AuditFindingStatus, EvidenceStatus


def _counts(query, column) -> dict[str, int]:
    return {str(getattr(value, "value", value)): count for value, count in query.group_by(column).with_entities(column, func.count()).all()}


def build_metrics(db: Session, ctx: OrgContext) -> dict:
    evidence_by_status = _counts(scoped_query(db, Evidence, ctx), Evidence.status)
    evidence_by_classification = _counts(
        scoped_query(db, Evidence, ctx).filter(Evidence.status == EvidenceStatus.active), Evidence.classification
    )
    audits_by_status = _counts(scoped_query(db, InternalAudit, ctx), InternalAudit.status)
    findings_by_type = _counts(
        scoped_query(db, InternalAuditFinding, ctx).filter(InternalAuditFinding.status == AuditFindingStatus.active),
        InternalAuditFinding.finding_type,
    )
    return {
        "evidence_by_status": evidence_by_status,
        "evidence_by_classification": evidence_by_classification,
        "audits_by_status": audits_by_status,
        "findings_by_type": findings_by_type,
    }
