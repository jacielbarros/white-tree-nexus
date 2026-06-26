"""Gap Metrics Service — cálculo de aderência ponderada e lista de lacunas.

Fórmula: Atende=1.0, Parcial=0.5, Não atende=0.0.
N/A e not_filled são excluídos do denominador.
Denominador zero → None (exibido como "—" no frontend).
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Optional

from sqlalchemy.orm import Session

from wtnapp.models.gap_assessment_model import GapAssessmentItem
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.settings import GapDimension, GapPriority, GapStatus, GapTheme

_WEIGHT: dict[GapStatus, float] = {
    GapStatus.meets: 1.0,
    GapStatus.partial: 0.5,
    GapStatus.not_meet: 0.0,
}

_PRIORITY_ORDER = {
    GapPriority.critical: 0,
    GapPriority.high: 1,
    GapPriority.medium: 2,
    GapPriority.low: 3,
    None: 4,
}


def _adherence(items: list[GapAssessmentItem]) -> Optional[float]:
    """Aderência DOS AVALIADOS: exclui N/A e não-preenchidos do denominador.

    Métrica de qualidade do que já foi avaliado — pode "parecer" alta com baixa cobertura.
    """
    applicable = [i for i in items if i.status in _WEIGHT]
    if not applicable:
        return None
    total = sum(_WEIGHT[i.status] for i in applicable)
    return round(total / len(applicable), 4)


def _consolidated(items: list[GapAssessmentItem]) -> Optional[float]:
    """Conformidade CONSOLIDADA: denominador = total exceto N/A; não-preenchido conta como 0.

    Número honesto da postura — cobertura baixa puxa o valor para baixo (não mascara).
    """
    applicable = [i for i in items if i.status != GapStatus.not_applicable]
    if not applicable:
        return None
    score = sum(_WEIGHT.get(i.status, 0.0) for i in applicable)
    return round(score / len(applicable), 4)


def _dimension_metric(items: list[GapAssessmentItem]) -> dict:
    return {
        "conformance": _consolidated(items),
        "adherence_evaluated": _adherence(items),
        "evaluated": sum(1 for i in items if i.status != GapStatus.not_filled),
        "total": len(items),
    }


def compute_dashboard(db: Session, tenant_id: uuid.UUID, assessment_id: uuid.UUID) -> dict:
    items = (
        db.query(GapAssessmentItem)
        .filter(
            GapAssessmentItem.tenant_id == tenant_id,
            GapAssessmentItem.assessment_id == assessment_id,
        )
        .all()
    )

    if not items:
        return {
            "overall_adherence": None,
            "consolidated_conformance": None,
            "total_items": 0,
            "evaluated_items": 0,
            "dimensions": {},
            "by_dimension": {},
            "by_clause": {},
            "by_theme": {},
            "status_distribution": {},
            "completeness": 0.0,
        }

    # Carrega catálogo para obter dimension/theme
    catalog_ids = [i.catalog_item_id for i in items]
    catalog_map: dict[uuid.UUID, GapCatalogItem] = {
        c.id: c
        for c in db.query(GapCatalogItem).filter(GapCatalogItem.id.in_(catalog_ids)).all()
    }

    by_dim: dict[str, list] = defaultdict(list)
    by_clause: dict[str, list] = defaultdict(list)
    by_theme: dict[str, list] = defaultdict(list)
    dist: dict[str, int] = defaultdict(int)
    filled = 0

    for item in items:
        cat = catalog_map.get(item.catalog_item_id)
        dist[item.status.value] += 1
        if item.status != GapStatus.not_filled:
            filled += 1

        if cat:
            by_dim[cat.dimension.value].append(item)
            if cat.dimension == GapDimension.clause:
                by_clause[cat.ref_code].append(item)
            elif cat.theme:
                by_theme[cat.theme.value].append(item)

    completeness = round(filled / len(items), 4) if items else 0.0

    return {
        # Âncora honesta: conformidade consolidada sobre a JORNADA COMPLETA (cláusulas + Anexo A).
        "consolidated_conformance": _consolidated(items),
        "total_items": len(items),
        "evaluated_items": filled,
        # Decomposição por dimensão (cláusulas 4–10 vs Anexo A): conformância + cobertura.
        "dimensions": {k: _dimension_metric(v) for k, v in by_dim.items()},
        # Aderência DOS AVALIADOS (métrica de apoio, demovida no frontend).
        "overall_adherence": _adherence(items),
        "by_dimension": {k: _adherence(v) for k, v in by_dim.items()},
        "by_clause": {k: _adherence(v) for k, v in by_clause.items()},
        "by_theme": {k: _adherence(v) for k, v in by_theme.items()},
        "status_distribution": dict(dist),
        "completeness": completeness,
    }


def list_gaps(
    db: Session,
    tenant_id: uuid.UUID,
    assessment_id: uuid.UUID,
    order_by: str = "priority",
) -> list[GapAssessmentItem]:
    """Retorna itens aplicáveis não conformes (partial + not_meet), ordenados por prioridade."""
    items = (
        db.query(GapAssessmentItem)
        .filter(
            GapAssessmentItem.tenant_id == tenant_id,
            GapAssessmentItem.assessment_id == assessment_id,
            GapAssessmentItem.status.in_([GapStatus.partial, GapStatus.not_meet]),
        )
        .all()
    )
    return sorted(items, key=lambda i: _PRIORITY_ORDER.get(i.priority, 4))
