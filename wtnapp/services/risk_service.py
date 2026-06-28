"""Registro de risco — geração de código, derivação de impacto, avaliação e histórico (Feature 012)."""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.asset_item_model import AssetItem
from wtnapp.models.risk_catalog_model import OrgThreat, OrgVulnerability
from wtnapp.models.risk_model import Risk, RiskAssetLink, RiskEvent
from wtnapp.services import risk_methodology_service as methodology_service
from wtnapp.settings import RISK_CODE_PREFIX, RiskEventType, RiskStatus


def next_code(db: Session, tenant_id: uuid.UUID) -> str:
    count = db.query(func.count(Risk.id)).filter(Risk.tenant_id == tenant_id).scalar() or 0
    return f"{RISK_CODE_PREFIX}-{count + 1:04d}"


def record_event(db: Session, tenant_id, risk_id, event_type: RiskEventType, *,
                 field=None, old=None, new=None, reason=None, actor_id=None) -> None:
    db.add(RiskEvent(
        tenant_id=tenant_id, risk_id=risk_id, event_type=event_type.value,
        field_name=field, old_value=None if old is None else str(old),
        new_value=None if new is None else str(new), reason=reason, actor_id=actor_id,
    ))


def _assert_catalog_refs(db: Session, tenant_id, threat_id, vulnerability_id) -> None:
    threat = db.query(OrgThreat).filter_by(id=threat_id, tenant_id=tenant_id).first()
    vuln = db.query(OrgVulnerability).filter_by(id=vulnerability_id, tenant_id=tenant_id).first()
    if threat is None or vuln is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")


def _linked_assets(db: Session, tenant_id, risk_id) -> list[AssetItem]:
    return (
        db.query(AssetItem)
        .join(RiskAssetLink, RiskAssetLink.asset_item_id == AssetItem.id)
        .filter(RiskAssetLink.tenant_id == tenant_id, RiskAssetLink.risk_id == risk_id)
        .all()
    )


def derive_impact(db: Session, tenant_id, risk_id, methodology: dict) -> int | None:
    """Impacto derivado da CIA (maior valor entre C, I e A dos ativos vinculados)."""
    assets = _linked_assets(db, tenant_id, risk_id)
    cia_values: list[str] = []
    for a in assets:
        for field in (a.confidentiality, a.integrity, a.availability):
            if field is not None:
                cia_values.append(field.value)
    return methodology_service.derive_impact_from_cia(cia_values, methodology)


