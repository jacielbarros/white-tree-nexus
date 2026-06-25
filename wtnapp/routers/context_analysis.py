"""Analise de Contexto (4.1)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.classification_access import require_classification_read
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.context_analysis_model import ContextAnalysis, ContextIssue
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.schemas.context_schema import (
    ContextAnalysisResponse,
    ContextAnalysisUpdate,
    ContextIssueCreate,
    ContextIssueResponse,
    ContextIssueUpdate,
    DocumentApproval,
    DocumentVersionResponse,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DocType, IssueFramework, IssueNature, IssueOrigin

router = APIRouter(prefix="/context/analysis", tags=["context"])
_NOT_FOUND = HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


def _get_or_create(db: Session, ctx: OrgContext) -> ContextAnalysis:
    analysis = scoped_query(db, ContextAnalysis, ctx).first()
    if analysis is None:
        analysis = ContextAnalysis(tenant_id=ctx.tenant_id)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
    return analysis


def _serialize(db: Session, analysis: ContextAnalysis) -> ContextAnalysisResponse:
    issues = db.query(ContextIssue).filter(ContextIssue.tenant_id == analysis.tenant_id, ContextIssue.analysis_id == analysis.id).all()
    current = db.get(DocumentVersion, analysis.current_version_id) if analysis.current_version_id else None
    return ContextAnalysisResponse(
        id=analysis.id,
        intended_outcomes=analysis.intended_outcomes,
        methodology=analysis.methodology,
        draft_status=analysis.draft_status,
        current_version_id=analysis.current_version_id,
        issues=issues,
        review_overdue=cds.review_overdue(current),
    )


def _snapshot(db: Session, analysis: ContextAnalysis) -> dict:
    return _serialize(db, analysis).model_dump(mode="json")


def _validate_issue(payload: ContextIssueCreate | ContextIssueUpdate) -> None:
    origin = getattr(payload, "origin", None)
    framework = getattr(payload, "framework", None)
    nature = getattr(payload, "nature", None) or IssueNature.contextual
    if framework == IssueFramework.pestel and origin != IssueOrigin.external:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "PESTEL deve representar questoes externas.")
    if framework == IssueFramework.pestel and nature in {IssueNature.strength, IssueNature.weakness}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Forcas e fraquezas devem ser internas.")
    if framework == IssueFramework.swot and nature in {IssueNature.strength, IssueNature.weakness} and origin != IssueOrigin.internal:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Forcas e fraquezas devem usar origem interna.")
    if framework == IssueFramework.swot and nature in {IssueNature.opportunity, IssueNature.threat} and origin != IssueOrigin.external:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Oportunidades e ameacas devem usar origem externa.")
    if framework == IssueFramework.swot and origin == IssueOrigin.external and nature not in {IssueNature.opportunity, IssueNature.threat}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "SWOT externo deve ser classificado como oportunidade ou ameaca.")


@router.get("", response_model=ContextAnalysisResponse)
def get_analysis(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    analysis = _get_or_create(db, ctx)
    current = db.get(DocumentVersion, analysis.current_version_id) if analysis.current_version_id else None
    require_classification_read(db, ctx, current.classification if current else None)
    return _serialize(db, analysis)


@router.put("", response_model=ContextAnalysisResponse)
def update_analysis(
    payload: ContextAnalysisUpdate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    analysis = _get_or_create(db, ctx)
    analysis.intended_outcomes = payload.intended_outcomes
    analysis.methodology = payload.methodology
    db.commit()
    db.refresh(analysis)
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ANALYSIS_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="context_analysis", entity_id=analysis.id,
    )
    return _serialize(db, analysis)


@router.post("/issues", status_code=status.HTTP_201_CREATED, response_model=ContextIssueResponse)
def create_issue(
    payload: ContextIssueCreate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    _validate_issue(payload)
    analysis = _get_or_create(db, ctx)
    issue = ContextIssue(tenant_id=ctx.tenant_id, analysis_id=analysis.id, **payload.model_dump())
    db.add(issue)
    db.commit()
    db.refresh(issue)
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ISSUE_CREATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="context_issue", entity_id=issue.id,
    )
    return issue


@router.patch("/issues/{issue_id}", response_model=ContextIssueResponse)
def update_issue(
    issue_id: uuid.UUID,
    payload: ContextIssueUpdate,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    issue = scoped_query(db, ContextIssue, ctx).filter(ContextIssue.id == issue_id).first()
    if issue is None:
        raise _NOT_FOUND
    data = payload.model_dump(exclude_unset=True)
    if "origin" not in data:
        data["origin"] = issue.origin
    if "framework" not in data:
        data["framework"] = issue.framework
    _validate_issue(ContextIssueUpdate(**data))
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)
    db.commit()
    db.refresh(issue)
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ISSUE_UPDATE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="context_issue", entity_id=issue.id,
    )
    return issue


@router.delete("/issues/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue(
    issue_id: uuid.UUID,
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    issue = scoped_query(db, ContextIssue, ctx).filter(ContextIssue.id == issue_id).first()
    if issue is None:
        raise _NOT_FOUND
    db.delete(issue)
    db.commit()
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ISSUE_DELETE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="context_issue", entity_id=issue_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/submit-review", response_model=ContextAnalysisResponse)
def submit_review(
    request: Request,
    ctx: OrgContext = Depends(require_permission("manage_context")),
    db: Session = Depends(get_db),
):
    analysis = cds.submit_review(db, _get_or_create(db, ctx))
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ANALYSIS_SUBMIT_REVIEW", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="context_analysis", entity_id=analysis.id,
    )
    return _serialize(db, analysis)


@router.post("/approve", status_code=status.HTTP_201_CREATED, response_model=DocumentVersionResponse)
def approve(
    payload: DocumentApproval,
    request: Request,
    ctx: OrgContext = Depends(require_permission("approve_context_document")),
    db: Session = Depends(get_db),
):
    analysis = _get_or_create(db, ctx)
    version = cds.approve_document(
        db=db, artifact=analysis, doc_type=DocType.context_analysis, actor_id=ctx.principal.user.id,
        classification=payload.classification, next_review_at=payload.next_review_at,
        change_nature=payload.change_nature, snapshot_factory=lambda: _snapshot(db, analysis),
    )
    AuditService.log_from_request(
        request=request, operation="CONTEXT_ANALYSIS_APPROVE", outcome=AuditOutcome.success,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="document_version", entity_id=version.id,
    )
    return version


@router.get("/versions", response_model=list[DocumentVersionResponse])
def versions(ctx: OrgContext = Depends(require_permission("view_context")), db: Session = Depends(get_db)):
    analysis = _get_or_create(db, ctx)
    return cds.list_versions(db, ctx.tenant_id, DocType.context_analysis, analysis.id)
