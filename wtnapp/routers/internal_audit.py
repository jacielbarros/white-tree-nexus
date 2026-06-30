"""Auditoria Interna (cláusula 9.2) — Feature 014, Fase 2.

Programas, auditorias (ciclo de vida), checklist (manual + import SoA/Gap) e constatações.
O relatório (Documento Controlado) é adicionado numa fatia posterior (US6).
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
from wtnapp.models.internal_audit_model import (
    InternalAudit,
    InternalAuditChecklistItem,
    InternalAuditFinding,
    InternalAuditProgram,
)
from wtnapp.schemas.evidence_schema import EvidenceLinkOut
from wtnapp.schemas.internal_audit_schema import (
    AuditDashboard,
    AuditDetail,
    AuditReadiness,
    AuditRequest,
    AuditSummary,
    ChecklistImportRequest,
    ChecklistItemRequest,
    ChecklistItemSummary,
    ChecklistItemUpdate,
    FindingRequest,
    FindingSummary,
    ProgramRequest,
    ProgramSummary,
    ReportApproveRequest,
    ReportVersionSummary,
    TransitionRequest,
)
from wtnapp.services import audit_metrics_service
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import internal_audit_export_service, internal_audit_report_service
from wtnapp.services import internal_audit_service as svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditFindingStatus, AuditOutcome, DocType, InternalAuditStatus

router = APIRouter(prefix="/internal-audit", tags=["internal-audit"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_internal_audit"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_internal_audit"))]
approve_dep = Annotated[OrgContext, Depends(require_permission("approve_audit_report"))]


def _report_version_summary(v: DocumentVersion) -> ReportVersionSummary:
    snap = v.content_snapshot or {}
    return ReportVersionSummary(
        id=v.id, version_number=v.version_number,
        status=v.status.value if v.status else "", classification=v.classification,
        signed=bool(snap.get("signature")), approved_by=v.approved_by, approved_at=v.created_at,
    )


def _audit(request: Request, ctx: OrgContext, operation: str, *, entity_id=None, outcome=AuditOutcome.success, details=None):
    AuditService.log_from_request(
        request=request, operation=operation, outcome=outcome,
        actor_user_id=ctx.principal.user.id, actor_role=ctx.role.value, tenant_id=ctx.tenant_id,
        entity_type="internal_audit", entity_id=str(entity_id) if entity_id else None, details=details or {},
    )


def _finding_summary(db: Session, ctx: OrgContext, f: InternalAuditFinding) -> FindingSummary:
    links = svc.finding_evidence_links(db, ctx, f.id)
    return FindingSummary(
        id=f.id, audit_id=f.audit_id, finding_type=f.finding_type, title=f.title, description=f.description,
        checklist_item_id=f.checklist_item_id, target_type=f.target_type, target_id=f.target_id,
        promotable=f.promotable, nonconformity_ref=f.nonconformity_ref, status=f.status,
        evidence_links=[EvidenceLinkOut(id=l.id, target_type=l.target_type, target_id=l.target_id, active=l.active) for l in links],
    )


def _detail(db: Session, ctx: OrgContext, audit: InternalAudit) -> AuditDetail:
    return AuditDetail(
        id=audit.id, program_id=audit.program_id, code=audit.code, title=audit.title, status=audit.status,
        auditor_member_id=audit.auditor_member_id, period_start=audit.period_start, period_end=audit.period_end,
        current_version_id=audit.current_version_id, draft_status=audit.draft_status,
        scope=audit.scope, criteria=audit.criteria,
        readiness=AuditReadiness(
            can_approve_report=svc.can_approve_report(db, ctx, audit),
            pending_items=svc.pending_items(db, ctx, audit.id),
            findings_count=svc.findings_count(db, ctx, audit.id),
        ),
    )


# ───────────────────────────── Dashboard do módulo ─────────────────────────────

@router.get("/dashboard", response_model=AuditDashboard)
def dashboard(db: db_dep, ctx: view_dep):
    return AuditDashboard(**audit_metrics_service.build_metrics(db, ctx))


# ───────────────────────────── Programas ─────────────────────────────

@router.get("/programs", response_model=list[ProgramSummary])
def list_programs(db: db_dep, ctx: view_dep):
    return scoped_query(db, InternalAuditProgram, ctx).order_by(InternalAuditProgram.created_at.desc()).all()


@router.post("/programs", response_model=ProgramSummary, status_code=status.HTTP_201_CREATED)
def create_program(request: Request, db: db_dep, ctx: manage_dep, body: ProgramRequest):
    program = InternalAuditProgram(
        tenant_id=ctx.tenant_id, name=body.name, objective=body.objective,
        period_start=body.period_start, period_end=body.period_end, created_by=ctx.principal.user.id,
    )
    db.add(program)
    svc.log_event(db, ctx=ctx, entity_type="program", event_type="created", entity_id=program.id)
    db.commit()
    db.refresh(program)
    _audit(request, ctx, "CREATE_AUDIT_PROGRAM", entity_id=program.id)
    return program


# ───────────────────────────── Auditorias ─────────────────────────────

@router.get("/audits", response_model=list[AuditSummary])
def list_audits(db: db_dep, ctx: view_dep, program_id: uuid.UUID | None = None, status_filter: InternalAuditStatus | None = None):
    query = scoped_query(db, InternalAudit, ctx)
    if program_id is not None:
        query = query.filter(InternalAudit.program_id == program_id)
    if status_filter is not None:
        query = query.filter(InternalAudit.status == status_filter)
    return query.order_by(InternalAudit.created_at.desc()).all()


@router.post("/audits", response_model=AuditSummary, status_code=status.HTTP_201_CREATED)
def create_audit(request: Request, db: db_dep, ctx: manage_dep, body: AuditRequest):
    audit = svc.create_audit(
        db, ctx, program_id=body.program_id, title=body.title, scope=body.scope, criteria=body.criteria,
        auditor_member_id=body.auditor_member_id, period_start=body.period_start, period_end=body.period_end,
    )
    db.commit()
    db.refresh(audit)
    _audit(request, ctx, "CREATE_INTERNAL_AUDIT", entity_id=audit.id, details={"code": audit.code})
    return audit


@router.get("/audits/{audit_id}", response_model=AuditDetail)
def get_audit_detail(audit_id: uuid.UUID, db: db_dep, ctx: view_dep):
    return _detail(db, ctx, svc.get_audit(db, ctx, audit_id))


@router.put("/audits/{audit_id}", response_model=AuditSummary)
def update_audit(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: AuditRequest):
    audit = svc.get_audit(db, ctx, audit_id)
    svc.get_program(db, ctx, body.program_id)
    svc._validate_member(db, ctx, body.auditor_member_id)
    audit.program_id = body.program_id
    audit.title = body.title
    audit.scope = body.scope
    audit.criteria = body.criteria
    audit.auditor_member_id = body.auditor_member_id
    audit.period_start = body.period_start
    audit.period_end = body.period_end
    svc.log_event(db, ctx=ctx, entity_type="audit", event_type="updated", audit_id=audit.id, entity_id=audit.id)
    db.commit()
    db.refresh(audit)
    _audit(request, ctx, "UPDATE_INTERNAL_AUDIT", entity_id=audit.id)
    return audit


@router.post("/audits/{audit_id}/transition", response_model=AuditSummary)
def transition(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: TransitionRequest):
    audit = svc.get_audit(db, ctx, audit_id)
    svc.transition_audit(db, ctx, audit, body.action)
    db.commit()
    db.refresh(audit)
    _audit(request, ctx, "TRANSITION_INTERNAL_AUDIT", entity_id=audit.id, details={"action": body.action, "status": audit.status.value})
    return audit


# ───────────────────────────── Checklist ─────────────────────────────

@router.get("/audits/{audit_id}/checklist", response_model=list[ChecklistItemSummary])
def list_checklist(audit_id: uuid.UUID, db: db_dep, ctx: view_dep):
    svc.get_audit(db, ctx, audit_id)
    return (
        scoped_query(db, InternalAuditChecklistItem, ctx)
        .filter(InternalAuditChecklistItem.audit_id == audit_id)
        .order_by(InternalAuditChecklistItem.order_index.asc())
        .all()
    )


@router.post("/audits/{audit_id}/checklist", response_model=ChecklistItemSummary, status_code=status.HTTP_201_CREATED)
def add_checklist(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ChecklistItemRequest):
    audit = svc.get_audit(db, ctx, audit_id)
    item = svc.add_checklist_item(db, ctx, audit, body)
    db.commit()
    db.refresh(item)
    _audit(request, ctx, "ADD_CHECKLIST_ITEM", entity_id=item.id)
    return item


@router.put("/audits/{audit_id}/checklist/{item_id}", response_model=ChecklistItemSummary)
def update_checklist(audit_id: uuid.UUID, item_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ChecklistItemUpdate):
    svc.get_audit(db, ctx, audit_id)
    item = svc.get_checklist_item(db, ctx, audit_id, item_id)
    svc.update_checklist_item(db, ctx, item, result=body.result, note=body.note)
    db.commit()
    db.refresh(item)
    _audit(request, ctx, "UPDATE_CHECKLIST_ITEM", entity_id=item.id, details={"result": item.result.value})
    return item


@router.post("/audits/{audit_id}/checklist/import", response_model=list[ChecklistItemSummary], status_code=status.HTTP_201_CREATED)
def import_checklist(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: ChecklistImportRequest):
    audit = svc.get_audit(db, ctx, audit_id)
    items = svc.import_checklist(db, ctx, audit, body.source, body.only_applicable)
    db.commit()
    for item in items:
        db.refresh(item)
    _audit(request, ctx, "IMPORT_CHECKLIST", entity_id=audit.id, details={"source": body.source, "count": len(items)})
    return items


# ───────────────────────────── Constatações ─────────────────────────────

@router.get("/audits/{audit_id}/findings", response_model=list[FindingSummary])
def list_findings(audit_id: uuid.UUID, db: db_dep, ctx: view_dep):
    svc.get_audit(db, ctx, audit_id)
    rows = (
        scoped_query(db, InternalAuditFinding, ctx)
        .filter(InternalAuditFinding.audit_id == audit_id, InternalAuditFinding.status == AuditFindingStatus.active)
        .order_by(InternalAuditFinding.created_at.asc())
        .all()
    )
    return [_finding_summary(db, ctx, f) for f in rows]


@router.post("/audits/{audit_id}/findings", response_model=FindingSummary, status_code=status.HTTP_201_CREATED)
def add_finding(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: FindingRequest):
    audit = svc.get_audit(db, ctx, audit_id)
    finding = svc.create_finding(db, ctx, audit, body)
    db.commit()
    db.refresh(finding)
    _audit(request, ctx, "CREATE_AUDIT_FINDING", entity_id=finding.id, details={"type": finding.finding_type.value, "promotable": finding.promotable})
    return _finding_summary(db, ctx, finding)


@router.put("/findings/{finding_id}", response_model=FindingSummary)
def edit_finding(finding_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: FindingRequest):
    finding = svc.get_finding(db, ctx, finding_id)
    svc.update_finding(db, ctx, finding, body)
    db.commit()
    db.refresh(finding)
    _audit(request, ctx, "UPDATE_AUDIT_FINDING", entity_id=finding.id)
    return _finding_summary(db, ctx, finding)


@router.delete("/findings/{finding_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_finding(finding_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    finding = svc.get_finding(db, ctx, finding_id)
    svc.inactivate_finding(db, ctx, finding)
    db.commit()
    _audit(request, ctx, "INACTIVATE_AUDIT_FINDING", entity_id=finding.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ───────────────────────────── Relatório (Documento Controlado) ─────────────────────────────

@router.post("/audits/{audit_id}/report/submit-review", response_model=AuditDetail)
def submit_report_review(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    audit = svc.get_audit(db, ctx, audit_id)
    internal_audit_report_service.submit_review(db, ctx, audit)
    db.commit()
    db.refresh(audit)
    _audit(request, ctx, "SUBMIT_AUDIT_REPORT_REVIEW", entity_id=audit.id)
    return _detail(db, ctx, audit)


@router.post("/audits/{audit_id}/report/approve", response_model=ReportVersionSummary, status_code=status.HTTP_201_CREATED)
def approve_report(audit_id: uuid.UUID, request: Request, db: db_dep, ctx: approve_dep, body: ReportApproveRequest = Body(default=ReportApproveRequest())):
    audit = svc.get_audit(db, ctx, audit_id)
    version = internal_audit_report_service.approve(
        db, ctx, audit, sign=body.sign, classification=body.classification,
        next_review_at=body.next_review_at, change_nature=body.change_nature,
    )
    db.commit()
    db.refresh(version)
    _audit(request, ctx, "APPROVE_AUDIT_REPORT", entity_id=audit.id, details={"version_number": version.version_number, "signed": bool((version.content_snapshot or {}).get("signature"))})
    return _report_version_summary(version)


@router.get("/audits/{audit_id}/report/versions", response_model=list[ReportVersionSummary])
def list_report_versions(audit_id: uuid.UUID, db: db_dep, ctx: view_dep):
    audit = svc.get_audit(db, ctx, audit_id)
    versions = cds.list_versions(db, ctx.tenant_id, DocType.internal_audit_report, audit.id)
    return [_report_version_summary(v) for v in versions]


@router.get("/audits/{audit_id}/report/versions/{version_id}/export")
def export_report(audit_id: uuid.UUID, version_id: uuid.UUID, request: Request, db: db_dep, ctx: view_dep):
    audit = svc.get_audit(db, ctx, audit_id)
    version = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.id == version_id,
            DocumentVersion.tenant_id == ctx.tenant_id,
            DocumentVersion.document_type == DocType.internal_audit_report,
            DocumentVersion.document_id == audit.id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versao nao encontrada.")
    require_classification_read(db, ctx, version.classification)
    pdf = internal_audit_export_service.render_pdf(version)
    _audit(request, ctx, "EXPORT_AUDIT_REPORT", entity_id=version.id, details={"version_number": version.version_number})
    filename = quote(f"relatorio-auditoria-{audit.code}-v{version.version_number}.pdf")
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})
