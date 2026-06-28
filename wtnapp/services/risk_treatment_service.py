"""Tratamento de risco, plano (Documento Controlado) e insumo da SoA (Feature 012).

Este serviço NÃO escreve em `soa`/`soa_item`: o `soa_feed` apenas expõe o vínculo controle ← risco
(read-only) para a futura feature de finalização da SoA.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.risk_model import Risk, RiskAssetLink, RiskPlan, RiskTreatmentControl
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import risk_methodology_service as methodology_service
from wtnapp.services import risk_service
from wtnapp.settings import (
    Classification,
    DocStatus,
    DocType,
    RiskEventType,
    RiskStatus,
    RiskTreatmentOption,
    SoaInclusionReason,
)


def set_treatment(db: Session, ctx: OrgContext, risk_id, data: dict) -> Risk:
    tenant_id = ctx.tenant_id
    actor = ctx.principal.user.id
    risk = risk_service.get_risk(db, ctx, risk_id)
    option = data["treatment_option"]

    old = risk.treatment_option.value if risk.treatment_option else None
    risk.treatment_option = option
    risk.treatment_note = data.get("treatment_note")
    record_event = risk_service.record_event
    record_event(db, tenant_id, risk_id, RiskEventType.treatment_decision, field="treatment_option",
                 old=old, new=option.value, reason=data.get("reason"), actor_id=actor)

    methodology = methodology_service.get_or_default(db, tenant_id)
    if data.get("residual_probability_level") is not None:
        risk.residual_probability_level = data["residual_probability_level"]
    if data.get("residual_impact_level") is not None:
        risk.residual_impact_level = data["residual_impact_level"]
    risk.residual_level_key = methodology_service.compute_level(
        risk.residual_probability_level, risk.residual_impact_level, methodology
    )
    risk.residual_above_acceptance = methodology_service.is_above_acceptance(
        risk.residual_level_key, methodology
    )

    if option != RiskTreatmentOption.accept and risk.status == RiskStatus.assessed:
        risk.status = RiskStatus.in_treatment
    risk.updated_by = actor
    db.commit()
    db.refresh(risk)
    return risk


def add_control(db: Session, ctx: OrgContext, risk_id, data: dict) -> RiskTreatmentControl:
    tenant_id = ctx.tenant_id
    risk = risk_service.get_risk(db, ctx, risk_id)

    gap_id = data.get("gap_catalog_item_id")
    custom = (data.get("custom_control_label") or "").strip() or None
    if bool(gap_id) == bool(custom):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Informe exatamente um: controle do catálogo de Gap OU controle custom.",
        )
    if gap_id is not None:
        gap = db.query(GapCatalogItem).filter_by(id=gap_id, tenant_id=tenant_id).first()
        if gap is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")

    # Tratamento "mitigar" exige responsável + prazo por controle (FR-044).
    if risk.treatment_option == RiskTreatmentOption.mitigate:
        if data.get("responsible_user_id") is None or data.get("due_date") is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Controle de mitigação exige responsável e prazo.",
            )

    control = RiskTreatmentControl(
        tenant_id=tenant_id, risk_id=risk_id, gap_catalog_item_id=gap_id,
        custom_control_label=custom, responsible_user_id=data.get("responsible_user_id"),
        due_date=data.get("due_date"), note=data.get("note"), created_by=ctx.principal.user.id,
    )
    db.add(control)
    risk_service.record_event(db, tenant_id, risk_id, RiskEventType.control_add, field="control",
                              new=custom or str(gap_id), actor_id=ctx.principal.user.id)
    db.commit()
    db.refresh(control)
    return control


def list_controls(db: Session, ctx: OrgContext, risk_id) -> list[RiskTreatmentControl]:
    risk_service.get_risk(db, ctx, risk_id)
    return db.query(RiskTreatmentControl).filter_by(tenant_id=ctx.tenant_id, risk_id=risk_id).all()


def remove_control(db: Session, ctx: OrgContext, risk_id, control_id) -> None:
    control = db.query(RiskTreatmentControl).filter_by(
        id=control_id, tenant_id=ctx.tenant_id, risk_id=risk_id
    ).first()
    if control is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    label = control.custom_control_label or str(control.gap_catalog_item_id)
    db.delete(control)
    risk_service.record_event(db, ctx.tenant_id, risk_id, RiskEventType.control_remove,
                              field="control", old=label, actor_id=ctx.principal.user.id)
    db.commit()


def accept_risk(db: Session, ctx: OrgContext, risk_id, data: dict) -> Risk:
    risk = risk_service.get_risk(db, ctx, risk_id)
    if not (data.get("acceptance_reason") or "").strip() or not data.get("accepted_owner_user_id"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Aceitação exige justificativa e o dono do risco.",
        )
    risk.treatment_option = RiskTreatmentOption.accept
    risk.acceptance_reason = data["acceptance_reason"].strip()
    risk.accepted_owner_user_id = data["accepted_owner_user_id"]
    risk.accepted_by_user_id = ctx.principal.user.id
    risk.accepted_at = datetime.now(timezone.utc)
    risk.status = RiskStatus.accepted
    risk_service.record_event(db, ctx.tenant_id, risk_id, RiskEventType.accepted,
                              reason=data["acceptance_reason"].strip(), actor_id=ctx.principal.user.id)
    db.commit()
    db.refresh(risk)
    return risk


def soa_feed(db: Session, tenant_id: uuid.UUID) -> list[dict]:
    """Insumo read-only da SoA: para cada controle do Gap selecionado, os riscos tratados.

    NÃO escreve na SoA — apenas agrega o vínculo controle ← risco.
    """
    controls = (
        db.query(RiskTreatmentControl)
        .filter(RiskTreatmentControl.tenant_id == tenant_id,
                RiskTreatmentControl.gap_catalog_item_id.isnot(None))
        .all()
    )
    by_gap: dict[uuid.UUID, dict] = {}
    for c in controls:
        risk = db.query(Risk).filter_by(id=c.risk_id, tenant_id=tenant_id).first()
        if risk is None or risk.is_archived:
            continue
        entry = by_gap.setdefault(c.gap_catalog_item_id, {"risk_ids": [], "risk_codes": []})
        if risk.id not in entry["risk_ids"]:
            entry["risk_ids"].append(risk.id)
            entry["risk_codes"].append(risk.code)
    feed = []
    for gap_id, entry in by_gap.items():
        gap = db.query(GapCatalogItem).filter_by(id=gap_id, tenant_id=tenant_id).first()
        feed.append({
            "gap_catalog_item_id": gap_id,
            "ref_code": gap.ref_code if gap else None,
            "inclusion_reason": SoaInclusionReason.risk_treatment.value,
            "risk_ids": entry["risk_ids"],
            "risk_codes": entry["risk_codes"],
        })
    return feed


def get_or_create_plan(db: Session, tenant_id: uuid.UUID) -> RiskPlan:
    plan = db.query(RiskPlan).filter_by(tenant_id=tenant_id).first()
    if plan is None:
        plan = RiskPlan(tenant_id=tenant_id)
        db.add(plan)
        db.commit()
        db.refresh(plan)
    return plan


def submit_plan(db: Session, ctx: OrgContext) -> RiskPlan:
    plan = get_or_create_plan(db, ctx.tenant_id)
    cds.submit_review(db, plan)
    risk_service.record_event(db, ctx.tenant_id, None, RiskEventType.plan_submitted,
                              actor_id=ctx.principal.user.id)
    db.commit()
    db.refresh(plan)
    return plan


def _plan_snapshot(db: Session, tenant_id: uuid.UUID) -> dict:
    risks = db.query(Risk).filter_by(tenant_id=tenant_id, is_archived=False).all()
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "risks": [
            {
                "code": r.code, "title": r.title, "status": r.status.value,
                "inherent_level": r.inherent_level_key, "residual_level": r.residual_level_key,
                "treatment_option": r.treatment_option.value if r.treatment_option else None,
                "above_acceptance": r.above_acceptance,
            }
            for r in risks
        ],
        "soa_feed": [
            {**e, "gap_catalog_item_id": str(e["gap_catalog_item_id"]),
             "risk_ids": [str(x) for x in e["risk_ids"]]}
            for e in soa_feed(db, tenant_id)
        ],
    }


def approve_plan(db: Session, ctx: OrgContext, data: dict):
    """Aprova o plano (gate duro: riscos avaliados). Cria versão imutável. Assinatura opcional."""
    tenant_id = ctx.tenant_id
    plan = get_or_create_plan(db, tenant_id)

    # Gate duro a jusante: todos os riscos não arquivados devem estar avaliados (FR-027).
    unevaluated = db.query(Risk).filter(
        Risk.tenant_id == tenant_id, Risk.is_archived == False,  # noqa: E712
        Risk.status == RiskStatus.identified,
    ).count()
    if unevaluated > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Existem {unevaluated} risco(s) não avaliado(s). Avalie-os antes de aprovar o plano.",
        )
    active = db.query(Risk).filter_by(tenant_id=tenant_id, is_archived=False).count()
    if active == 0:
        raise HTTPException(status.HTTP_409_CONFLICT, "Não há riscos para consolidar no plano.")

    classification = Classification(data.get("classification") or Classification.uso_interno.value)
    signed = bool(data.get("sign"))
    change_nature = data.get("change_nature") or "Aprovação do Plano de Tratamento de Riscos"
    if signed:
        change_nature = f"{change_nature} (assinado)"

    version = cds.approve_document(
        db=db, artifact=plan, doc_type=DocType.risk_treatment_plan,
        actor_id=ctx.principal.user.id, classification=classification,
        next_review_at=data.get("next_review_at"), change_nature=change_nature,
        snapshot_factory=lambda: _plan_snapshot(db, tenant_id),
    )
    risk_service.record_event(db, tenant_id, None, RiskEventType.plan_approved,
                              new=str(version.version_number), reason=change_nature,
                              actor_id=ctx.principal.user.id)
    db.commit()
    return version


def list_plan_versions(db: Session, ctx: OrgContext):
    plan = get_or_create_plan(db, ctx.tenant_id)
    return cds.list_versions(db, ctx.tenant_id, DocType.risk_treatment_plan, plan.id)


def asset_links(db: Session, ctx: OrgContext, asset_id) -> dict:
    """Preenche os placeholders do detalhe do ativo: ameaças/vulnerabilidades/riscos/controles."""
    from wtnapp.models.asset_item_model import AssetItem
    from wtnapp.models.risk_catalog_model import (
        AssetThreatLink, AssetVulnerabilityLink, OrgThreat, OrgVulnerability,
    )
    tenant_id = ctx.tenant_id
    asset = db.query(AssetItem).filter_by(id=asset_id, tenant_id=tenant_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")

    threats = (
        db.query(OrgThreat)
        .join(AssetThreatLink, AssetThreatLink.threat_id == OrgThreat.id)
        .filter(AssetThreatLink.tenant_id == tenant_id, AssetThreatLink.asset_item_id == asset_id)
        .all()
    )
    vulns = (
        db.query(OrgVulnerability)
        .join(AssetVulnerabilityLink, AssetVulnerabilityLink.vulnerability_id == OrgVulnerability.id)
        .filter(AssetVulnerabilityLink.tenant_id == tenant_id,
                AssetVulnerabilityLink.asset_item_id == asset_id)
        .all()
    )
    risk_ids = {
        link.risk_id for link in db.query(RiskAssetLink).filter_by(
            tenant_id=tenant_id, asset_item_id=asset_id
        ).all()
    }
    risks = db.query(Risk).filter(Risk.id.in_(risk_ids)).all() if risk_ids else []
    controls = (
        db.query(RiskTreatmentControl)
        .filter(RiskTreatmentControl.tenant_id == tenant_id,
                RiskTreatmentControl.risk_id.in_(risk_ids))
        .all()
    ) if risk_ids else []
    return {"threats": threats, "vulnerabilities": vulns, "risks": risks, "controls": controls}
