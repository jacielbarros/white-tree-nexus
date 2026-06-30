"""Repositório transversal de evidências (Feature 014): upload, repositório central, vínculos,
download, versionamento e cadeia de custódia. Generaliza a Feature 008."""

import uuid
from datetime import datetime, timezone
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Query, Request, Response, UploadFile, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import has_permission, require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceLink, EvidenceVersion
from wtnapp.schemas.evidence_schema import (
    EvidenceEventSummary,
    EvidenceHistory,
    EvidenceInactivateRequest,
    EvidenceLinkOut,
    EvidenceLinkRequest,
    EvidenceSummary,
    EvidenceVersionSummary,
)
from wtnapp.services import evidence_service as svc
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, Classification, EvidenceEventType, EvidenceStatus, SgsiArtifactType
from wtnapp.utils.evidence_storage import (
    EvidenceStorageError,
    EvidenceStorageUnavailable,
    read_bytes,
    store_upload_file,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_evidence"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_evidence"))]


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
        entity_type="evidence",
        entity_id=str(evidence_id) if evidence_id else None,
        details=details or {},
    )


def _not_found(request: Request, ctx: OrgContext, *, resource: str, target_id: uuid.UUID) -> HTTPException:
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
    return HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


def _storage_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, EvidenceStorageError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Storage de evidencias indisponivel.")


def _link_out(link: EvidenceLink) -> EvidenceLinkOut:
    return EvidenceLinkOut(id=link.id, target_type=link.target_type, target_id=link.target_id, active=link.active)


def _summary(db: Session, ctx: OrgContext, evidence: Evidence, version: EvidenceVersion) -> EvidenceSummary:
    return EvidenceSummary(
        id=evidence.id,
        title=evidence.title,
        description=evidence.description,
        classification=evidence.classification,
        status=evidence.status,
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
        can_download=svc.can_download(ctx, evidence.classification),
        links=[_link_out(link) for link in svc.active_links(db, ctx, evidence.id)],
    )


def _require_target(request: Request, db: Session, ctx: OrgContext, target_type: SgsiArtifactType, target_id: uuid.UUID) -> None:
    if not svc.target_exists(db, ctx, target_type, target_id):
        raise _not_found(request, ctx, resource=f"target:{target_type.value}", target_id=target_id)


def _get_or_404(request: Request, db: Session, ctx: OrgContext, evidence_id: uuid.UUID, *, include_inactive: bool = False) -> Evidence:
    evidence = svc.get_evidence(db, ctx, evidence_id, include_inactive=include_inactive)
    if evidence is None:
        raise _not_found(request, ctx, resource="evidence", target_id=evidence_id)
    return evidence


@router.get("", response_model=list[EvidenceSummary])
def search_evidence(
    request: Request,
    db: db_dep,
    ctx: view_dep,
    q: str | None = None,
    target_type: SgsiArtifactType | None = None,
    target_id: uuid.UUID | None = None,
    classification: Classification | None = None,
    author_id: uuid.UUID | None = None,
    status_filter: EvidenceStatus | None = Query(default=None, alias="status"),
    page: int = 1,
    page_size: int = 50,
):
    query = scoped_query(db, Evidence, ctx)
    if status_filter is None:
        query = query.filter(Evidence.status == EvidenceStatus.active)
    else:
        if status_filter == EvidenceStatus.inactive and not has_permission(ctx.role, "manage_evidence"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")
        query = query.filter(Evidence.status == status_filter)
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(Evidence.title.ilike(like))
    if classification is not None:
        query = query.filter(Evidence.classification == classification)
    if author_id is not None:
        query = query.filter(Evidence.created_by == author_id)
    if target_type is not None or target_id is not None:
        link_q = scoped_query(db, EvidenceLink, ctx).filter(EvidenceLink.active.is_(True))
        if target_type is not None:
            link_q = link_q.filter(EvidenceLink.target_type == target_type)
        if target_id is not None:
            link_q = link_q.filter(EvidenceLink.target_id == target_id)
        evidence_ids = {row.evidence_id for row in link_q.all()}
        query = query.filter(Evidence.id.in_(evidence_ids or {uuid.uuid4()}))

    page = max(1, page)
    page_size = max(1, min(page_size, 200))
    rows = query.order_by(Evidence.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    summaries: list[EvidenceSummary] = []
    for evidence in rows:
        version = svc.current_version(db, evidence)
        if version is not None:
            summaries.append(_summary(db, ctx, evidence, version))
    return summaries


@router.post("", response_model=EvidenceSummary, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    request: Request,
    db: db_dep,
    ctx: manage_dep,
    file: UploadFile = File(...),
    classification: Classification = Form(...),
    target_type: SgsiArtifactType = Form(...),
    target_id: uuid.UUID = Form(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
):
    _require_target(request, db, ctx, target_type, target_id)
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
        title=svc.safe_title(title, stored.original_filename),
        description=svc.safe_text(description),
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
        tenant_id=ctx.tenant_id,
        evidence_id=evidence.id,
        target_type=target_type,
        target_id=target_id,
        created_by=ctx.principal.user.id,
    )
    db.add(link)
    db.flush()
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.uploaded, evidence_id=evidence.id, version_id=version.id, details={"version_number": 1, "classification": classification.value, "size_bytes": stored.size_bytes})
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.linked, evidence_id=evidence.id, link_id=link.id, target_type=target_type, target_id=target_id)
    db.commit()
    db.refresh(evidence)
    db.refresh(version)
    _audit(request, ctx=ctx, operation="UPLOAD_EVIDENCE", evidence_id=evidence.id, details={"target_type": target_type.value, "classification": classification.value, "size_bytes": stored.size_bytes})
    return _summary(db, ctx, evidence, version)


