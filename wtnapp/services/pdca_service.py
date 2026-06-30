"""Visão de ciclo PDCA (read-only) — Feature 015, 10.1.

Agrega, por artefato (ou org), o loop fechado: constatações (5a) → NCs → ações/verificação →
melhorias. **Somente metadados**; **sem write-back** nos módulos consumidos. RBAC composto é aplicado
no router (constatações só com `view_internal_audit`, atas só com `view_management_review`).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.improvement_model import Improvement
from wtnapp.models.internal_audit_model import InternalAuditFinding
from wtnapp.models.management_review_model import ManagementReview
from wtnapp.models.nonconformity_model import CorrectiveAction, NonConformity
from wtnapp.settings import AuditFindingStatus, SgsiArtifactType


@dataclass
class PdcaEntry:
    occurred_at: datetime
    phase: str  # check | act | plan
    kind: str
    ref_id: uuid.UUID
    label: str
    detail: str


def build_cycle(
    db: Session,
    ctx: OrgContext,
    target_type: SgsiArtifactType | None,
    target_id: uuid.UUID | None,
    *,
    include_findings: bool,
    include_reviews: bool,
) -> list[PdcaEntry]:
    entries: list[PdcaEntry] = []
    has_target = target_type is not None and target_id is not None

    # CHECK — constatações de auditoria (5a) que referenciam o alvo.
    if include_findings:
        fq = scoped_query(db, InternalAuditFinding, ctx).filter(InternalAuditFinding.status == AuditFindingStatus.active)
        if has_target:
            fq = fq.filter(InternalAuditFinding.target_type == target_type, InternalAuditFinding.target_id == target_id)
        for f in fq.all():
            entries.append(PdcaEntry(f.created_at, "check", "finding", f.id, f.title, f"Constatação ({f.finding_type.value})"))

    # CHECK — atas de análise crítica (org-level).
    if include_reviews:
        for r in scoped_query(db, ManagementReview, ctx).all():
            entries.append(PdcaEntry(datetime.combine(r.review_date, datetime.min.time()), "check", "management_review", r.id, r.title, "Análise crítica pela direção"))

    # ACT — NCs e ações corretivas.
    ncq = scoped_query(db, NonConformity, ctx)
    if has_target:
        ncq = ncq.filter(NonConformity.target_type == target_type, NonConformity.target_id == target_id)
    nc_ids = []
    for nc in ncq.all():
        nc_ids.append(nc.id)
        entries.append(PdcaEntry(nc.created_at, "act", "nonconformity", nc.id, nc.code, f"NC {nc.severity.value} ({nc.status.value})"))
    if nc_ids:
        for a in scoped_query(db, CorrectiveAction, ctx).filter(CorrectiveAction.nonconformity_id.in_(nc_ids)).all():
            entries.append(PdcaEntry(a.created_at, "act", "corrective_action", a.id, a.description[:60], f"Ação corretiva ({a.status.value})"))

    # ACT — melhorias que realimentam o alvo.
    iq = scoped_query(db, Improvement, ctx)
    if has_target:
        iq = iq.filter(Improvement.target_type == target_type, Improvement.target_id == target_id)
    for imp in iq.all():
        entries.append(PdcaEntry(imp.created_at, "act", "improvement", imp.id, imp.code, f"Melhoria ({imp.origin.value}, {imp.status.value})"))

    entries.sort(key=lambda e: e.occurred_at)
    return entries
