"""SoA — consolidação a partir da avaliação corrente do Gap Analysis e detecção de divergência.

Consolidação é **aditiva e idempotente**: cria itens da SoA ausentes (pré-preenchidos via mapeamento
de status), preserva itens já editados manualmente. A divergência é derivada na leitura comparando os
campos consolidados com o **valor vivo** do `gap_assessment_item` (sem snapshot por campo).
"""

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.soa_model import Soa, SoaItem
from wtnapp.settings import GAP_TO_SOA_STATUS, GapDimension, GapStatus


# Campos consolidados (com origem no Gap) sujeitos a detecção de divergência.
CONSOLIDATED_FIELDS = (
    "applicable",
    "exclusion_justification",
    "implementation_status",
    "responsible",
    "deadline",
)


def _gap_applicable(gap_status: GapStatus) -> bool:
    return gap_status != GapStatus.not_applicable


def _gap_impl_status(gap_status: GapStatus):
    mapped = GAP_TO_SOA_STATUS.get(gap_status)
    return mapped.value if mapped is not None else None


def _norm(value):
    """Normaliza valores para comparação/exibição (enum→value, date→iso)."""
    if value is None:
        return None
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def get_or_create_soa(db: Session, tenant_id: uuid.UUID) -> Soa:
    soa = db.query(Soa).filter_by(tenant_id=tenant_id).first()
    if soa is None:
        assessment = db.query(GapAssessment).filter_by(tenant_id=tenant_id).first()
        soa = Soa(tenant_id=tenant_id, gap_assessment_id=assessment.id if assessment else None)
        db.add(soa)
        db.flush()
    return soa


def consolidate(db: Session, tenant_id: uuid.UUID) -> dict:
    """Gera/atualiza a SoA a partir da avaliação corrente do Gap. Aditivo e idempotente."""
    assessment = db.query(GapAssessment).filter_by(tenant_id=tenant_id).first()
    if assessment is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Gap Analysis ausente. Adote o catálogo e avalie antes de gerar a SoA.",
        )

    soa = get_or_create_soa(db, tenant_id)
    soa.gap_assessment_id = assessment.id

    # Itens do Anexo A da avaliação (não descontinuados), com o controle do catálogo.
    rows = (
        db.query(GapAssessmentItem, GapCatalogItem)
        .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
        .filter(
            GapAssessmentItem.assessment_id == assessment.id,
            GapCatalogItem.dimension == GapDimension.annex_a,
            GapCatalogItem.is_discontinued.is_(False),
        )
        .all()
    )

    existing = {
        s.catalog_item_id: s
        for s in db.query(SoaItem).filter(SoaItem.soa_id == soa.id).all()
    }

    added = 0
    preserved = 0
    for gap_item, cat in rows:
        if cat.id in existing:
            # Preserva edição manual; só garante o vínculo de origem.
            si = existing[cat.id]
            if si.gap_assessment_item_id is None:
                si.gap_assessment_item_id = gap_item.id
            preserved += 1
            continue
        applicable = _gap_applicable(gap_item.status)
        mapped = GAP_TO_SOA_STATUS.get(gap_item.status)
        db.add(SoaItem(
            tenant_id=tenant_id,
            soa_id=soa.id,
            catalog_item_id=cat.id,
            gap_assessment_item_id=gap_item.id,
            ref_code=cat.ref_code,
            theme=cat.theme,
            name=cat.name,
            applicable=applicable,
            inclusion_reasons=[],
            exclusion_justification=gap_item.exclusion_justification if not applicable else None,
            implementation_status=mapped,
            responsible=gap_item.responsible,
            deadline=gap_item.deadline,
        ))
        added += 1

    db.commit()
    return {"soa_id": str(soa.id), "added": added, "preserved": preserved}


def compute_divergence(db: Session, item: SoaItem) -> list[dict]:
    """Compara os campos consolidados da SoA com o valor vivo do Gap. Lista divergências."""
    if item.gap_assessment_item_id is None:
        return []
    gap = db.get(GapAssessmentItem, item.gap_assessment_item_id)
    if gap is None:
        return []

    gap_values = {
        "applicable": _gap_applicable(gap.status),
        "exclusion_justification": gap.exclusion_justification,
        "implementation_status": _gap_impl_status(gap.status),
        "responsible": gap.responsible,
        "deadline": gap.deadline,
    }
    soa_values = {
        "applicable": item.applicable,
        "exclusion_justification": item.exclusion_justification,
        "implementation_status": item.implementation_status,
        "responsible": item.responsible,
        "deadline": item.deadline,
    }

    out: list[dict] = []
    for field in CONSOLIDATED_FIELDS:
        soa_v = _norm(soa_values[field])
        gap_v = _norm(gap_values[field])
        if soa_v != gap_v:
            out.append({"field": field, "soa_value": soa_v, "gap_value": gap_v})
    return out


def reconcile(db: Session, item: SoaItem, fields: list[str]) -> list[str]:
    """Aplica o valor vivo do Gap aos campos indicados (ou a todos divergentes se vazio)."""
    divergences = {d["field"]: d for d in compute_divergence(db, item)}
    target = fields or list(divergences.keys())
    gap = db.get(GapAssessmentItem, item.gap_assessment_item_id) if item.gap_assessment_item_id else None
    if gap is None:
        return []

    applied: list[str] = []
    for field in target:
        if field not in divergences:
            continue
        if field == "applicable":
            item.applicable = _gap_applicable(gap.status)
        elif field == "exclusion_justification":
            item.exclusion_justification = gap.exclusion_justification
        elif field == "implementation_status":
            mapped = GAP_TO_SOA_STATUS.get(gap.status)
            item.implementation_status = mapped
        elif field == "responsible":
            item.responsible = gap.responsible
        elif field == "deadline":
            item.deadline = gap.deadline
        applied.append(field)
    return applied
