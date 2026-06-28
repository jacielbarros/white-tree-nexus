"""Módulo de Gestão de Riscos (Feature 012) — três fases num router.

Leitura: `view_risk`. Escrita: `manage_risk`. Aprovação do plano: `approve_risk_plan`.
Tudo escopado por `ctx.tenant_id`; cross-tenant ⇒ 404 genérico + audit.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.risk_catalog_model import OrgThreat, OrgVulnerability
from wtnapp.models.risk_model import Risk, RiskEvent
from wtnapp.schemas.risk_schema import (
    AcceptRequest,
    AdoptResult,
    ArchiveRequest,
    ControlCreate,
    ControlResponse,
    HeatmapCell,
    LinkAssetRequest,
    MethodologyResponse,
    MethodologyUpdate,
    PlanApprove,
    PlanResponse,
    RiskCreate,
    RiskEvaluate,
    RiskEventResponse,
    RiskResponse,
    SoaFeedItem,
    ThreatCreate,
    ThreatResponse,
    TreatmentUpdate,
    VulnerabilityCreate,
    VulnerabilityResponse,
)
from wtnapp.services import (
    risk_catalog_service,
    risk_metrics_service,
    risk_methodology_service,
    risk_service,
    risk_treatment_service,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/risk", tags=["risk"])

db_dependency = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_risk"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_risk"))]
approve_dep = Annotated[OrgContext, Depends(require_permission("approve_risk_plan"))]


def _audit(request, ctx, operation, entity_type, entity_id=None, details=None):
    AuditService.log_from_request(
        request=request, operation=operation, outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id, entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None, details=details,
    )


def _risk_to_response(db: Session, ctx: OrgContext, risk: Risk) -> RiskResponse:
    data = RiskResponse.model_validate(risk).model_dump()
    data["asset_item_ids"] = risk_service.asset_ids(db, ctx.tenant_id, risk.id)
    return RiskResponse(**data)


# --- Metodologia ---

@router.get("/methodology", response_model=MethodologyResponse)
def get_methodology(db: db_dependency, ctx: view_dep):
    return risk_methodology_service.get_or_default(db, ctx.tenant_id)


@router.put("/methodology", response_model=MethodologyResponse)
def put_methodology(payload: MethodologyUpdate, request: Request, db: db_dependency, ctx: manage_dep):
    data = payload.model_dump()
    data["cia_impact_map"] = {k: int(v) for k, v in data["cia_impact_map"].items()}
    risk_methodology_service.save_methodology(db, ctx.tenant_id, data)
    changed = risk_methodology_service.recompute_all(db, ctx.tenant_id)
    db.commit()
    _audit(request, ctx, "UPDATE", "risk_methodology", ctx.tenant_id,
           {"risks_reclassified": len(changed)})
    return risk_methodology_service.get_or_default(db, ctx.tenant_id)


# --- Catálogo: ameaças ---

@router.get("/threats", response_model=list[ThreatResponse])
def list_threats(db: db_dependency, ctx: view_dep, include_archived: bool = False):
    q = db.query(OrgThreat).filter(OrgThreat.tenant_id == ctx.tenant_id)
    if not include_archived:
        q = q.filter(OrgThreat.is_archived == False)  # noqa: E712
    return q.order_by(OrgThreat.code).all()


@router.post("/threats/adopt", response_model=AdoptResult)
def adopt_threats(request: Request, db: db_dependency, ctx: manage_dep):
    result = risk_catalog_service.adopt_threats(db, ctx.tenant_id)
    _audit(request, ctx, "ADOPT", "org_threat", ctx.tenant_id, result)
    return result


@router.post("/threats", response_model=ThreatResponse, status_code=status.HTTP_201_CREATED)
def create_threat(payload: ThreatCreate, request: Request, db: db_dependency, ctx: manage_dep):
    threat = risk_catalog_service.create_threat(db, ctx.tenant_id, ctx.principal.user.id, payload.model_dump())
    _audit(request, ctx, "CREATE", "org_threat", threat.id)
    return threat


@router.put("/threats/{threat_id}", response_model=ThreatResponse)
def update_threat(threat_id: uuid.UUID, payload: ThreatCreate, request: Request, db: db_dependency, ctx: manage_dep):
    threat = db.query(OrgThreat).filter_by(id=threat_id, tenant_id=ctx.tenant_id).first()
    if threat is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    for k, v in payload.model_dump().items():
        setattr(threat, k, v)
    db.commit()
    db.refresh(threat)
    _audit(request, ctx, "UPDATE", "org_threat", threat.id)
    return threat


@router.post("/threats/{threat_id}/archive", response_model=ThreatResponse)
def archive_threat(threat_id: uuid.UUID, payload: ArchiveRequest, request: Request, db: db_dependency, ctx: manage_dep):
    threat = db.query(OrgThreat).filter_by(id=threat_id, tenant_id=ctx.tenant_id).first()
    if threat is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    risk_catalog_service.archive_item(db, threat, payload.reason)
    _audit(request, ctx, "ARCHIVE", "org_threat", threat.id)
    return threat


@router.post("/threats/{threat_id}/assets", status_code=status.HTTP_201_CREATED)
def link_threat_asset(threat_id: uuid.UUID, payload: LinkAssetRequest, request: Request, db: db_dependency, ctx: manage_dep):
    threat = db.query(OrgThreat).filter_by(id=threat_id, tenant_id=ctx.tenant_id).first()
    if threat is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    risk_catalog_service.link_threat_asset(db, ctx.tenant_id, threat, payload.asset_item_id, ctx.principal.user.id)
    _audit(request, ctx, "LINK", "asset_threat_link", threat.id, {"asset_item_id": str(payload.asset_item_id)})
    return {"status": "linked"}


# --- Catálogo: vulnerabilidades ---

@router.get("/vulnerabilities", response_model=list[VulnerabilityResponse])
def list_vulnerabilities(db: db_dependency, ctx: view_dep, include_archived: bool = False):
    q = db.query(OrgVulnerability).filter(OrgVulnerability.tenant_id == ctx.tenant_id)
    if not include_archived:
        q = q.filter(OrgVulnerability.is_archived == False)  # noqa: E712
    return q.order_by(OrgVulnerability.code).all()


@router.post("/vulnerabilities/adopt", response_model=AdoptResult)
def adopt_vulnerabilities(request: Request, db: db_dependency, ctx: manage_dep):
    result = risk_catalog_service.adopt_vulnerabilities(db, ctx.tenant_id)
    _audit(request, ctx, "ADOPT", "org_vulnerability", ctx.tenant_id, result)
    return result


@router.post("/vulnerabilities", response_model=VulnerabilityResponse, status_code=status.HTTP_201_CREATED)
def create_vulnerability(payload: VulnerabilityCreate, request: Request, db: db_dependency, ctx: manage_dep):
    vuln = risk_catalog_service.create_vulnerability(db, ctx.tenant_id, ctx.principal.user.id, payload.model_dump())
    _audit(request, ctx, "CREATE", "org_vulnerability", vuln.id)
    return vuln


@router.post("/vulnerabilities/{vuln_id}/archive", response_model=VulnerabilityResponse)
def archive_vulnerability(vuln_id: uuid.UUID, payload: ArchiveRequest, request: Request, db: db_dependency, ctx: manage_dep):
    vuln = db.query(OrgVulnerability).filter_by(id=vuln_id, tenant_id=ctx.tenant_id).first()
    if vuln is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    risk_catalog_service.archive_item(db, vuln, payload.reason)
    _audit(request, ctx, "ARCHIVE", "org_vulnerability", vuln.id)
    return vuln


@router.post("/vulnerabilities/{vuln_id}/assets", status_code=status.HTTP_201_CREATED)
def link_vuln_asset(vuln_id: uuid.UUID, payload: LinkAssetRequest, request: Request, db: db_dependency, ctx: manage_dep):
    vuln = db.query(OrgVulnerability).filter_by(id=vuln_id, tenant_id=ctx.tenant_id).first()
    if vuln is None:
        from fastapi import HTTPException
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")
    risk_catalog_service.link_vulnerability_asset(db, ctx.tenant_id, vuln, payload.asset_item_id, ctx.principal.user.id)
    _audit(request, ctx, "LINK", "asset_vulnerability_link", vuln.id, {"asset_item_id": str(payload.asset_item_id)})
    return {"status": "linked"}


# --- Registro de risco (Fase 2) ---

@router.get("/risks", response_model=list[RiskResponse])
def list_risks(
    db: db_dependency, ctx: view_dep,
    q: str | None = None, status_filter: str | None = None, level: str | None = None,
    owner_user_id: uuid.UUID | None = None, asset_item_id: uuid.UUID | None = None,
    above_acceptance: bool | None = None, has_treatment: bool | None = None,
    include_archived: bool = False,
):
    filters = {
        "q": q, "level": level, "owner_user_id": owner_user_id, "asset_item_id": asset_item_id,
        "above_acceptance": above_acceptance, "include_archived": include_archived,
    }
    if status_filter:
        from wtnapp.settings import RiskStatus
        filters["status"] = RiskStatus(status_filter)
    risks = risk_service.list_risks(db, ctx, filters)
    if has_treatment is not None:
        risks = [r for r in risks if (r.treatment_option is not None) == has_treatment]
    return [_risk_to_response(db, ctx, r) for r in risks]


@router.post("/risks", response_model=RiskResponse, status_code=status.HTTP_201_CREATED)
def create_risk(payload: RiskCreate, request: Request, db: db_dependency, ctx: manage_dep):
    risk = risk_service.create_risk(db, ctx, payload.model_dump())
    _audit(request, ctx, "CREATE", "risk", risk.id)
    return _risk_to_response(db, ctx, risk)


@router.get("/risks/{risk_id}", response_model=RiskResponse)
def get_risk(risk_id: uuid.UUID, db: db_dependency, ctx: view_dep):
    return _risk_to_response(db, ctx, risk_service.get_risk(db, ctx, risk_id))


@router.put("/risks/{risk_id}", response_model=RiskResponse)
def evaluate_risk(risk_id: uuid.UUID, payload: RiskEvaluate, request: Request, db: db_dependency, ctx: manage_dep):
    risk = risk_service.evaluate_risk(db, ctx, risk_id, payload.model_dump(exclude_unset=True))
    _audit(request, ctx, "UPDATE", "risk", risk.id)
    return _risk_to_response(db, ctx, risk)


@router.post("/risks/{risk_id}/archive", response_model=RiskResponse)
def archive_risk(risk_id: uuid.UUID, payload: ArchiveRequest, request: Request, db: db_dependency, ctx: manage_dep):
    risk = risk_service.archive_risk(db, ctx, risk_id, payload.reason)
    _audit(request, ctx, "ARCHIVE", "risk", risk.id)
    return _risk_to_response(db, ctx, risk)


@router.get("/risks/{risk_id}/history", response_model=list[RiskEventResponse])
def risk_history(risk_id: uuid.UUID, db: db_dependency, ctx: view_dep):
    risk_service.get_risk(db, ctx, risk_id)
    return (
        db.query(RiskEvent)
        .filter_by(tenant_id=ctx.tenant_id, risk_id=risk_id)
        .order_by(RiskEvent.occurred_at.asc())
        .all()
    )


@router.get("/matrix", response_model=list[HeatmapCell])
def matrix(db: db_dependency, ctx: view_dep):
    return risk_metrics_service.heatmap(db, ctx.tenant_id)


@router.get("/dashboard")
def dashboard(db: db_dependency, ctx: view_dep):
    return risk_metrics_service.dashboard(db, ctx.tenant_id)


# --- Tratamento (Fase 3) ---

@router.put("/risks/{risk_id}/treatment", response_model=RiskResponse)
def set_treatment(risk_id: uuid.UUID, payload: TreatmentUpdate, request: Request, db: db_dependency, ctx: manage_dep):
    risk = risk_treatment_service.set_treatment(db, ctx, risk_id, payload.model_dump())
    _audit(request, ctx, "TREATMENT", "risk", risk.id)
    return _risk_to_response(db, ctx, risk)


@router.get("/risks/{risk_id}/controls", response_model=list[ControlResponse])
def list_controls(risk_id: uuid.UUID, db: db_dependency, ctx: view_dep):
    return risk_treatment_service.list_controls(db, ctx, risk_id)


@router.post("/risks/{risk_id}/controls", response_model=ControlResponse, status_code=status.HTTP_201_CREATED)
def add_control(risk_id: uuid.UUID, payload: ControlCreate, request: Request, db: db_dependency, ctx: manage_dep):
    control = risk_treatment_service.add_control(db, ctx, risk_id, payload.model_dump())
    _audit(request, ctx, "CONTROL_ADD", "risk_treatment_control", control.id, {"risk_id": str(risk_id)})
    return control


@router.delete("/risks/{risk_id}/controls/{control_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_control(risk_id: uuid.UUID, control_id: uuid.UUID, request: Request, db: db_dependency, ctx: manage_dep):
    risk_treatment_service.remove_control(db, ctx, risk_id, control_id)
    _audit(request, ctx, "CONTROL_REMOVE", "risk_treatment_control", control_id, {"risk_id": str(risk_id)})


@router.post("/risks/{risk_id}/accept", response_model=RiskResponse)
def accept_risk(risk_id: uuid.UUID, payload: AcceptRequest, request: Request, db: db_dependency, ctx: manage_dep):
    risk = risk_treatment_service.accept_risk(db, ctx, risk_id, payload.model_dump())
    _audit(request, ctx, "ACCEPT", "risk", risk.id)
    return _risk_to_response(db, ctx, risk)


@router.get("/soa-feed", response_model=list[SoaFeedItem])
def soa_feed(db: db_dependency, ctx: view_dep):
    return risk_treatment_service.soa_feed(db, ctx.tenant_id)


@router.get("/assets/{asset_id}/links")
def asset_links(asset_id: uuid.UUID, db: db_dependency, ctx: view_dep):
    links = risk_treatment_service.asset_links(db, ctx, asset_id)
    return {
        "threats": [ThreatResponse.model_validate(t) for t in links["threats"]],
        "vulnerabilities": [VulnerabilityResponse.model_validate(v) for v in links["vulnerabilities"]],
        "risks": [_risk_to_response(db, ctx, r) for r in links["risks"]],
        "controls": [ControlResponse.model_validate(c) for c in links["controls"]],
    }


# --- Plano de Tratamento ---

@router.get("/plan", response_model=PlanResponse)
def get_plan(db: db_dependency, ctx: view_dep):
    plan = risk_treatment_service.get_or_create_plan(db, ctx.tenant_id)
    return PlanResponse(id=plan.id, draft_status=plan.draft_status.value, current_version_id=plan.current_version_id)


@router.post("/plan/submit-review", response_model=PlanResponse)
def submit_plan(request: Request, db: db_dependency, ctx: manage_dep):
    plan = risk_treatment_service.submit_plan(db, ctx)
    _audit(request, ctx, "SUBMIT_REVIEW", "risk_plan", plan.id)
    return PlanResponse(id=plan.id, draft_status=plan.draft_status.value, current_version_id=plan.current_version_id)


@router.post("/plan/approve")
def approve_plan(payload: PlanApprove, request: Request, db: db_dependency, ctx: approve_dep):
    version = risk_treatment_service.approve_plan(db, ctx, payload.model_dump())
    _audit(request, ctx, "APPROVE", "risk_plan", version.document_id,
           {"version": version.version_number, "signed": payload.sign})
    return {"version_id": str(version.id), "version_number": version.version_number}


@router.get("/plan/versions")
def plan_versions(db: db_dependency, ctx: view_dep):
    versions = risk_treatment_service.list_plan_versions(db, ctx)
    return [
        {"id": str(v.id), "version_number": v.version_number, "status": v.status.value,
         "classification": v.classification.value if v.classification else None}
        for v in versions
    ]
