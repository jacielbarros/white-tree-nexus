"""Métricas do módulo de riscos — heat map 5x5 e dashboard (Feature 012)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from wtnapp.models.risk_model import Risk, RiskAssetLink
from wtnapp.services import risk_methodology_service as methodology_service
from wtnapp.settings import RiskStatus, RiskTreatmentOption


def _active_risks(db: Session, tenant_id: uuid.UUID) -> list[Risk]:
    return (
        db.query(Risk)
        .filter(Risk.tenant_id == tenant_id, Risk.is_archived == False)  # noqa: E712
        .all()
    )


def heatmap(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    """Distribuição dos riscos avaliados por célula probabilidade × impacto (5x5)."""
    methodology = methodology_service.get_or_default(db, tenant_id)
    matrix = methodology.get("risk_matrix", {})
    counts: dict[tuple[int, int], int] = {}
    for risk in _active_risks(db, tenant_id):
        if risk.probability_level and risk.impact_level:
            key = (risk.probability_level, risk.impact_level)
            counts[key] = counts.get(key, 0) + 1
    cells = []
    for prob in range(1, 6):
        for impact in range(1, 6):
            cells.append({
                "probability": prob,
                "impact": impact,
                "level_key": matrix.get(f"{prob}x{impact}"),
                "count": counts.get((prob, impact), 0),
            })
    return cells


def dashboard(db: Session, tenant_id: uuid.UUID) -> dict:
    """Dashboard completo do módulo: heat map + distribuições + inerente×residual."""
    risks = _active_risks(db, tenant_id)

    by_level: dict[str, int] = {}
    by_owner: dict[str, int] = {}
    without_treatment = accepted = residual_pending = inherent_above = residual_above = 0
    for r in risks:
        if r.inherent_level_key:
            by_level[r.inherent_level_key] = by_level.get(r.inherent_level_key, 0) + 1
        if r.owner_user_id:
            key = str(r.owner_user_id)
            by_owner[key] = by_owner.get(key, 0) + 1
        if r.treatment_option is None and r.status in (RiskStatus.identified, RiskStatus.assessed):
            without_treatment += 1
        if r.treatment_option == RiskTreatmentOption.accept or r.status == RiskStatus.accepted:
            accepted += 1
        if r.above_acceptance:
            inherent_above += 1
        if r.residual_above_acceptance:
            residual_above += 1
        if r.treatment_option is not None and r.residual_above_acceptance:
            residual_pending += 1

    by_asset: dict[str, int] = {}
    for link in db.query(RiskAssetLink).filter_by(tenant_id=tenant_id).all():
        key = str(link.asset_item_id)
        by_asset[key] = by_asset.get(key, 0) + 1

    top = sorted(
        [r for r in risks if r.above_acceptance],
        key=lambda r: ((r.probability_level or 0) * (r.impact_level or 0)),
        reverse=True,
    )[:10]

    return {
        "heatmap": heatmap(db, tenant_id),
        "by_level": by_level,
        "top_risks": [str(r.id) for r in top],
        "without_treatment": without_treatment,
        "accepted": accepted,
        "residual_pending": residual_pending,
        "by_owner": by_owner,
        "by_asset": by_asset,
        "inherent_vs_residual": {"inherent_above": inherent_above, "residual_above": residual_above},
    }