@router.get("/{evidence_id}", response_model=EvidenceSummary)
def get_evidence_detail(evidence_id: uuid.UUID, request: Request, db: db_dep, ctx: view_dep):
    include_inactive = has_permission(ctx.role, "manage_evidence")
    evidence = _get_or_404(request, db, ctx, evidence_id, include_inactive=include_inactive)
    version = svc.current_version(db, evidence)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evidencia sem versao corrente.")
    return _summary(db, ctx, evidence, version)


@router.get("/{evidence_id}/download")
def download_evidence(evidence_id: uuid.UUID, request: Request, db: db_dep, ctx: view_dep):
    evidence = _get_or_404(request, db, ctx, evidence_id)
    version = svc.current_version(db, evidence)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evidencia sem versao corrente.")
    if not svc.can_download(ctx, evidence.classification):
        svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.access_denied, outcome=AuditOutcome.denied, evidence_id=evidence.id, version_id=version.id, details={"reason": "classification"})
        db.commit()
        _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE_DENIED", outcome=AuditOutcome.denied, evidence_id=evidence.id)
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")
    try:
        content = read_bytes(version.storage_key)
    except EvidenceStorageUnavailable as exc:
        _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE_DENIED", outcome=AuditOutcome.denied, evidence_id=evidence.id, details={"reason": type(exc).__name__})
        raise _storage_http_error(exc)
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.downloaded, evidence_id=evidence.id, version_id=version.id, details={"classification": evidence.classification.value, "version_number": version.version_number})
    db.commit()
    _audit(request, ctx=ctx, operation="DOWNLOAD_EVIDENCE", evidence_id=evidence.id, details={"version_number": version.version_number})
    filename = quote(version.original_filename)
    return Response(content=content, media_type=version.mime_type or "application/octet-stream", headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})


@router.post("/{evidence_id}/versions", response_model=EvidenceSummary, status_code=status.HTTP_201_CREATED)
async def replace_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: manage_dep,
    file: UploadFile = File(...),
    classification: Classification = Form(...),
    description: str | None = Form(None),
):
    evidence = _get_or_404(request, db, ctx, evidence_id)
    version_id = uuid.uuid4()
    next_number = svc.next_version_number(db, ctx, evidence.id)
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
        evidence.description = svc.safe_text(description)
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.replaced, evidence_id=evidence.id, version_id=version.id, details={"version_number": next_number, "classification": classification.value, "size_bytes": stored.size_bytes})
    db.commit()
    db.refresh(evidence)
    db.refresh(version)
    _audit(request, ctx=ctx, operation="REPLACE_EVIDENCE", evidence_id=evidence.id, details={"version_number": next_number})
    return _summary(db, ctx, evidence, version)


