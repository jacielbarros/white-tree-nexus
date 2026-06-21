"""Gap Assessment router — matriz, itens, dashboard, lacunas, baseline."""

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem, GapAssessmentItemEvent
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.schemas.gap_assessment_schema import (
    AssessmentItemResponse,
    AssessmentItemUpdate,
    AssessmentResponse,
    BaselineApproveRequest,
    BaselineComparisonResponse,
    BaselineResponse,
    DashboardResponse,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.gap_metrics_service import compute_dashboard, list_gaps
from wtnapp.settings import Classification, DocStatus, DocType, GapStatus

router = APIRouter(prefix="/gap/assessment", tags=["gap-assessment"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_gap"))]
approve_dep = Annotated[OrgContext, Depends(require_permission("approve_gap_baseline"))]


def _get_assessment(db: Session, tenant_id: uuid.UUID) -> GapAssessment:
    assessment = db.query(GapAssessment).filter_by(tenant_id=tenant_id).first()
    if assessment is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Avaliação não encontrada. Adote o catálogo primeiro.")
    return assessment


@router.get("", response_model=AssessmentResponse)
def get_assessment(db: db_dep, ctx: view_dep):
    assessment = _get_assessment(db, ctx.tenant_id)
    items = (
        db.query(GapAssessmentItem)
        .filter(GapAssessmentItem.assessment_id == assessment.id)
        .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
        .order_by(GapCatalogItem.order)
        .all()
    )
    return AssessmentResponse(
        id=assessment.id,
        seed_version=None,
        draft_status=assessment.draft_status,
        current_version_id=assessment.current_version_id,
        items=[_item_response(db, i) for i in items],
    )


def _item_response(db: Session, item: GapAssessmentItem) -> AssessmentItemResponse:
    cat = db.get(GapCatalogItem, item.catalog_item_id)
    return AssessmentItemResponse(
        id=item.id,
        catalog_item_id=item.catalog_item_id,
        ref_code=cat.ref_code if cat else "",
        dimension=cat.dimension.value if cat else "",
        theme=cat.theme.value if cat and cat.theme else None,
        name=cat.name if cat else "",
        status=item.status,
        findings=item.findings,
        actions=item.actions,
        priority=item.priority,
        responsible=item.responsible,
        deadline=item.deadline,
        evidence_ref=item.evidence_ref,
        notes=item.notes,
        exclusion_justification=item.exclusion_justification,
        maturity_level=item.maturity_level,
        effort_estimate=item.effort_estimate,
        soa_ref=item.soa_ref,
    )


@router.put("/items/{item_id}", response_model=AssessmentItemResponse)
def update_assessment_item(
    item_id: uuid.UUID,
    body: AssessmentItemUpdate,
    db: db_dep,
    ctx: manage_dep,
    request: Request,
):
    item = scoped_query(db, GapAssessmentItem, ctx).filter(GapAssessmentItem.id == item_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado.")

    data = body.model_dump(exclude_unset=True)

    new_status = data.get("status", item.status)
    if new_status == GapStatus.not_applicable and not data.get("exclusion_justification") and not item.exclusion_justification:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "exclusion_justification é obrigatória quando status=not_applicable.",
        )

    # Grava eventos append-only para campos relevantes
    tracked_fields = {"status", "priority"}
    for field in tracked_fields:
        if field in data:
            old_val = getattr(item, field)
            new_val = data[field]
            old_str = old_val.value if hasattr(old_val, "value") else str(old_val) if old_val is not None else None
            new_str = new_val.value if hasattr(new_val, "value") else str(new_val) if new_val is not None else None
            if old_str != new_str:
                db.add(GapAssessmentItemEvent(
                    tenant_id=ctx.tenant_id,
                    item_id=item.id,
                    field=field,
                    old_value=old_str,
                    new_value=new_str,
                    actor_id=ctx.principal.user.id,
                ))

    for field, value in data.items():
        setattr(item, field, value)
    item.updated_by = ctx.principal.user.id

    db.commit()
    db.refresh(item)

    AuditService.log_from_request(
        request=request,
        operation="UPDATE",
        entity_type="gap_assessment_item",
        entity_id=str(item.id),
        details={"fields_updated": list(data.keys())},
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _item_response(db, item)


@router.get("/dashboard", response_model=DashboardResponse)
def get_dashboard(db: db_dep, ctx: view_dep):
    assessment = _get_assessment(db, ctx.tenant_id)
    return compute_dashboard(db, ctx.tenant_id, assessment.id)


@router.get("/gaps", response_model=list[AssessmentItemResponse])
def get_gaps(db: db_dep, ctx: view_dep, order_by: str = "priority"):
    assessment = _get_assessment(db, ctx.tenant_id)
    items = list_gaps(db, ctx.tenant_id, assessment.id, order_by)
    return [_item_response(db, i) for i in items]


@router.post("/submit-review")
def submit_review(db: db_dep, ctx: approve_dep, request: Request):
    assessment = _get_assessment(db, ctx.tenant_id)
    result = cds.submit_review(db, assessment)
    AuditService.log_from_request(
        request=request,
        operation="SUBMIT_REVIEW",
        entity_type="gap_assessment",
        entity_id=str(assessment.id),
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return {"status": result.draft_status}


@router.post("/approve", response_model=BaselineResponse)
def approve_baseline(
    body: BaselineApproveRequest,
    db: db_dep,
    ctx: approve_dep,
    request: Request,
):
    assessment = _get_assessment(db, ctx.tenant_id)

    dashboard = compute_dashboard(db, ctx.tenant_id, assessment.id)
    items = (
        db.query(GapAssessmentItem)
        .filter(GapAssessmentItem.assessment_id == assessment.id)
        .all()
    )
    item_snapshots = [
        {
            "id": str(i.id),
            "catalog_item_id": str(i.catalog_item_id),
            "status": i.status.value,
            "priority": i.priority.value if i.priority else None,
            "findings": i.findings,
            "actions": i.actions,
        }
        for i in items
    ]

    version = cds.approve_document(
        db=db,
        artifact=assessment,
        doc_type=DocType.gap_baseline,
        actor_id=ctx.principal.user.id,
        classification=Classification(body.classification),
        next_review_at=None,
        change_nature=body.change_nature,
        snapshot_factory=lambda: {
            "dashboard": dashboard,
            "items": item_snapshots,
        },
    )
    AuditService.log_from_request(
        request=request,
        operation="APPROVE_BASELINE",
        entity_type="gap_assessment",
        entity_id=str(assessment.id),
        details={"version_number": version.version_number},
        actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    return _baseline_response(version)


@router.get("/baselines", response_model=list[BaselineResponse])
def list_baselines(db: db_dep, ctx: view_dep):
    assessment = _get_assessment(db, ctx.tenant_id)
    versions = cds.list_versions(db, ctx.tenant_id, DocType.gap_baseline, assessment.id)
    return [_baseline_response(v) for v in versions]


@router.get("/baselines/compare", response_model=BaselineComparisonResponse)
def compare_baselines(
    db: db_dep,
    ctx: view_dep,
    from_id: uuid.UUID,
    to_id: uuid.UUID,
):
    assessment = _get_assessment(db, ctx.tenant_id)

    v_from = db.query(DocumentVersion).filter(
        DocumentVersion.id == from_id,
        DocumentVersion.tenant_id == ctx.tenant_id,
        DocumentVersion.document_id == assessment.id,
    ).first()
    v_to = db.query(DocumentVersion).filter(
        DocumentVersion.id == to_id,
        DocumentVersion.tenant_id == ctx.tenant_id,
        DocumentVersion.document_id == assessment.id,
    ).first()

    if v_from is None or v_to is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Baseline não encontrada.")

    overall_from = v_from.content_snapshot.get("dashboard", {}).get("overall_adherence")
    overall_to = v_to.content_snapshot.get("dashboard", {}).get("overall_adherence")
    overall_delta = None
    if overall_from is not None and overall_to is not None:
        overall_delta = round(overall_to - overall_from, 4)

    dim_from = v_from.content_snapshot.get("dashboard", {}).get("by_dimension", {})
    dim_to = v_to.content_snapshot.get("dashboard", {}).get("by_dimension", {})
    dim_delta = {}
    for dim in set(list(dim_from.keys()) + list(dim_to.keys())):
        f = dim_from.get(dim)
        t = dim_to.get(dim)
        dim_delta[dim] = round(t - f, 4) if f is not None and t is not None else None

    return BaselineComparisonResponse(
        from_baseline=_baseline_response(v_from),
        to_baseline=_baseline_response(v_to),
        overall_delta=overall_delta,
        by_dimension_delta=dim_delta,
    )


def _baseline_response(v: DocumentVersion) -> BaselineResponse:
    dashboard = v.content_snapshot.get("dashboard", {}) if v.content_snapshot else {}
    return BaselineResponse(
        id=v.id,
        version_number=v.version_number,
        status=v.status.value,
        classification=v.classification.value,
        emitted_at=v.created_at,
        overall_adherence=dashboard.get("overall_adherence"),
    )
