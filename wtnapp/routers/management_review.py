"""Análise Crítica pela Direção (cláusula 9.3) — Feature 015 / 5b.

Coleção (uma por reunião) como Documento Controlado: criar/editar → submeter → aprovar (assinatura
opcional) → versões/PDF. Gate duro de completude na aprovação.
"""

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.classification_access import require_classification_read
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.management_review_model import ManagementReview
from wtnapp.schemas.management_review_schema import (
    ReviewApproveRequest,
    ReviewDetail,
    ReviewReadiness,
    ReviewRequest,
    ReviewSummary,
    ReviewVersionSummary,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import management_review_export_service, management_review_service as svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DocType

router = APIRouter(prefix="/management-reviews", tags=["management-review"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_management_review"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_management_review"))]
approve_dep = Annotated[OrgContext, Depends(require_permission("approve_management_review"))]


def _audit(request: Request, ctx: OrgContext, operation: str, *, entity_id=None, details=None):
    AuditService.log_from_request(
        request=request, operation=operation, outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="management_review", entity_id=str(entity_id) if entity_id else None, details=details or {},
    )


def _detail(db: Session, ctx: OrgContext, r: ManagementReview) -> ReviewDetail:
    return ReviewDetail(
        id=r.id, title=r.title, review_date=r.review_date, draft_status=r.draft_status.value,
        current_version_id=r.current_version_id, inputs=dict(r.inputs or {}), outputs=dict(r.outputs or {}),
        readiness=ReviewReadiness(can_approve=svc.is_complete(r)),
    )


def _version_summary(v: DocumentVersion) -> ReviewVersionSummary:
    snap = v.content_snapshot or {}
    return ReviewVersionSummary(
        id=v.id, version_number=v.version_number, status=v.status.value if v.status else "",
        classification=v.classification, signed=bool(snap.get("signature")),
        approved_by=v.approved_by, approved_at=v.created_at,
    )


@router.get("", response_model=list[ReviewSummary])
def list_reviews(db: db_dep, ctx: view_dep):
    rows = scoped_query(db, ManagementReview, ctx).order_by(ManagementReview.review_date.desc()).all()
    return [ReviewSummary.model_validate(r) for r in rows]


@router.post("", response_model=ReviewSummary, status_code=status.HTTP_201_CREATED)
def create_review(request: Request, db: db_dep, ctx: manage_dep, body: ReviewRequest):
    review = svc.create_review(db, ctx, body)
    db.commit()
    db.refresh(review)
    _audit(request, ctx, "CREATE_MANAGEMENT_REVIEW", entity_id=review.id)
    return ReviewSummary.model_validate(review)


@router.get("/{review_id}", response_model=ReviewDetail)
def get_review(review_id: uuid.UUID, db: db_dep, ctx: view_dep):
    return _detail(db, ctx, svc.get_review(db, ctx, review_id))


@router.put("/{review_id}", response_model=ReviewSummary)
def update_review(review_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ReviewRequest):
    review = svc.get_review(db, ctx, review_id)
    svc.update_review(db, ctx, review, body)
    db.commit()
    db.refresh(review)
    _audit(request, ctx, "UPDATE_MANAGEMENT_REVIEW", entity_id=review.id)
    return ReviewSummary.model_validate(review)


@router.post("/{review_id}/submit-review", response_model=ReviewDetail)
def submit_review(review_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    review = svc.get_review(db, ctx, review_id)
    svc.submit_review(db, ctx, review)
    db.refresh(review)
    _audit(request, ctx, "SUBMIT_MANAGEMENT_REVIEW", entity_id=review.id)
    return _detail(db, ctx, review)


@router.post("/{review_id}/approve", response_model=ReviewVersionSummary, status_code=status.HTTP_201_CREATED)
def approve(review_id: uuid.UUID, request: Request, db: db_dep, ctx: approve_dep, body: ReviewApproveRequest = Body(default=ReviewApproveRequest())):
    review = svc.get_review(db, ctx, review_id)
    version = svc.approve(db, ctx, review, sign=body.sign, classification=body.classification, next_review_at=body.next_review_at, change_nature=body.change_nature)
    db.refresh(version)
    _audit(request, ctx, "APPROVE_MANAGEMENT_REVIEW", entity_id=review.id, details={"version_number": version.version_number, "signed": bool((version.content_snapshot or {}).get("signature"))})
    return _version_summary(version)


@router.get("/{review_id}/versions", response_model=list[ReviewVersionSummary])
def list_versions(review_id: uuid.UUID, db: db_dep, ctx: view_dep):
    review = svc.get_review(db, ctx, review_id)
    return [_version_summary(v) for v in cds.list_versions(db, ctx.tenant_id, DocType.management_review, review.id)]


@router.get("/{review_id}/versions/{version_id}/export")
def export_version(review_id: uuid.UUID, version_id: uuid.UUID, request: Request, db: db_dep, ctx: view_dep):
    review = svc.get_review(db, ctx, review_id)
    version = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.id == version_id,
            DocumentVersion.tenant_id == ctx.tenant_id,
            DocumentVersion.document_type == DocType.management_review,
            DocumentVersion.document_id == review.id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versao nao encontrada.")
    require_classification_read(db, ctx, version.classification)
    pdf = management_review_export_service.render_pdf(version)
    _audit(request, ctx, "EXPORT_MANAGEMENT_REVIEW", entity_id=version.id, details={"version_number": version.version_number})
    filename = quote(f"analise-critica-v{version.version_number}.pdf")
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})
