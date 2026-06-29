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
from wtnapp.settings import GAP_TO_SOA_STATUS, GapDimension, GapStatus, SoaInclusionReason


# Campos consolidados (com origem no Gap) sujeitos a detecção de divergência.
CONSOLIDATED_FIELDS = (
    "applicable",
    "exclusion_justification",
    "implementation_status",
    "responsible",
    "deadline",
)

# Razão de inclusão dirigida pelo tratamento de risco (Feature 013).
RISK_REASON = SoaInclusionReason.risk_treatment.value


# ── Insumo de risco (read-only) ──────────────────────────────────────────────

def build_feed_index(db: Session, tenant_id: uuid.UUID) -> dict:
    """Calcula o soa-feed do módulo de Risco UMA vez e indexa por gap_catalog_item_id."""
    from wtnapp.services import risk_treatment_service  # lazy: evita ciclo de import

    return {e["gap_catalog_item_id"]: e for e in risk_treatment_service.soa_feed(db, tenant_id)}


def _risk_links_from_feed(entry: dict) -> list[dict]:
    return [
        {"risk_id": str(rid), "risk_code": code}
        for rid, code in zip(entry.get("risk_ids", []), entry.get("risk_codes", []))
    ]


def derive_origin(item: SoaItem) -> str:
    """Origem da inclusão (derivada): risk | manual | risk+manual | none."""
    if not item.applicable:
        return "none"
    reasons = item.inclusion_reasons or []
    has_risk = RISK_REASON in reasons
    has_manual = any(r != RISK_REASON for r in reasons)
    if has_risk and has_manual:
        return "risk+manual"
    if has_risk:
        return "risk"
    if has_manual:
        return "manual"
    return "none"


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

    # --- Passo dirigido por risco (Feature 013): aditivo, 1ª-mão, idempotente ---
    # Lê o valor VIVO do soa-feed. Aplica risco só a item que nunca carregou vínculo de risco;
    # drift posterior vira divergência (compute_risk_divergence), reconciliável explicitamente.
    db.flush()  # garante que os itens recém-criados no passo Gap apareçam na query abaixo
    feed_index = build_feed_index(db, tenant_id)
    items_by_catalog = {
        s.catalog_item_id: s for s in db.query(SoaItem).filter(SoaItem.soa_id == soa.id).all()
    }
    risk_applied = 0
    out_of_scope: list[str] = []
    for gap_catalog_id, entry in feed_index.items():
        si = items_by_catalog.get(gap_catalog_id)
        if si is None:
            # Controle tratado por risco fora do conjunto Anexo A da SoA → notice (não cria item).
            out_of_scope.append(entry.get("ref_code") or str(gap_catalog_id))
            continue
        already_risk = RISK_REASON in (si.inclusion_reasons or []) or bool(si.risk_links)
        if already_risk:
            continue  # preserva edições; mudança no insumo vira divergência
        reasons = list(si.inclusion_reasons or [])
        reasons.append(RISK_REASON)
        si.inclusion_reasons = reasons
        si.applicable = True
        si.risk_links = _risk_links_from_feed(entry)
        risk_applied += 1

    db.commit()
    return {
        "soa_id": str(soa.id),
        "added": added,
        "preserved": preserved,
        "risk_applied": risk_applied,
        "out_of_scope": out_of_scope,
    }


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
            # source/source_value (Feature 013) + gap_value (compat).
            out.append({
                "field": field, "source": "gap",
                "soa_value": soa_v, "source_value": gap_v, "gap_value": gap_v,
            })
    return out


def compute_risk_divergence(db: Session, item: SoaItem, feed_index: dict) -> list[dict]:
    """Divergências contra o insumo de risco VIVO (soa-feed). Fonte 'risk' (Feature 013).

    (a) feed aponta o controle mas a SoA não o inclui por risco;
    (b) item incluído por risco cujo feed não aponta mais o controle (risco órfão);
    (c) conjunto de riscos vinculados difere do feed.
    """
    entry = feed_index.get(item.catalog_item_id)
    has_risk_reason = RISK_REASON in (item.inclusion_reasons or [])
    out: list[dict] = []

    if entry is not None:
        feed_codes = sorted(l["risk_code"] for l in _risk_links_from_feed(entry))
        soa_codes = sorted(l.get("risk_code") for l in (item.risk_links or []))
        if not item.applicable or not has_risk_reason:
            out.append({
                "field": "risk_inclusion", "source": "risk",
                "soa_value": "não incluído por risco", "source_value": feed_codes,
            })
        elif feed_codes != soa_codes:
            out.append({
                "field": "risk_links", "source": "risk",
                "soa_value": soa_codes, "source_value": feed_codes,
            })
    elif has_risk_reason:
        out.append({
            "field": "risk_inclusion", "source": "risk",
            "soa_value": "incluído por risco", "source_value": "sem risco correspondente",
        })
    return out


def _reconcile_gap(db: Session, item: SoaItem, fields: list[str]) -> list[str]:
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
            item.implementation_status = GAP_TO_SOA_STATUS.get(gap.status)
        elif field == "responsible":
            item.responsible = gap.responsible
        elif field == "deadline":
            item.deadline = gap.deadline
        applied.append(field)
    return applied


def _reconcile_risk(db: Session, item: SoaItem, fields: list[str], feed_index: dict) -> list[str]:
    """Aplica o valor vivo do insumo de risco. Preserva as razões manuais.

    Se a remoção do vínculo de risco deixar um item aplicável sem nenhuma razão, ele permanece
    aplicável e fica INCOMPLETO (derivado na leitura) — sem auto-flip para 'Não aplicável'.
    """
    risk_divs = {d["field"]: d for d in compute_risk_divergence(db, item, feed_index)}
    if not risk_divs:
        return []
    if fields and not any(f in ("risk_inclusion", "risk_links") for f in fields):
        return []

    entry = feed_index.get(item.catalog_item_id)
    if entry is not None:
        # Incluir + razão de risco + riscos do feed (sem remover razões manuais).
        reasons = list(item.inclusion_reasons or [])
        if RISK_REASON not in reasons:
            reasons.append(RISK_REASON)
        item.inclusion_reasons = reasons
        item.applicable = True
        item.risk_links = _risk_links_from_feed(entry)
    else:
        # Remover razão de risco + riscos órfãos; manuais preservadas; pode ficar incompleto.
        item.inclusion_reasons = [r for r in (item.inclusion_reasons or []) if r != RISK_REASON]
        item.risk_links = []
    return list(risk_divs.keys())


def reconcile(db: Session, item: SoaItem, fields: list[str], source: str = "all",
              feed_index: dict | None = None) -> list[str]:
    """Reconcilia divergências por fonte (gap e/ou risco). Ação explícita do usuário."""
    applied: list[str] = []
    if source in ("all", "gap"):
        applied.extend(_reconcile_gap(db, item, fields))
    if source in ("all", "risk"):
        if feed_index is None:
            feed_index = build_feed_index(db, item.tenant_id)
        applied.extend(_reconcile_risk(db, item, fields, feed_index))
    return applied