def create_risk(db: Session, ctx: OrgContext, data: dict) -> Risk:
    tenant_id = ctx.tenant_id
    if not (data.get("title") or "").strip() or not (data.get("description") or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Título e descrição são obrigatórios.")
    _assert_catalog_refs(db, tenant_id, data["threat_id"], data["vulnerability_id"])

    risk = Risk(
        tenant_id=tenant_id, code=next_code(db, tenant_id), title=data["title"].strip(),
        description=data["description"].strip(), threat_id=data["threat_id"],
        vulnerability_id=data["vulnerability_id"], status=RiskStatus.identified,
        created_by=ctx.principal.user.id,
    )
    db.add(risk)
    db.flush()

    for asset_id in data.get("asset_item_ids") or []:
        asset = db.query(AssetItem).filter_by(id=asset_id, tenant_id=tenant_id).first()
        if asset is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
        db.add(RiskAssetLink(tenant_id=tenant_id, risk_id=risk.id, asset_item_id=asset_id))

    record_event(db, tenant_id, risk.id, RiskEventType.created, actor_id=ctx.principal.user.id)
    db.commit()
    db.refresh(risk)
    return risk


def get_risk(db: Session, ctx: OrgContext, risk_id) -> Risk:
    risk = db.query(Risk).filter_by(id=risk_id, tenant_id=ctx.tenant_id).first()
    if risk is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    return risk


def asset_ids(db: Session, tenant_id, risk_id) -> list[uuid.UUID]:
    return [
        r.asset_item_id
        for r in db.query(RiskAssetLink).filter_by(tenant_id=tenant_id, risk_id=risk_id).all()
    ]


def evaluate_risk(db: Session, ctx: OrgContext, risk_id, data: dict) -> Risk:
    """Avalia/edita prob, impacto (derivado/override), dono. Calcula nível + aceitação; eventos."""
    tenant_id = ctx.tenant_id
    actor = ctx.principal.user.id
    risk = get_risk(db, ctx, risk_id)
    methodology = methodology_service.get_or_default(db, tenant_id)

    has_assets = bool(asset_ids(db, tenant_id, risk_id))
    derived = derive_impact(db, tenant_id, risk_id, methodology) if has_assets else None
    risk.impact_derived_level = derived

    # Probabilidade
    if "probability_level" in data and data["probability_level"] is not None:
        if risk.probability_level != data["probability_level"]:
            record_event(db, tenant_id, risk_id, RiskEventType.probability_change,
                         field="probability_level", old=risk.probability_level,
                         new=data["probability_level"], actor_id=actor)
        risk.probability_level = data["probability_level"]

    # Impacto: derivado da CIA por padrão; override manual exige justificativa
    requested_impact = data.get("impact_level")
    if requested_impact is not None:
        is_override = derived is None or requested_impact != derived
        if is_override and derived is not None:
            if not (data.get("impact_override_reason") or "").strip():
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Justificativa obrigatória ao sobrescrever o impacto derivado da CIA.",
                )
            risk.impact_is_override = True
            risk.impact_override_reason = data["impact_override_reason"].strip()
        else:
            risk.impact_is_override = False
            risk.impact_override_reason = None
        if risk.impact_level != requested_impact:
            record_event(db, tenant_id, risk_id, RiskEventType.impact_change, field="impact_level",
                         old=risk.impact_level, new=requested_impact, actor_id=actor)
        risk.impact_level = requested_impact
    elif derived is not None:
        risk.impact_level = derived
        risk.impact_is_override = False
        risk.impact_override_reason = None
    elif not has_assets and risk.impact_level is None:
        # Cenário sem ativos exige impacto manual (não há CIA de onde derivar).
        pass

    # Dono
    if "owner_user_id" in data and data["owner_user_id"] != risk.owner_user_id:
        record_event(db, tenant_id, risk_id, RiskEventType.owner_change, field="owner_user_id",
                     old=risk.owner_user_id, new=data["owner_user_id"], actor_id=actor)
        risk.owner_user_id = data["owner_user_id"]

    # Nível + aceitação
    old_level = risk.inherent_level_key
    risk.inherent_level_key = methodology_service.compute_level(
        risk.probability_level, risk.impact_level, methodology
    )
    risk.above_acceptance = methodology_service.is_above_acceptance(risk.inherent_level_key, methodology)
    if old_level != risk.inherent_level_key:
        record_event(db, tenant_id, risk_id, RiskEventType.level_change, field="inherent_level_key",
                     old=old_level, new=risk.inherent_level_key, actor_id=actor,
                     reason=data.get("reason"))

    # Transição de status: avaliado quando prob+impacto+dono presentes
    if (risk.probability_level is not None and risk.impact_level is not None
            and risk.owner_user_id is not None and risk.status == RiskStatus.identified):
        risk.status = RiskStatus.assessed

    risk.updated_by = actor
    db.commit()
    db.refresh(risk)
    return risk


def archive_risk(db: Session, ctx: OrgContext, risk_id, reason: str) -> Risk:
    if not (reason or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Justificativa obrigatória para arquivar.")
    risk = get_risk(db, ctx, risk_id)
    risk.is_archived = True
    risk.archive_reason = reason
    record_event(db, ctx.tenant_id, risk_id, RiskEventType.archived, reason=reason,
                 actor_id=ctx.principal.user.id)
    db.commit()
    db.refresh(risk)
    return risk


def list_risks(db: Session, ctx: OrgContext, filters: dict) -> list[Risk]:
    q = db.query(Risk).filter(Risk.tenant_id == ctx.tenant_id)
    if not filters.get("include_archived"):
        q = q.filter(Risk.is_archived == False)  # noqa: E712
    if filters.get("status"):
        q = q.filter(Risk.status == filters["status"])
    if filters.get("level"):
        q = q.filter(Risk.inherent_level_key == filters["level"])
    if filters.get("owner_user_id"):
        q = q.filter(Risk.owner_user_id == filters["owner_user_id"])
    if filters.get("above_acceptance") is not None:
        q = q.filter(Risk.above_acceptance == filters["above_acceptance"])
    if filters.get("treatment_option"):
        q = q.filter(Risk.treatment_option == filters["treatment_option"])
    if filters.get("q"):
        term = f"%{filters['q'].lower()}%"
        q = q.filter(func.lower(Risk.title).like(term) | func.lower(Risk.description).like(term))
    risks = q.order_by(Risk.code).all()
    if filters.get("asset_item_id"):
        ids = {
            r.risk_id for r in db.query(RiskAssetLink).filter_by(
                tenant_id=ctx.tenant_id, asset_item_id=filters["asset_item_id"]
            ).all()
        }
        risks = [r for r in risks if r.id in ids]
    return risks
