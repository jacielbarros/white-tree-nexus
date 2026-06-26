"""Agregações do módulo de Ativos / Processos / Escopo (cards de resumo + dashboard).

Todas as métricas são tenant-scoped e calculadas sobre o inventário **não arquivado**
(record_status != archived) — itens arquivados saem da visão de gestão ativa.
"""

from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.asset_item_model import AssetItem
from wtnapp.schemas.asset_schema import AssetDashboardResponse, AssetSummaryResponse
from wtnapp.services.asset_service import derive_review_status
from wtnapp.settings import (
    AssetRecordStatus,
    AssetReviewStatus,
    AssetScopeStatus,
    AssetType,
    CiaLevel,
)


def _active_items(db: Session, ctx: OrgContext) -> list[AssetItem]:
    return (
        scoped_query(db, AssetItem, ctx)
        .filter(AssetItem.record_status != AssetRecordStatus.archived)
        .all()
    )


def _cia_complete(it: AssetItem) -> bool:
    return it.confidentiality is not None and it.integrity is not None and it.availability is not None


def summary(db: Session, ctx: OrgContext) -> AssetSummaryResponse:
    items = _active_items(db, ctx)
    return AssetSummaryResponse(
        total=len(items),
        assets=sum(1 for it in items if it.item_type == AssetType.information_asset),
        processes=sum(1 for it in items if it.item_type == AssetType.business_process),
        suppliers=sum(1 for it in items if it.item_type == AssetType.supplier),
        in_scope=sum(1 for it in items if it.scope_status == AssetScopeStatus.in_scope),
        critical=sum(1 for it in items if it.criticality == CiaLevel.critica),
        without_responsible=sum(1 for it in items if it.responsible_user_id is None),
        cia_incomplete=sum(1 for it in items if not _cia_complete(it)),
    )


def dashboard(db: Session, ctx: OrgContext) -> AssetDashboardResponse:
    items = _active_items(db, ctx)

    by_type: dict[str, int] = {t.value: 0 for t in AssetType}
    by_criticality: dict[str, int] = {c.value: 0 for c in CiaLevel}
    by_criticality["unset"] = 0
    by_scope: dict[str, int] = {s.value: 0 for s in AssetScopeStatus}
    by_review_status: dict[str, int] = {r.value: 0 for r in AssetReviewStatus}
    with_personal_data = 0
    critical_without_review = 0
    without_responsible = 0

    for it in items:
        by_type[it.item_type.value] += 1
        by_criticality[it.criticality.value if it.criticality else "unset"] += 1
        by_scope[it.scope_status.value] += 1
        review = derive_review_status(it.next_review_at)
        by_review_status[review.value] += 1
        if it.has_personal_data:
            with_personal_data += 1
        if it.criticality == CiaLevel.critica and review in (AssetReviewStatus.overdue, AssetReviewStatus.undefined):
            critical_without_review += 1
        if it.responsible_user_id is None:
            without_responsible += 1

    return AssetDashboardResponse(
        by_type=by_type,
        by_criticality=by_criticality,
        by_scope=by_scope,
        by_review_status=by_review_status,
        with_personal_data=with_personal_data,
        critical_without_review=critical_without_review,
        without_responsible=without_responsible,
    )
