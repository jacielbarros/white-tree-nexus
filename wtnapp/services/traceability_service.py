"""Timeline de rastreabilidade (read-only) por artefato — Feature 014, US7.

Agrega, para um alvo (controle/risco/ativo), os eventos e artefatos associados: evidências
vinculadas, eventos de custódia e constatações que o referenciam. Apenas metadados — nunca
conteúdo de arquivo ou `storage_key`.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink
from wtnapp.models.internal_audit_model import InternalAuditFinding
from wtnapp.settings import AuditFindingStatus, EvidenceStatus, SgsiArtifactType


@dataclass
class TimelineEntry:
    occurred_at: datetime
    kind: str  # evidence | finding | event
    ref_id: uuid.UUID
    label: str
    detail: str


def build_timeline(
    db: Session,
    ctx: OrgContext,
    target_type: SgsiArtifactType,
    target_id: uuid.UUID,
    *,
    include_findings: bool,
) -> list[TimelineEntry]:
    entries: list[TimelineEntry] = []

    # Evidências vinculadas (ativas) ao alvo.
    links = (
        scoped_query(db, EvidenceLink, ctx)
        .filter(
            EvidenceLink.target_type == target_type,
            EvidenceLink.target_id == target_id,
            EvidenceLink.active.is_(True),
        )
        .all()
    )
    evidence_ids = {l.evidence_id for l in links}
    by_link = {l.evidence_id: l for l in links}
    if evidence_ids:
        for ev in scoped_query(db, Evidence, ctx).filter(Evidence.id.in_(evidence_ids)).all():
            link = by_link.get(ev.id)
            entries.append(TimelineEntry(
                occurred_at=link.created_at if link else ev.created_at,
                kind="evidence", ref_id=ev.id,
                label=ev.title,
                detail=f"Evidência ({ev.classification.value}, {ev.status.value})",
            ))

    # Eventos de custódia que referenciam o alvo.
    events = (
        scoped_query(db, EvidenceEvent, ctx)
        .filter(EvidenceEvent.target_type == target_type, EvidenceEvent.target_id == target_id)
        .all()
    )
    for e in events:
        entries.append(TimelineEntry(
            occurred_at=e.occurred_at, kind="event", ref_id=e.id,
            label=e.event_type, detail=f"Evento de evidência ({e.outcome})",
        ))

    # Constatações que referenciam o alvo (apenas com permissão de auditoria interna).
    if include_findings:
        findings = (
            scoped_query(db, InternalAuditFinding, ctx)
            .filter(
                InternalAuditFinding.target_type == target_type,
                InternalAuditFinding.target_id == target_id,
                InternalAuditFinding.status == AuditFindingStatus.active,
            )
            .all()
        )
        for f in findings:
            entries.append(TimelineEntry(
                occurred_at=f.created_at, kind="finding", ref_id=f.id,
                label=f.title, detail=f"Constatação ({f.finding_type.value})",
            ))

    entries.sort(key=lambda x: x.occurred_at, reverse=True)
    return entries
