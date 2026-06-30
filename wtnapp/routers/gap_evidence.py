"""Gap Analysis evidence attachments — superfície de compatibilidade da Feature 008.

A partir da Feature 014 as evidências do Gap vivem no **repositório transversal unificado**
(`evidence`/`evidence_version`/`evidence_link`/`evidence_event`). Este router preserva os mesmos
paths, DTOs e permissões (`view_gap`/`manage_gap`) do 008, delegando o armazenamento ao store
unificado via vínculo `target_type=gap_item`.
"""

import uuid
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import has_permission, require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink, EvidenceVersion
from wtnapp.models.gap_assessment_model import GapAssessmentItem
from wtnapp.schemas.gap_evidence_schema import (
    GapEvidenceEventSummary,
    GapEvidenceHistory,
    GapEvidenceInactivateRequest,
    GapEvidenceSummary,
    GapEvidenceVersionSummary,
)
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, Classification, EvidenceEventType, EvidenceStatus, SgsiArtifactType
from wtnapp.utils.evidence_storage import (
    EvidenceStorageError,
    EvidenceStorageUnavailable,
    read_bytes,
    store_upload_file,
)

router = APIRouter(prefix="/gap/assessment/items/{item_id}/evidences", tags=["gap-evidence"])

db_dependency = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_gap"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_gap"))]

_TARGET = SgsiArtifactType.gap_item


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _audit_access_denied(request: Request | None, ctx: OrgContext, *, resource: str, target_id: uuid.UUID) -> None:
    if request is None:
        return
    AuditService.log_from_request(
        request=request,
        operation="EVIDENCE_ACCESS_DENIED",
        outcome=AuditOutcome.denied,
        actor_user_id=ctx.principal.user.id,
        actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id,
        entity_type=resource,
        entity_id=str(target_id),
        details={"reason": "not_found_or_not_in_tenant"},
    )


