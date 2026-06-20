"""Visao consolidada, sugestoes e politica de classificacao."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.routers.stakeholders import derive_strategy
from wtnapp.schemas.classification_schema import ClassificationPolicyPayload, ClassificationPolicyResponse
from wtnapp.schemas.suggestion_schema import SuggestionAccept, SuggestionResponse
from wtnapp.services import suggestion_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome

router = APIRouter(prefix="/context", tags=["context"])


@router.get("/classification-policy", response_model=ClassificationPolicyResponse)
def get_policy(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    policy = scoped_query(db, ClassificationAccessPolicy, ctx).first()
    if policy is None:
        return ClassificationPolicyResponse(rules={})
    return policy


@router.put("/classification-policy", response_model=ClassificationPolicyResponse)
def put_policy(
    payload: ClassificationPolicyPayload,
    request: Request,
    ctx: OrgContext = Depends(require_permission("approve_context_document")),
    db: Session = Depends(get_db),
):
    policy = scoped_query(db, ClassificationAccessPolicy, ctx).first()
    if policy is None:
        policy = ClassificationAccessPolicy(tenant_id=ctx.tenant_id)
        db.add(policy)
    policy.rules = payload.rules
    db.commit()
    db.refresh(policy)
    AuditService.log_from_request(
        request=request, operation="CLASSIFICATION_POLICY_SAVE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="classification_access_policy", entity_id=policy.id,
    )
    return policy


@router.get("/overview")
def overview(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    from wtnapp.routers.context_analysis import _get_or_create as get_analysis, _serialize as ser_analysis
    from wtnapp.routers.scope import _get_or_create as get_scope, _serialize as ser_scope
    from wtnapp.routers.stakeholders import _get_or_create as get_stakeholders, _serialize as ser_stakeholders

    return {
        "analysis": ser_analysis(db, get_analysis(db, ctx)).model_dump(mode="json"),
        "stakeholders": ser_stakeholders(db, get_stakeholders(db, ctx)).model_dump(mode="json"),
        "scope": ser_scope(db, get_scope(db, ctx)).model_dump(mode="json"),
    }


@router.get("/suggestions", response_model=list[SuggestionResponse])
def suggestions(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    diagnostic = scoped_query(db, Diagnostic, ctx).first()
    return suggestion_service.build_suggestions(diagnostic)


@router.post("/suggestions/accept")
def accept_suggestion(
    payload: SuggestionAccept,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    diagnostic = scoped_query(db, Diagnostic, ctx).first()
    match = next((s for s in suggestion_service.build_suggestions(diagnostic) if s["id"] == payload.suggestion_id), None)
    if match is None:
        raise HTTPException(404, "Sugestao nao encontrada.")
    if match["target"] != "stakeholder":
        raise HTTPException(422, "Tipo de sugestao nao suportado.")

    from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement

    item = scoped_query(db, StakeholderMap, ctx).first()
    if item is None:
        item = StakeholderMap(tenant_id=ctx.tenant_id)
        db.add(item)
        db.flush()
    data = match["payload"]
    stakeholder = Stakeholder(
        tenant_id=ctx.tenant_id,
        map_id=item.id,
        name=data["name"],
        type=data["type"],
        power=data["power"],
        interest=data["interest"],
        strategy=derive_strategy(data["power"], data["interest"]),
    )
    db.add(stakeholder)
    db.flush()
    for req in data.get("requirements", []):
        db.add(StakeholderRequirement(tenant_id=ctx.tenant_id, stakeholder_id=stakeholder.id, **req))
    db.commit()
    AuditService.log_from_request(
        request=request, operation="SUGGESTION_ACCEPT", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="suggestion", entity_id=payload.suggestion_id,
    )
    return {"created_id": str(stakeholder.id), "target": match["target"]}