@router.delete("/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def inactivate_evidence(
    evidence_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: manage_dep,
    body: EvidenceInactivateRequest | None = Body(default=None),
):
    evidence = _get_or_404(request, db, ctx, evidence_id)
    evidence.status = EvidenceStatus.inactive
    evidence.inactivated_by = ctx.principal.user.id
    evidence.inactivated_at = _now()
    evidence.inactivation_reason = svc.safe_text(body.reason if body else None, limit=300)
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.inactivated, evidence_id=evidence.id, details={"reason_provided": bool(evidence.inactivation_reason)})
    db.commit()
    _audit(request, ctx=ctx, operation="INACTIVATE_EVIDENCE", evidence_id=evidence.id, details={"reason_provided": bool(evidence.inactivation_reason)})
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{evidence_id}/history", response_model=EvidenceHistory)
def evidence_history(evidence_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    evidence = _get_or_404(request, db, ctx, evidence_id, include_inactive=True)
    current = svc.current_version(db, evidence)
    if current is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Evidencia sem versao corrente.")
    versions = scoped_query(db, EvidenceVersion, ctx).filter(EvidenceVersion.evidence_id == evidence.id).order_by(EvidenceVersion.version_number.desc()).all()
    events = scoped_query(db, EvidenceEvent, ctx).filter(EvidenceEvent.evidence_id == evidence.id).order_by(EvidenceEvent.occurred_at.desc()).all()
    return EvidenceHistory(
        evidence=_summary(db, ctx, evidence, current),
        versions=[
            EvidenceVersionSummary(
                id=v.id, version_number=v.version_number, classification=v.classification,
                file_name=v.original_filename, mime_type=v.mime_type, extension=v.extension,
                size_bytes=v.size_bytes, content_hash=v.content_hash, hash_algorithm=v.hash_algorithm,
                uploaded_by=v.uploaded_by, uploaded_at=v.uploaded_at, is_current=evidence.current_version_id == v.id,
            )
            for v in versions
        ],
        events=[
            EvidenceEventSummary(id=e.id, event_type=e.event_type, outcome=e.outcome, actor_id=e.actor_id, occurred_at=e.occurred_at, details=e.details)
            for e in events
        ],
    )


@router.post("/{evidence_id}/links", response_model=EvidenceLinkOut, status_code=status.HTTP_201_CREATED)
def link_evidence(evidence_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep, body: EvidenceLinkRequest = Body(...)):
    evidence = _get_or_404(request, db, ctx, evidence_id)
    _require_target(request, db, ctx, body.target_type, body.target_id)
    existing = (
        scoped_query(db, EvidenceLink, ctx)
        .filter(EvidenceLink.evidence_id == evidence.id, EvidenceLink.target_type == body.target_type, EvidenceLink.target_id == body.target_id)
        .first()
    )
    if existing is not None:
        if existing.active:
            raise HTTPException(status.HTTP_409_CONFLICT, "Vinculo ja existe.")
        existing.active = True
        svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.linked, evidence_id=evidence.id, link_id=existing.id, target_type=body.target_type, target_id=body.target_id)
        db.commit()
        _audit(request, ctx=ctx, operation="LINK_EVIDENCE", evidence_id=evidence.id, details={"target_type": body.target_type.value})
        return _link_out(existing)
    link = EvidenceLink(tenant_id=ctx.tenant_id, evidence_id=evidence.id, target_type=body.target_type, target_id=body.target_id, created_by=ctx.principal.user.id)
    db.add(link)
    db.flush()
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.linked, evidence_id=evidence.id, link_id=link.id, target_type=body.target_type, target_id=body.target_id)
    db.commit()
    db.refresh(link)
    _audit(request, ctx=ctx, operation="LINK_EVIDENCE", evidence_id=evidence.id, details={"target_type": body.target_type.value})
    return _link_out(link)


@router.delete("/{evidence_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_evidence(evidence_id: uuid.UUID, link_id: uuid.UUID, request: Request, db: db_dep, ctx: manage_dep):
    evidence = _get_or_404(request, db, ctx, evidence_id)
    link = scoped_query(db, EvidenceLink, ctx).filter(EvidenceLink.id == link_id, EvidenceLink.evidence_id == evidence.id, EvidenceLink.active.is_(True)).first()
    if link is None:
        raise _not_found(request, ctx, resource="evidence_link", target_id=link_id)
    link.active = False
    svc.log_event(db, ctx=ctx, event_type=EvidenceEventType.unlinked, evidence_id=evidence.id, link_id=link.id, target_type=link.target_type, target_id=link.target_id)
    db.commit()
    _audit(request, ctx=ctx, operation="UNLINK_EVIDENCE", evidence_id=evidence.id, details={"target_type": link.target_type.value})
    return Response(status_code=status.HTTP_204_NO_CONTENT)
