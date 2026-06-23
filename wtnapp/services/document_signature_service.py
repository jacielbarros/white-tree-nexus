"""Generic electronic signature flow for controlled printable documents."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp import settings
from wtnapp.helpers.permissions import has_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.print_document_model import (
    DocumentAccessEvent,
    DocumentPreview,
    DocumentSignature,
    PrintTemplate,
    PrintTemplateVersion,
    SignedDocument,
    SignedDocumentSnapshot,
)
from wtnapp.schemas.print_document_schema import DocumentPreviewCreate, SignPreviewRequest
from wtnapp.services import print_render_service
from wtnapp.services.print_snapshot_service import build_snapshot
from wtnapp.services.print_template_service import (
    canonical_json,
    resolve_active_template_version,
    resolve_variables,
    sha256_canonical,
)
from wtnapp.settings import (
    AuditOutcome,
    Classification,
    DocumentAccessEventType,
    DocumentPreviewStatus,
    PrintableDocumentType,
    SignedDocumentStatus,
)
from wtnapp.utils.document_storage import (
    DocumentStorageError,
    DocumentStorageUnavailable,
    read_pdf,
    sha256_bytes,
    store_pdf,
)

VIEW_PERMISSION_BY_TYPE: dict[PrintableDocumentType, str] = {
    PrintableDocumentType.context_report: "view_context",
    PrintableDocumentType.gap_report: "view_gap",
    PrintableDocumentType.soa_report: "view_soa",
    PrintableDocumentType.gap_baseline: "view_gap",
    PrintableDocumentType.form_response: "view_form",
}

SIGN_PERMISSION_BY_TYPE: dict[PrintableDocumentType, str] = {
    PrintableDocumentType.context_report: "approve_context_document",
    PrintableDocumentType.gap_report: "approve_gap_baseline",
    PrintableDocumentType.soa_report: "approve_soa",
    PrintableDocumentType.gap_baseline: "approve_gap_baseline",
    PrintableDocumentType.form_response: "sign_form",
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _check_permission(ctx: OrgContext, permission: str) -> None:
    if not has_permission(ctx.role, permission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente.")


def check_view_permission(ctx: OrgContext, document_type: PrintableDocumentType) -> None:
    _check_permission(ctx, VIEW_PERMISSION_BY_TYPE[document_type])


def check_sign_permission(ctx: OrgContext, document_type: PrintableDocumentType) -> None:
    _check_permission(ctx, SIGN_PERMISSION_BY_TYPE[document_type])


def log_event(
    db: Session,
    *,
    ctx: OrgContext,
    event_type: DocumentAccessEventType,
    entity_type: str,
    entity_id: uuid.UUID | None,
    outcome: AuditOutcome = AuditOutcome.success,
    details: dict[str, Any] | None = None,
) -> None:
    db.add(
        DocumentAccessEvent(
            tenant_id=ctx.tenant_id,
            event_type=event_type.value,
            entity_type=entity_type,
            entity_id=entity_id,
            actor_user_id=ctx.principal.user.id,
            actor_role=ctx.role.value,
            outcome=outcome.value,
            details=details or {},
        )
    )


def _storage_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, DocumentStorageError):
        return HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Storage de documentos indisponivel.")


def _render_http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, print_render_service.DocumentRenderTimeout):
        return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Tempo limite de geracao do PDF excedido.")
    return HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Nao foi possivel gerar o PDF.")


def _template_default_classification(db: Session, version: PrintTemplateVersion) -> Classification:
    template = db.get(PrintTemplate, version.template_id)
    return template.default_classification if template else Classification.uso_interno


def create_preview(
    db: Session,
    ctx: OrgContext,
    payload: DocumentPreviewCreate,
) -> DocumentPreview:
    check_view_permission(ctx, payload.document_type)
    version = resolve_active_template_version(db, ctx, payload.document_type, payload.template_version_id)
    classification = payload.classification or _template_default_classification(db, version)
    bundle = build_snapshot(db, ctx, payload.document_type, classification.value)
    variables, warnings = resolve_variables(version, bundle.variables)
    snapshot = dict(bundle.snapshot)
    snapshot["variables"] = variables
    snapshot_hash = sha256_canonical(snapshot)
    preview_id = uuid.uuid4()
    try:
        pdf = print_render_service.render_pdf(
            template_version=version,
            snapshot=snapshot,
            variables=variables,
            is_preview=True,
        )
        stored = store_pdf(content=pdf, tenant_id=ctx.tenant_id, kind="previews", document_id=preview_id)
    except (DocumentStorageError, DocumentStorageUnavailable) as exc:
        raise _storage_http_error(exc)
    except (print_render_service.DocumentRenderError, print_render_service.DocumentRenderTimeout) as exc:
        raise _render_http_error(exc)

    preview = DocumentPreview(
        id=preview_id,
        tenant_id=ctx.tenant_id,
        document_type=payload.document_type,
        source_artifact_type=bundle.source_artifact_type,
        source_artifact_id=bundle.source_artifact_id,
        source_document_version_id=bundle.source_document_version_id,
        template_version_id=version.id,
        classification=classification,
        status=DocumentPreviewStatus.active,
        artifact_fingerprint=bundle.artifact_fingerprint,
        template_hash=version.content_hash,
        snapshot_hash=snapshot_hash,
        preview_pdf_hash=stored.content_hash,
        preview_storage_key=stored.storage_key,
        snapshot_json=snapshot,
        rendered_variables=variables,
        warnings=warnings,
        expires_at=_now() + timedelta(minutes=settings.DOCUMENT_PREVIEW_TTL_MINUTES),
        created_by=ctx.principal.user.id,
    )
    db.add(preview)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.preview_created,
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": payload.document_type.value, "classification": classification.value},
    )
    db.commit()
    db.refresh(preview)
    return preview


def get_preview(db: Session, ctx: OrgContext, preview_id: uuid.UUID) -> DocumentPreview:
    preview = scoped_query(db, DocumentPreview, ctx).filter(DocumentPreview.id == preview_id).first()
    if preview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    check_view_permission(ctx, preview.document_type)
    return preview


def read_preview_pdf(db: Session, ctx: OrgContext, preview_id: uuid.UUID) -> tuple[DocumentPreview, bytes]:
    preview = get_preview(db, ctx, preview_id)
    try:
        content = read_pdf(preview.preview_storage_key)
    except DocumentStorageUnavailable as exc:
        raise _storage_http_error(exc)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.preview_downloaded,
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": preview.document_type.value, "classification": preview.classification.value},
    )
    db.commit()
    return preview, content


def _next_signed_version(db: Session, preview: DocumentPreview) -> int:
    return (
        db.query(func.max(SignedDocument.version_number))
        .filter(
            SignedDocument.tenant_id == preview.tenant_id,
            SignedDocument.document_type == preview.document_type,
            SignedDocument.source_artifact_type == preview.source_artifact_type,
            SignedDocument.source_artifact_id == preview.source_artifact_id,
        )
        .scalar()
        or 0
    ) + 1


def _identifier(preview: DocumentPreview, version_number: int) -> str:
    source = str(preview.source_artifact_id or preview.id).split("-")[0].upper()
    return f"WTN-{preview.document_type.value.replace('_', '-').upper()}-{source}-V{version_number:03d}"


def _mark_preview(preview: DocumentPreview, status_value: DocumentPreviewStatus) -> None:
    preview.status = status_value


def _validate_preview_for_signature(db: Session, ctx: OrgContext, preview: DocumentPreview, body: SignPreviewRequest) -> None:
    if preview.status != DocumentPreviewStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preview nao esta ativo para assinatura.")
    if _aware(preview.expires_at) < _now():
        _mark_preview(preview, DocumentPreviewStatus.expired)
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Preview expirado. Gere uma nova pre-visualizacao.")
    if body.confirm_snapshot_hash and body.confirm_snapshot_hash != preview.snapshot_hash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Hash confirmado nao corresponde ao preview.")
    template_version = db.get(PrintTemplateVersion, preview.template_version_id)
    if template_version is None or template_version.content_hash != preview.template_hash:
        _mark_preview(preview, DocumentPreviewStatus.stale)
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Template alterado. Gere uma nova pre-visualizacao.")
    current = build_snapshot(db, ctx, preview.document_type, preview.classification.value)
    if current.artifact_fingerprint != preview.artifact_fingerprint:
        _mark_preview(preview, DocumentPreviewStatus.stale)
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Artefato alterado. Gere uma nova pre-visualizacao.")


def sign_preview(
    db: Session,
    ctx: OrgContext,
    preview_id: uuid.UUID,
    body: SignPreviewRequest,
    request: Request | None = None,
) -> SignedDocument:
    preview = get_preview(db, ctx, preview_id)
    check_sign_permission(ctx, preview.document_type)
    _validate_preview_for_signature(db, ctx, preview, body)

    template_version = db.get(PrintTemplateVersion, preview.template_version_id)
    if template_version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Template do preview indisponivel.")
    version_number = _next_signed_version(db, preview)
    signed_id = uuid.uuid4()
    signed_at = _now()
    identifier = _identifier(preview, version_number)
    user = ctx.principal.user
    signature_meta = {
        "identifier": identifier,
        "signer_name": user.full_name or str(user.id),
        "signed_at": signed_at.isoformat(),
        "pdf_hash": preview.snapshot_hash,
    }
    variables = dict(preview.rendered_variables or {})
    variables["document_status"] = "Assinado"
    try:
        pdf = print_render_service.render_pdf(
            template_version=template_version,
            snapshot=preview.snapshot_json,
            variables=variables,
            is_preview=False,
            signature_meta=signature_meta,
        )
        stored = store_pdf(content=pdf, tenant_id=ctx.tenant_id, kind="signed", document_id=signed_id)
    except (DocumentStorageError, DocumentStorageUnavailable) as exc:
        raise _storage_http_error(exc)
    except (print_render_service.DocumentRenderError, print_render_service.DocumentRenderTimeout) as exc:
        raise _render_http_error(exc)

    signed = SignedDocument(
        id=signed_id,
        tenant_id=ctx.tenant_id,
        document_type=preview.document_type,
        source_artifact_type=preview.source_artifact_type,
        source_artifact_id=preview.source_artifact_id,
        source_document_version_id=preview.source_document_version_id,
        preview_id=preview.id,
        template_version_id=preview.template_version_id,
        version_number=version_number,
        status=SignedDocumentStatus.signed,
        classification=preview.classification,
        identifier=identifier,
        pdf_hash=stored.content_hash,
        snapshot_hash=preview.snapshot_hash,
        hash_algorithm=stored.hash_algorithm,
        pdf_storage_key=stored.storage_key,
        size_bytes=stored.size_bytes,
        signed_by=user.id,
        signed_at=signed_at,
    )
    db.add(signed)
    db.flush()
    db.add(
        SignedDocumentSnapshot(
            tenant_id=ctx.tenant_id,
            signed_document_id=signed.id,
            artifact_fingerprint=preview.artifact_fingerprint,
            template_hash=preview.template_hash,
            snapshot_hash=preview.snapshot_hash,
            rendered_variables=variables,
            snapshot_json=preview.snapshot_json,
        )
    )
    db.add(
        DocumentSignature(
            tenant_id=ctx.tenant_id,
            signed_document_id=signed.id,
            signer_user_id=user.id,
            signer_role=ctx.role.value,
            signer_name=user.full_name or str(user.id),
            signer_email=user.email,
            signed_at=signed_at,
            content_hash=preview.snapshot_hash,
            pdf_hash=stored.content_hash,
            algorithm="sha256",
            level="advanced",
            auth_context={"method": "authenticated_session", "super_admin_context": ctx.is_super_admin},
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
    _mark_preview(preview, DocumentPreviewStatus.signed)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.signed,
        entity_type="signed_document",
        entity_id=signed.id,
        details={"document_type": preview.document_type.value, "version_number": version_number},
    )
    db.commit()
    db.refresh(signed)
    return signed


def get_signed_document(db: Session, ctx: OrgContext, document_id: uuid.UUID) -> SignedDocument:
    document = scoped_query(db, SignedDocument, ctx).filter(SignedDocument.id == document_id).first()
    if document is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    check_view_permission(ctx, document.document_type)
    return document


def list_signed_documents(
    db: Session,
    ctx: OrgContext,
    document_type: PrintableDocumentType | None = None,
    source_artifact_id: uuid.UUID | None = None,
) -> list[SignedDocument]:
    query = scoped_query(db, SignedDocument, ctx)
    if document_type is not None:
        check_view_permission(ctx, document_type)
        query = query.filter(SignedDocument.document_type == document_type)
    if source_artifact_id is not None:
        query = query.filter(SignedDocument.source_artifact_id == source_artifact_id)
    return query.order_by(SignedDocument.signed_at.desc(), SignedDocument.version_number.desc()).all()


def is_obsolete(db: Session, document: SignedDocument) -> bool:
    newer = (
        db.query(SignedDocument)
        .filter(
            SignedDocument.tenant_id == document.tenant_id,
            SignedDocument.document_type == document.document_type,
            SignedDocument.source_artifact_type == document.source_artifact_type,
            SignedDocument.source_artifact_id == document.source_artifact_id,
            SignedDocument.version_number > document.version_number,
        )
        .first()
    )
    return newer is not None


def signed_response_dict(db: Session, document: SignedDocument) -> dict[str, Any]:
    status_value = SignedDocumentStatus.obsolete if is_obsolete(db, document) else SignedDocumentStatus.signed
    return {
        "id": document.id,
        "document_type": document.document_type,
        "source_artifact_id": document.source_artifact_id,
        "template_version_id": document.template_version_id,
        "version_number": document.version_number,
        "status": status_value,
        "classification": document.classification,
        "identifier": document.identifier,
        "pdf_hash": document.pdf_hash,
        "snapshot_hash": document.snapshot_hash,
        "size_bytes": document.size_bytes,
        "signed_by": document.signed_by,
        "signed_at": document.signed_at,
    }


def read_signed_pdf(db: Session, ctx: OrgContext, document_id: uuid.UUID) -> tuple[SignedDocument, bytes]:
    document = get_signed_document(db, ctx, document_id)
    try:
        content = read_pdf(document.pdf_storage_key)
    except DocumentStorageUnavailable as exc:
        raise _storage_http_error(exc)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.signed_downloaded,
        entity_type="signed_document",
        entity_id=document.id,
        details={"document_type": document.document_type.value, "version_number": document.version_number},
    )
    db.commit()
    return document, content


def verify_signed_document(db: Session, ctx: OrgContext, document_id: uuid.UUID) -> dict[str, Any]:
    document = get_signed_document(db, ctx, document_id)
    snapshot = (
        scoped_query(db, SignedDocumentSnapshot, ctx)
        .filter(SignedDocumentSnapshot.signed_document_id == document.id)
        .first()
    )
    try:
        content = read_pdf(document.pdf_storage_key)
        pdf_hash = sha256_bytes(content)
    except DocumentStorageUnavailable:
        pdf_hash = ""
    snapshot_hash = sha256_canonical(snapshot.snapshot_json) if snapshot else ""
    valid = pdf_hash == document.pdf_hash and snapshot_hash == document.snapshot_hash
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.verified,
        entity_type="signed_document",
        entity_id=document.id,
        details={"valid": valid, "document_type": document.document_type.value},
    )
    db.commit()
    return {
        "valid": valid,
        "identifier": document.identifier,
        "pdf_hash": document.pdf_hash,
        "snapshot_hash": document.snapshot_hash,
        "verified_at": _now(),
    }
