"""Dashboard Service — agrega o estado de conformidade dos módulos existentes (Feature 006).

Camada de **leitura**: compõe Contexto (Cláusula 4), Gap Analysis e SoA num payload de home, sem
novo modelo de domínio. Toda query é escopada por `ctx.tenant_id`. Resiliência: a montagem de cada
card é isolada (fail-open por card) — falha em um módulo não derruba os demais. O isolamento de
tenant permanece fail-closed (resolvido por `get_org_context`, antes deste service).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from wtnapp.helpers.permissions import has_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.context_analysis_model import ContextAnalysis
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.organization_model import Organization
from wtnapp.models.scope_model import ScopeStatement
from wtnapp.models.soa_model import Soa, SoaItem
from wtnapp.models.stakeholder_model import StakeholderMap
from wtnapp.schemas.dashboard_schema import (
    AdherencePoint,
    DashboardCardStatus,
    DashboardKpis,
    DashboardModuleId,
    DashboardResponse,
    ModuleCard,
    NextAction,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.gap_metrics_service import compute_dashboard, list_gaps
from wtnapp.settings import DocStatus, DocType, GapPriority

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_date(value) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _card_status(draft_status: DocStatus, current_version_id, overdue: bool) -> DashboardCardStatus:
    """Mapeia o estado de um Documento Controlado → vocabulário de card (research D4)."""
    if current_version_id is not None:
        return DashboardCardStatus.needs_review if overdue else DashboardCardStatus.in_force
    if draft_status == DocStatus.in_review:
        return DashboardCardStatus.in_review
    return DashboardCardStatus.draft


def _earliest_deadline(rows) -> tuple[str | None, date | None]:
    """Responsável + menor `deadline` futuro entre itens; cai no menor prazo se nenhum futuro (C3)."""
    today = _now().date()
    dated = [r for r in rows if r.deadline is not None]
    if not dated:
        return None, None
    future = [r for r in dated if _as_date(r.deadline) >= today]
    chosen = min(future or dated, key=lambda r: _as_date(r.deadline))
    return chosen.responsible, _as_date(chosen.deadline)


def _current_version(db: Session, version_id) -> DocumentVersion | None:
    return db.get(DocumentVersion, version_id) if version_id else None


# ── Card builders (cada um isolado por fail-open no orquestrador) ─────────────


def _context_card(db: Session, ctx: OrgContext) -> ModuleCard:
    analysis = db.query(ContextAnalysis).filter_by(tenant_id=ctx.tenant_id).first()
    smap = db.query(StakeholderMap).filter_by(tenant_id=ctx.tenant_id).first()
    scope = db.query(ScopeStatement).filter_by(tenant_id=ctx.tenant_id).first()

    artifacts = [a for a in (analysis, smap, scope) if a is not None]
    if not artifacts:
        return ModuleCard(
            id=DashboardModuleId.context,
            title="Contexto · Cláusula 4",
            status=DashboardCardStatus.not_started,
            not_started=True,
            next_action=NextAction(label="Iniciar análise de contexto", route="context-analysis"),
        )

    approved = sum(1 for a in artifacts if a.current_version_id is not None)
    progress = round(approved / 3 * 100, 1)

    # Status do conjunto: o escopo (4.3) é o documento âncora; usa-o quando existir.
    anchor = scope or analysis or smap
    current = _current_version(db, anchor.current_version_id)
    overdue = cds.review_overdue(current)
    status = _card_status(anchor.draft_status, anchor.current_version_id, overdue)

    if anchor.current_version_id is not None:
        action = NextAction(label="Ver visão consolidada", route="context-overview")
    elif anchor.draft_status == DocStatus.in_review:
        action = NextAction(label="Aprovar documentos", route="context-overview")
    else:
        action = NextAction(label="Completar análise de contexto", route="context-analysis")

    return ModuleCard(
        id=DashboardModuleId.context,
        title="Contexto · Cláusula 4",
        status=status,
        progress_pct=progress,
        overdue=overdue,
        next_action=action,
    )


def _gap_card(db: Session, ctx: OrgContext, kpis: DashboardKpis) -> ModuleCard:
    assessment = db.query(GapAssessment).filter_by(tenant_id=ctx.tenant_id).first()
    if assessment is None:
        return ModuleCard(
            id=DashboardModuleId.gap,
            title="Gap Analysis · Anexo A",
            status=DashboardCardStatus.not_started,
            not_started=True,
            next_action=NextAction(label="Adotar catálogo", route="gap-catalog"),
        )

    metrics = compute_dashboard(db, ctx.tenant_id, assessment.id)

    # Conformidade consolidada da JORNADA COMPLETA (cláusulas 4–10 + Anexo A) — fonte única
    # compartilhada com o dashboard do Gap (decisão 1a + 2i). Antes o KPI da home era escopado
    # só ao Anexo A (0/93), divergindo da tela do Gap; agora as duas telas batem.
    dims = metrics.get("dimensions", {})
    kpis.overall_adherence = metrics["consolidated_conformance"]
    kpis.controls_evaluated = metrics["evaluated_items"]
    kpis.controls_total = metrics["total_items"]
    kpis.conformance_clause = (dims.get("clause") or {}).get("conformance")
    kpis.conformance_annex = (dims.get("annex_a") or {}).get("conformance")
    gaps = list_gaps(db, ctx.tenant_id, assessment.id)
    kpis.critical_gaps = sum(1 for g in gaps if g.priority == GapPriority.critical)

    progress = round(metrics["completeness"] * 100, 1)
    current = _current_version(db, assessment.current_version_id)
    overdue = cds.review_overdue(current)
    status = _card_status(assessment.draft_status, assessment.current_version_id, overdue)

    items = (
        db.query(GapAssessmentItem)
        .filter_by(tenant_id=ctx.tenant_id, assessment_id=assessment.id)
        .all()
    )
    responsible, deadline = _earliest_deadline(items)

    if assessment.current_version_id is not None:
        action = NextAction(label="Ver baselines", route="gap-baselines")
    elif metrics["completeness"] >= 1:
        action = NextAction(label="Ver dashboard de aderência", route="gap-dashboard")
    else:
        action = NextAction(label="Avaliar controles", route="gap-analysis")

    return ModuleCard(
        id=DashboardModuleId.gap,
        title="Gap Analysis · Anexo A",
        status=status,
        progress_pct=progress,
        responsible=responsible,
        deadline=deadline,
        overdue=overdue,
        next_action=action,
    )


def _soa_card(db: Session, ctx: OrgContext) -> ModuleCard:
    soa = db.query(Soa).filter_by(tenant_id=ctx.tenant_id).first()
    if soa is None:
        return ModuleCard(
            id=DashboardModuleId.soa,
            title="Declaração de Aplicabilidade",
            status=DashboardCardStatus.not_started,
            not_started=True,
            next_action=NextAction(label="Consolidar do Gap", route="soa"),
        )

    items = db.query(SoaItem).filter_by(tenant_id=ctx.tenant_id, soa_id=soa.id).all()
    filled = sum(1 for i in items if i.implementation_status is not None)
    progress = round(filled / len(items) * 100, 1) if items else None

    current = _current_version(db, soa.current_version_id)
    overdue = cds.review_overdue(current)
    status = _card_status(soa.draft_status, soa.current_version_id, overdue)
    responsible, deadline = _earliest_deadline(items)

    if soa.current_version_id is not None:
        action = NextAction(label="Ver versões da SoA", route="soa-versions")
    elif soa.draft_status == DocStatus.in_review:
        action = NextAction(label="Aprovar SoA", route="soa-versions")
    else:
        action = NextAction(label="Completar declaração", route="soa")

    return ModuleCard(
        id=DashboardModuleId.soa,
        title="Declaração de Aplicabilidade",
        status=status,
        progress_pct=progress,
        responsible=responsible,
        deadline=deadline,
        overdue=overdue,
        next_action=action,
    )


def _risk_card(db: Session, ctx: OrgContext) -> ModuleCard:
    """Readiness do Módulo de Riscos (Feature 012) na esteira."""
    from wtnapp.models.risk_model import Risk, RiskPlan
    from wtnapp.settings import RiskStatus

    risks = db.query(Risk).filter_by(tenant_id=ctx.tenant_id, is_archived=False).all()
    plan = db.query(RiskPlan).filter_by(tenant_id=ctx.tenant_id).first()

    if not risks:
        return ModuleCard(
            id=DashboardModuleId.risk,
            title="Gestão de Riscos",
            status=DashboardCardStatus.not_started,
            not_started=True,
            next_action=NextAction(label="Identificar riscos", route="risks"),
        )

    evaluated = sum(1 for r in risks if r.status != RiskStatus.identified)
    progress = round(evaluated / len(risks) * 100, 1)

    current = _current_version(db, plan.current_version_id) if plan else None
    overdue = cds.review_overdue(current)
    draft_status = plan.draft_status if plan else DocStatus.draft
    current_version_id = plan.current_version_id if plan else None
    status = _card_status(draft_status, current_version_id, overdue)

    if current_version_id is not None:
        action = NextAction(label="Ver Plano de Tratamento", route="risk-treatment-plan")
    elif evaluated < len(risks):
        action = NextAction(label="Avaliar riscos", route="risks")
    else:
        action = NextAction(label="Tratar e aprovar o plano", route="risk-treatment-plan")

    return ModuleCard(
        id=DashboardModuleId.risk,
        title="Gestão de Riscos",
        status=status,
        progress_pct=progress,
        overdue=overdue,
        next_action=action,
    )


def _internal_audit_card(db: Session, ctx: OrgContext) -> ModuleCard:
    """Readiness de Evidências & Auditoria Interna (Feature 014) na esteira."""
    from wtnapp.models.internal_audit_model import InternalAudit
    from wtnapp.settings import InternalAuditStatus

    audits = db.query(InternalAudit).filter_by(tenant_id=ctx.tenant_id).all()
    if not audits:
        return ModuleCard(
            id=DashboardModuleId.internal_audit,
            title="Evidências & Auditoria Interna",
            status=DashboardCardStatus.not_started,
            not_started=True,
            next_action=NextAction(label="Planejar auditoria", route="internal-audit"),
        )

    # Âncora: auditoria com relatório aprovado, senão a mais recente.
    approved = [a for a in audits if a.current_version_id is not None]
    anchor = approved[0] if approved else max(audits, key=lambda a: a.created_at)
    completed = sum(1 for a in audits if a.status == InternalAuditStatus.completed)
    progress = round(completed / len(audits) * 100, 1)

    current = _current_version(db, anchor.current_version_id)
    overdue = cds.review_overdue(current)
    status = _card_status(anchor.draft_status, anchor.current_version_id, overdue)

    if anchor.current_version_id is not None:
        action = NextAction(label="Ver relatório de auditoria", route="internal-audit-detail")
    elif anchor.status == InternalAuditStatus.completed:
        action = NextAction(label="Aprovar relatório", route="internal-audit-detail")
    else:
        action = NextAction(label="Conduzir auditoria", route="internal-audit-detail")

    return ModuleCard(
        id=DashboardModuleId.internal_audit,
        title="Evidências & Auditoria Interna",
        status=status,
        progress_pct=progress,
        overdue=overdue,
        next_action=action,
    )


def _placeholder_cards() -> list[ModuleCard]:
    return [
        ModuleCard(
            id=DashboardModuleId.action_plan,
            title="NC & Ações Corretivas",
            status=DashboardCardStatus.not_started,
            not_started=True,
            placeholder=True,
            next_action=NextAction(label="Em breve · Módulo 5b", route="dashboard"),
        ),
    ]


def _error_card(module_id: DashboardModuleId, title: str) -> ModuleCard:
    return ModuleCard(
        id=module_id,
        title=title,
        status=DashboardCardStatus.error,
        next_action=NextAction(label="Tentar novamente", route="dashboard"),
    )


def _adherence_trend(db: Session, ctx: OrgContext) -> list[AdherencePoint] | None:
    """P2 (D9) — série de aderência a partir das baselines aprovadas do Gap. Null se < 2."""
    baselines = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.tenant_id == ctx.tenant_id,
            DocumentVersion.document_type == DocType.gap_baseline,
        )
        .order_by(DocumentVersion.version_number.asc())
        .all()
    )
    points: list[AdherencePoint] = []
    for bl in baselines:
        snap = bl.content_snapshot or {}
        adherence = (snap.get("dashboard") or {}).get("overall_adherence")
        if adherence is None:
            continue
        points.append(
            AdherencePoint(date=_as_date(bl.emitted_at), adherence=adherence, version=bl.version_number)
        )
    return points if len(points) >= 2 else None


# ── Orquestrador ─────────────────────────────────────────────────────────────


def build_dashboard(db: Session, ctx: OrgContext) -> DashboardResponse:
    org = db.get(Organization, ctx.tenant_id)
    kpis = DashboardKpis()
    cards: list[ModuleCard] = []

    # Gating por permissão de módulo (não eleva permissões) + fail-open por card.
    builders: list[tuple[str, DashboardModuleId, str, object]] = [
        ("view_context", DashboardModuleId.context, "Contexto · Cláusula 4", lambda: _context_card(db, ctx)),
        ("view_gap", DashboardModuleId.gap, "Gap Analysis · Anexo A", lambda: _gap_card(db, ctx, kpis)),
        ("view_soa", DashboardModuleId.soa, "Declaração de Aplicabilidade", lambda: _soa_card(db, ctx)),
        ("view_risk", DashboardModuleId.risk, "Gestão de Riscos", lambda: _risk_card(db, ctx)),
        ("view_internal_audit", DashboardModuleId.internal_audit, "Evidências & Auditoria Interna", lambda: _internal_audit_card(db, ctx)),
    ]
    for perm, module_id, title, build in builders:
        if not has_permission(ctx.role, perm):
            continue
        try:
            cards.append(build())
        except Exception:  # noqa: BLE001 — fail-open por card (D8); isolamento permanece fail-closed
            logger.exception("Falha ao montar card do dashboard: %s (tenant=%s)", module_id.value, ctx.tenant_id)
            cards.append(_error_card(module_id, title))

    cards.extend(_placeholder_cards())

    real_cards = [c for c in cards if not c.placeholder]
    kpis.modules_total = len(real_cards)
    kpis.modules_approved = sum(1 for c in real_cards if c.status == DashboardCardStatus.in_force)

    trend = None
    if has_permission(ctx.role, "view_gap"):
        try:
            trend = _adherence_trend(db, ctx)
        except Exception:  # noqa: BLE001
            logger.exception("Falha ao montar série de aderência (tenant=%s)", ctx.tenant_id)

    return DashboardResponse(
        organization_id=ctx.tenant_id,
        organization_name=org.name if org else "",
        kpis=kpis,
        cards=cards,
        adherence_trend=trend,
        generated_at=_now(),
    )