def _get_item(db: Session, ctx: OrgContext, item_id: uuid.UUID, request: Request | None = None) -> GapAssessmentItem:
    item = scoped_query(db, GapAssessmentItem, ctx).filter(GapAssessmentItem.id == item_id).first()
    if item is None:
        _audit_access_denied(request, ctx, resource="gap_assessment_item", target_id=item_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return item


def _linked_evidence_ids(db: Session, ctx: OrgContext, item_id: uuid.UUID) -> set[uuid.UUID]:
    rows = (
        scoped_query(db, EvidenceLink, ctx)
        .filter(
            EvidenceLink.target_type == _TARGET,
            EvidenceLink.target_id == item_id,
            EvidenceLink.active.is_(True),
        )
        .all()
    )
    return {row.evidence_id for row in rows}


def _get_evidence(
    db: Session,
    ctx: OrgContext,
    item_id: uuid.UUID,
    evidence_id: uuid.UUID,
    *,
    include_inactive: bool = False,
    request: Request | None = None,
) -> Evidence:
    if evidence_id not in _linked_evidence_ids(db, ctx, item_id):
        _audit_access_denied(request, ctx, resource="gap_evidence", target_id=evidence_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    query = scoped_query(db, Evidence, ctx).filter(Evidence.id == evidence_id)
    if not include_inactive:
        query = query.filter(Evidence.status == EvidenceStatus.active)
    evidence = query.first()
    if evidence is None:
        _audit_access_denied(request, ctx, resource="gap_evidence", target_id=evidence_id)
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return evidence


def _current_version(db: Session, evidence: Evidence) -> EvidenceVersion:
    if evidence.current_version_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evidencia sem versao corrente.")
    version = db.get(EvidenceVersion, evidence.current_version_id)
    if version is None or version.tenant_id != evidence.tenant_id or version.evidence_id != evidence.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evidencia sem versao corrente.")
    return version


def _can_download(ctx: OrgContext, classification: Classification) -> bool:
    if classification in {Classification.publico, Classification.uso_interno}:
        return has_permission(ctx.role, "view_gap")
    return has_permission(ctx.role, "manage_gap")


def _summary(evidence: Evidence, version: EvidenceVersion, item_id: uuid.UUID, ctx: OrgContext) -> GapEvidenceSummary:
    return GapEvidenceSummary(
        id=evidence.id,
        assessment_item_id=item_id,
        title=evidence.title,
        description=evidence.description,
        classification=evidence.classification,
        status=evidence.status.value,
        current_version_id=version.id,
        file_name=version.original_filename,
        mime_type=version.mime_type,
        extension=version.extension,
        size_bytes=version.size_bytes,
        content_hash=version.content_hash,
        hash_algorithm=version.hash_algorithm,
        uploaded_by=version.uploaded_by,
        uploaded_at=version.uploaded_at,
        created_at=evidence.created_at,
        can_download=_can_download(ctx, evidence.classification),
    )


def _version_summary(version: EvidenceVersion, evidence: Evidence) -> GapEvidenceVersionSummary:
    return GapEvidenceVersionSummary(
        id=version.id,
        version_number=version.version_number,
        classification=version.classification,
        file_name=version.original_filename,
        mime_type=version.mime_type,
        extension=version.extension,
        size_bytes=version.size_bytes,
        content_hash=version.content_hash,
        hash_algorithm=version.hash_algorithm,
        uploaded_by=version.uploaded_by,
        uploaded_at=version.uploaded_at,
        is_current=evidence.current_version_id == version.id,
    )


def _event_summary(event: EvidenceEvent) -> GapEvidenceEventSummary:
    return GapEvidenceEventSummary(
        id=event.id,
        event_type=event.event_type,
        outcome=event.outcome,
        actor_id=event.actor_id,
        occurred_at=event.occurred_at,
        details=event.details,
    )


def _safe_title(title: str | None, filename: str) -> str:
    value = (title or filename).strip()
    return value[:255] or filename[:255]


def _safe_description(description: str | None) -> str | None:
    value = (description or "").strip()
    return value[:1000] or None


def _log_event(
    db: Session,
    *,
    ctx: OrgContext,
    event_type: EvidenceEventType,
    outcome: AuditOutcome = AuditOutcome.success,
    evidence_id: uuid.UUID | None = None,
    version_id: uuid.UUID | None = None,
    link_id: uuid.UUID | None = None,
    item_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        EvidenceEvent(
            tenant_id=ctx.tenant_id,
            evidence_id=evidence_id,
            version_id=version_id,
            link_id=link_id,
            target_type=_TARGET if item_id is not None else None,
            target_id=item_id,
            event_type=event_type.value,
            outcome=outcome.value,
            actor_id=ctx.principal.user.id,
            details=details or {},
        )
    )


def _audit(
    request: Request,
    *,
    ctx: OrgContext,
    operation: str,
    outcome: AuditOutcome = AuditOutcome.success,
    evidence_id: uuid.UUID | None = None,
    details: dict | None = None,
) -> None:
    AuditService.log_from_request(
        request=request,
        operation=operation,
        outcome=outcome,
        actor_user_id=ctx.principal.user.id,
        actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id,
        entity_type="gap_evidence",
        entity_id=str(evidence_id) if evidence_id else None,
        details=details or {},
    )


def _storage_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EvidenceStorageError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Storage de evidencias indisponivel.")


@router.get("", response_model=list[GapEvidenceSummary])
def list_evidences(item_id: uuid.UUID, request: Request, db: db_dependency, ctx: view_dep, include_history: bool = False):
    _get_item(db, ctx, item_id, request)
    if include_history and not has_permission(ctx.role, "manage_gap"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")
    evidence_ids = _linked_evidence_ids(db, ctx, item_id)
    if not evidence_ids:
        return []
    query = scoped_query(db, Evidence, ctx).filter(Evidence.id.in_(evidence_ids))
    if not include_history:
        query = query.filter(Evidence.status == EvidenceStatus.active)
    evidences = query.order_by(Evidence.created_at.desc()).all()
    return [_summary(e, _current_version(db, e), item_id, ctx) for e in evidences]


@router.post("", response_model=GapEvidenceSummary, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    item_id: uuid.UUID,
    request: Request,
    db: db_dependency,
    ctx: manage_dep,
    file: UploadFile = File(...),
    classification: Classification = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
):
    item = _get_item(db, ctx, item_id, request)
    evidence_id = uuid.uuid4()
    version_id = uuid.uuid4()
    try:
        stored = await store_upload_file(upload=file, tenant_id=ctx.tenant_id, evidence_id=evidence_id, version_id=version_id)
    except (EvidenceStorageError, EvidenceStorageUnavailable) as exc:
        _audit(request, ctx=ctx, operation="UPLOAD_EVIDENCE_DENIED", outcome=AuditOutcome.denied, details={"reason": type(exc).__name__})
        raise _storage_http_error(exc)

    evidence = Evidence(
        id=evidence_id,
        tenant_id=ctx.tenant_id,
        title=_safe_title(title, stored.original_filename),
        description=_safe_description(description),
        classification=classification,
        status=EvidenceStatus.active,
        created_by=ctx.principal.user.id,
    )
    db.add(evidence)
    db.flush()
    version = EvidenceVersion(
        id=version_id,
        tenant_id=ctx.tenant_id,
        evidence_id=evidence.id,
        version_number=1,
        classification=classification,
        original_filename=stored.original_filename,
        storage_key=stored.storage_key,
        content_hash=stored.content_hash,
        hash_algorithm=stored.hash_algorithm,
        encrypted=stored.encrypted,
        encryption_scheme=stored.encryption_scheme,
        size_bytes=stored.size_bytes,
        mime_type=stored.mime_type,
        extension=stored.extension,
        uploaded_by=ctx.principal.user.id,
    )
    db.add(version)
    db.flush()
    evidence.current_version_id = version.id
    link = EvidenceLink(
        tenant_id=ctx.tenant_id, evidence_id=evidence.id, target_type=_TARGET,
        target_id=item.id, created_by=ctx.principal.user.id,
    )
    db.add(link)
    db.flush()
    _log_event(db, ctx=ctx, event_type=EvidenceEventType.uploaded, evidence_id=evidence.id, version_id=version.id, item_id=item.id, details={"version_number": 1, "classification": classification.value, "size_bytes": stored.size_bytes})
    _log_event(db, ctx=ctx, event_type=EvidenceEventType.linked, evidence_id=evidence.id, link_id=link.id, item_id=item.id)
    db.commit()
    db.refresh(evidence)
    db.refresh(version)
    _audit(request, ctx=ctx, operation="UPLOAD_EVIDENCE", evidence_id=evidence.id, details={"item_id": str(item.id), "classification": classification.value, "size_bytes": stored.size_bytes})
    return _summary(evidence, version, item.id, ctx)


@router.get("/{evidence_id}/download")
def download_evidence(item_id: uuid.UUID, evidence_id: uuid.UUID, request: Request, db: db_dependency, ctx: view_dep):
    _get_item(db, ctx, item_id, request)
    evidence = _get_evidence(db, ctx, item_id, evidence_id, request=request)
    version = _current_version(db, evidence)
    if not _can_download(ctx, evidence.classification):
        _log_event(db, ctx=ctx, event_type=EvidenceEventType.access_denied, outcome=AuditOutcome.denied, evidence_id=evidence.id, version_id=version.id, item_id=item_id, details={"reason": "classification"})
        db.commit()
        _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE_DENIED", outcome=AuditOutcome.denied, evidence_id=evidence.id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")
    try:
        content = read_bytes(version.storage_key)
    except EvidenceStorageUnavailable as exc:
        _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE_DENIED", outcome=AuditOutcome.denied, evidence_id=evidence.id, details={"reason": type(exc).__name__})
        raise _storage_http_error(exc)
    _log_event(db, ctx=ctx, event_type=EvidenceEventType.downloaded, evidence_id=evidence.id, version_id=version.id, item_id=item_id, details={"classification": evidence.classification.value, "version_number": version.version_number})
    db.commit()
    _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE", evidence_id=evidence.id, details={"classification": evidence.classification.value, "version_number": version.version_number})
    filename = quote(version.original_filename)
    return Response(content=content, media_type=version.mime_type or "application/octet-stream", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})


@router.post("/{evidence_id}/versions", response_model=GapEvidenceSummary, status_code=status.HTTP_201_CREATED)
async def replace_evidence(
    item_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    db: db_dependency,
    ctx: manage_dep,
    file: UploadFile = File(...),
    classification: Classification = Form(...),
    description: str | None = Form(None),
):
    _get_item(db, ctx, item_id, request)
    evidence = _get_evidence(db, ctx, item_id, evidence_id, request=request)
    version_id = uuid.uuid4()
    next_number = (
        db.query(func.max(EvidenceVersion.version_number))
        .filter(EvidenceVersion.tenant_id == ctx.tenant_id, EvidenceVersion.evidence_id == evidence.id)
        .scalar()
        or 0
    ) + 1
    try:
        stored = await store_upload_file(upload=file, tenant_id=ctx.tenant_id, evidence_id=evidence.id, version_id=version_id)
    except (EvidenceStorageError, EvidenceStorageUnavailable) as exc:
        _audit(request, ctx=ctx, operation="REPLACE_EVIDENCE_DENIED", outcome=AuditOutcome.denied, evidence_id=evidence.id, details={"reason": type(exc).__name__})
        raise _storage_http_error(exc)
    version = EvidenceVersion(
        id=version_id,
        tenant_id=ctx.tenant_id,
        evidence_id=evidence.id,
        version_number=next_number,
        classification=classification,
        original_filename=stored.original_filename,
        storage_key=stored.storage_key,
        content_hash=stored.content_hash,
        hash_algorithm=stored.hash_algorithm,
        encrypted=stored.encrypted,
        encryption_scheme=stored.encryption_scheme,
        size_bytes=stored.size_bytes,
        mime_type=stored.mime_type,
        extension=stored.extension,
        uploaded_by=ctx.principal.user.id,
    )
    db.add(version)
    db.flush()
    evidence.current_version_id = version.id
    evidence.classification = classification
    if description is not None:
        evidence.description = _safe_description(description)
    _log_event(db, ctx=ctx, event_type=EvidenceEventType.replaced, evidence_id=evidence.id, version_id=version.id, item_id=item_id, details={"version_number": next_number, "classification": classification.value, "size_bytes": stored.size_bytes})
    db.commit()
    db.refresh(evidence)
    db.refresh(version)
    _audit(request, ctx=ctx, operation="REPLACE_EVIDENCE", evidence_id=evidence.id, details={"version_number": next_number, "classification": classification.value, "size_bytes": stored.size_bytes})
    return _summary(evidence, version, item_id, ctx)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def inactivate_evidence(
    item_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    db: db_dependency,
    ctx: manage_dep,
    body: GapEvidenceInactivateRequest | None = Body(default=None),
):
    _get_item(db, ctx, item_id, request)
    evidence = _get_evidence(db, ctx, item_id, evidence_id, request=request)
    version = _current_version(db, evidence)
    evidence.status = EvidenceStatus.inactive
    evidence.inactivated_by = ctx.principal.user.id
    evidence.inactivated_at = _now()
    evidence.inactivation_reason = _safe_description(body.reason if body else None)
    _log_event(db, ctx=ctx, event_type=EvidenceEventType.inactivated, evidence_id=evidence.id, version_id=version.id, item_id=item_id, details={"reason_provided": bool(evidence.inactivation_reason)})
    db.commit()
    _audit(request, ctx=ctx, operation="INACTIVATE_EVIDENCE", evidence_id=evidence.id, details={"reason_provided": bool(evidence.inactivation_reason)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{evidence_id}/history", response_model=GapEvidenceHistory)
def evidence_history(item_id: uuid.UUID, evidence_id: uuid.UUID, request: Request, db: db_dependency, ctx: manage_dep):
    _get_item(db, ctx, item_id, request)
    evidence = _get_evidence(db, ctx, item_id, evidence_id, include_inactive=True, request=request)
    current = _current_version(db, evidence)
    versions = scoped_query(db, EvidenceVersion, ctx).filter(EvidenceVersion.evidence_id == evidence.id).order_by(EvidenceVersion.version_number.desc()).all()
    events = scoped_query(db, EvidenceEvent, ctx).filter(EvidenceEvent.evidence_id == evidence.id).order_by(EvidenceEvent.occurred_at.desc()).all()
    return GapEvidenceHistory(
        evidence=_summary(evidence, current, item_id, ctx),
        versions=[_version_summary(v, evidence) for v in versions],
        events=[_event_summary(e) for e in events],
    )
