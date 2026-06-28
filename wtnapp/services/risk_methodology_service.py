"""Metodologia de risco — get-or-default 5x5, cálculo de nível, critério de aceitação,
derivação de impacto a partir da CIA e recálculo em massa (Feature 012)."""

from __future__ import annotations

import copy
import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.models.risk_methodology_model import RiskMethodology
from wtnapp.models.risk_model import Risk
from wtnapp.settings import DEFAULT_RISK_METHODOLOGY, CIA_ORDER


def default_methodology() -> dict:
    """Cópia profunda da metodologia 5x5 padrão (usada quando a org não configurou)."""
    return copy.deepcopy(DEFAULT_RISK_METHODOLOGY)


def get_or_default(db: Session, tenant_id: uuid.UUID) -> dict:
    """Configuração da org como dict, ou o default 5x5 in-code (gate suave, FR-006)."""
    row = db.query(RiskMethodology).filter_by(tenant_id=tenant_id).first()
    if row is None:
        data = default_methodology()
        data["is_configured"] = False
        return data
    return {
        "is_configured": row.is_configured,
        "probability_scale": row.probability_scale,
        "impact_scale": row.impact_scale,
        "risk_levels": row.risk_levels,
        "risk_matrix": row.risk_matrix,
        "acceptance": row.acceptance,
        "cia_impact_map": row.cia_impact_map,
    }


def compute_level(probability: int | None, impact: int | None, methodology: dict) -> str | None:
    """Nível de risco (level_key) pela matriz prob×impacto. None se prob/impacto ausente."""
    if probability is None or impact is None:
        return None
    return methodology.get("risk_matrix", {}).get(f"{probability}x{impact}")


def is_above_acceptance(level_key: str | None, methodology: dict) -> bool | None:
    """True se o nível NÃO atende ao critério de aceitação (acima do critério)."""
    if level_key is None:
        return None
    acceptance = methodology.get("acceptance", {})
    accepted = acceptance.get(level_key)
    if accepted is None:
        return None
    return not accepted


def derive_impact_from_cia(cia_levels: list[str], methodology: dict) -> int | None:
    """Impacto derivado = mapeamento do MAIOR valor entre C, I e A dos ativos. None se incompleto."""
    order = {lvl.value: idx for idx, lvl in enumerate(CIA_ORDER)}
    valid = [lvl for lvl in cia_levels if lvl in order]
    if not valid:
        return None
    highest = max(valid, key=lambda lvl: order[lvl])
    return methodology.get("cia_impact_map", {}).get(highest)


def validate_methodology(data: dict) -> None:
    """Valida 5 níveis por escala, 25 células e consistência de chaves (422 se inválida)."""
    def _err(msg: str):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, msg)

    for field in ("probability_scale", "impact_scale"):
        scale = data.get(field) or []
        if len(scale) != 5:
            _err(f"'{field}' deve ter exatamente 5 níveis.")
    levels = data.get("risk_levels") or []
    if not levels:
        _err("'risk_levels' não pode ser vazio.")
    level_keys = {lvl.get("key") for lvl in levels}
    matrix = data.get("risk_matrix") or {}
    expected = {f"{p}x{i}" for p in range(1, 6) for i in range(1, 6)}
    if set(matrix.keys()) != expected:
        _err("'risk_matrix' deve cobrir as 25 combinações probabilidade × impacto (1x1..5x5).")
    for cell, key in matrix.items():
        if key not in level_keys:
            _err(f"Célula {cell} referencia um nível inexistente: {key}.")
    acceptance = data.get("acceptance") or {}
    for key in level_keys:
        if key not in acceptance:
            _err(f"'acceptance' não define o critério para o nível {key}.")


def save_methodology(db: Session, tenant_id: uuid.UUID, data: dict) -> RiskMethodology:
    """Persiste a metodologia da org (cria ou atualiza). Não comita (chamador comita)."""
    validate_methodology(data)
    row = db.query(RiskMethodology).filter_by(tenant_id=tenant_id).first()
    if row is None:
        row = RiskMethodology(tenant_id=tenant_id)
        db.add(row)
    row.is_configured = True
    row.probability_scale = data["probability_scale"]
    row.impact_scale = data["impact_scale"]
    row.risk_levels = data["risk_levels"]
    row.risk_matrix = data["risk_matrix"]
    row.acceptance = data["acceptance"]
    row.cia_impact_map = data["cia_impact_map"]
    db.flush()
    return row


def recompute_all(db: Session, tenant_id: uuid.UUID) -> list[uuid.UUID]:
    """Recalcula nível inerente/residual + aceitação de todos os riscos a partir de prob/impacto
    já registrados. Retorna os ids dos riscos cuja classificação mudou (FR-008)."""
    methodology = get_or_default(db, tenant_id)
    changed: list[uuid.UUID] = []
    for risk in db.query(Risk).filter_by(tenant_id=tenant_id).all():
        before = (risk.inherent_level_key, risk.above_acceptance, risk.residual_level_key)
        risk.inherent_level_key = compute_level(risk.probability_level, risk.impact_level, methodology)
        risk.above_acceptance = is_above_acceptance(risk.inherent_level_key, methodology)
        risk.residual_level_key = compute_level(
            risk.residual_probability_level, risk.residual_impact_level, methodology
        )
        risk.residual_above_acceptance = is_above_acceptance(risk.residual_level_key, methodology)
        after = (risk.inherent_level_key, risk.above_acceptance, risk.residual_level_key)
        if before != after:
            changed.append(risk.id)
    db.flush()
    return changed
