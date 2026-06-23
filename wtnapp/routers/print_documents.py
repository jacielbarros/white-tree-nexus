"""Printable previews, electronic signatures, template administration and integrity checks."""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.classification_access import can_read_classification, require_classification_read
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, get_org_context
from wtnapp.schemas.print_document_schema import (
    DocumentPreviewCreate,
    DocumentPreviewResponse,
    IntegrityVerificationResponse,
    PrintTemplateCreate,
    PrintTemplateResponse,
    PrintTemplateVersionCreate,
    PrintTemplateVersionResponse,
    SignPreviewRequest,
    SignedDocumentResponse,
)
from wtnapp.services import document_signature_service as signatures
from wtnapp.services import print_template_service as templates
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DocumentAccessEventType, PrintableDocumentType

router = APIRouter(prefix="/print-documents", tags=["print-documents"])

db_dep = Annotated[Session, Depends(get_db)]
ctx_dep = Annotated[OrgContext, Depends(get_org_context)]
template_admin_dep = Annotated[OrgContext, Depends(require_permission("manage_print_templates"))]


def _audit(
    request: Request,
    *,
    ctx: OrgContext,
    operation: str,
    outcome: AuditOutcome = AuditOutcome.success,
    entity_type: str = "print_document",
    entity_id: uuid.UUID | str | None = None,
    details: dict | None = None,
) -> None:
    AuditService.log_from_request(
        request=request,
        operation=operation,
        outcome=outcome,
        actor_user_id=ctx.principal.user.id,
        actor_role=ctx.role.value,
        tenant_id=ctx.tenant_id,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        details=details or {},
    )


def _audit_denied(request: Request, ctx: OrgContext, operation: str, exc: HTTPException) -> None:
    _audit(
        request,
        ctx=ctx,
        operation=operation,
        outcome=AuditOutcome.denied,
        details={"status_code": exc.status_code},
    )


def _classification_guard(
    db: Session,
    ctx: OrgContext,
    request: Request,
    *,
    classification,
    entity_type: str,
    entity_id: uuid.UUID,
    operation: str,
) -> None:
    try:
        require_classification_read(db, ctx, classification)
    except HTTPException as exc:
        signatures.log_event(
            db,
            ctx=ctx,
            event_type=DocumentAccessEventType.access_denied,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=AuditOutcome.denied,
            details={"reason": "classification"},
        )
        db.commit()
        _audit_denied(request, ctx, operation, exc)
        raise


def _pdf_response(content: bytes, filename: str) -> Response:
    encoded = quote(filename)
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded}"},
    )


@router.get("/templates", response_model=list[PrintTemplateResponse])
def list_print_templates(
    db: db_dep,
    ctx: template_admin_dep,
    document_type: PrintableDocumentType | None = Query(default=None),
):
    return templates.list_templates(db, ctx, document_type)


@router.post("/templates", response_model=PrintTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_print_template(
    payload: PrintTemplateCreate,
    request: Request,
    db: db_dep,
    ctx: template_admin_dep,
):
    template = templates.create_tenant_template(db, ctx, payload)
    signatures.log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.template_created,
        entity_type="print_template",
        entity_id=template.id,
        details={"document_type": payload.document_type.value},
    )
    db.commit()
    _audit(
        request,
        ctx=ctx,
        operation="CREATE_PRINT_TEMPLATE",
        entity_type="print_template",
        entity_id=template.id,
        details={"document_type": payload.document_type.value},
    )
    return template


@router.post(
    "/templates/{template_id}/versions",
    response_model=PrintTemplateVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_print_template_version(
    template_id: uuid.UUID,
    payload: PrintTemplateVersionCreate,
    request: Request,
    db: db_dep,
    ctx: template_admin_dep,
):
    version = templates.create_template_version(db, ctx, template_id, payload)
    signatures.log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.template_version_created,
        entity_type="print_template_version",
        entity_id=version.id,
        details={"template_id": str(template_id), "version_number": version.version_number},
    )
    db.commit()
    _audit(
        request,
        ctx=ctx,
        operation="CREATE_PRINT_TEMPLATE_VERSION",
        entity_type="print_template_version",
        entity_id=version.id,
        details={"template_id": str(template_id), "version_number": version.version_number},
    )
    return templates.version_response(db, version)


@router.post("/templates/{template_id}/versions/{version_id}/activate", response_model=PrintTemplateResponse)
def activate_print_template_version(
    template_id: uuid.UUID,
    version_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: template_admin_dep,
):
    template = templates.activate_template_version(db, ctx, template_id, version_id)
    signatures.log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.template_activated,
        entity_type="print_template",
        entity_id=template.id,
        details={"version_id": str(version_id)},
    )
    db.commit()
    _audit(
        request,
        ctx=ctx,
        operation="ACTIVATE_PRINT_TEMPLATE_VERSION",
        entity_type="print_template",
        entity_id=template.id,
        details={"version_id": str(version_id)},
    )
    return template


@router.post("/previews", response_model=DocumentPreviewResponse, status_code=status.HTTP_201_CREATED)
def create_preview(
    payload: DocumentPreviewCreate,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        preview = signatures.create_preview(db, ctx, payload)
    except HTTPException as exc:
        _audit_denied(request, ctx, "CREATE_DOCUMENT_PREVIEW_DENIED", exc)
        raise
    _audit(
        request,
        ctx=ctx,
        operation="CREATE_DOCUMENT_PREVIEW",
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": preview.document_type.value, "classification": preview.classification.value},
    )
    return preview


@router.get("/previews/{preview_id}", response_model=DocumentPreviewResponse)
def get_preview(
    preview_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        preview = signatures.get_preview(db, ctx, preview_id)
    except HTTPException as exc:
        _audit_denied(request, ctx, "GET_DOCUMENT_PREVIEW_DENIED", exc)
        raise
    return preview


@router.get("/previews/{preview_id}/pdf")
def download_preview_pdf(
    preview_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    preview = signatures.get_preview(db, ctx, preview_id)
    _classification_guard(
        db,
        ctx,
        request,
        classification=preview.classification,
        entity_type="document_preview",
        entity_id=preview.id,
        operation="DOWNLOAD_DOCUMENT_PREVIEW_DENIED",
    )
    try:
        preview, content = signatures.read_preview_pdf(db, ctx, preview_id)
    except HTTPException as exc:
        _audit_denied(request, ctx, "DOWNLOAD_DOCUMENT_PREVIEW_DENIED", exc)
        raise
    _audit(
        request,
        ctx=ctx,
        operation="DOWNLOAD_DOCUMENT_PREVIEW",
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": preview.document_type.value, "classification": preview.classification.value},
    )
    return _pdf_response(content, f"{preview.document_type.value}-preview.pdf")


@router.post("/previews/{preview_id}/sign", response_model=SignedDocumentResponse, status_code=status.HTTP_201_CREATED)
def sign_preview(
    preview_id: uuid.UUID,
    payload: SignPreviewRequest,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        document = signatures.sign_preview(db, ctx, preview_id, payload, request)
    except HTTPException as exc:
        _audit_denied(request, ctx, "SIGN_DOCUMENT_PREVIEW_DENIED", exc)
        raise
    _audit(
        request,
        ctx=ctx,
        operation="SIGN_DOCUMENT_PREVIEW",
        entity_type="signed_document",
        entity_id=document.id,
        details={"document_type": document.document_type.value, "version_number": document.version_number},
    )
    return signatures.signed_response_dict(db, document)


@router.get("/signed", response_model=list[SignedDocumentResponse])
def list_signed_documents(
    db: db_dep,
    ctx: ctx_dep,
    request: Request,
    document_type: PrintableDocumentType | None = Query(default=None),
    source_artifact_id: uuid.UUID | None = Query(default=None),
):
    try:
        rows = signatures.list_signed_documents(db, ctx, document_type, source_artifact_id)
    except HTTPException as exc:
        _audit_denied(request, ctx, "LIST_SIGNED_DOCUMENTS_DENIED", exc)
        raise
    visible = [doc for doc in rows if can_read_classification(db, ctx, doc.classification)]
    _audit(
        request,
        ctx=ctx,
        operation="LIST_SIGNED_DOCUMENTS",
        details={"document_type": document_type.value if document_type else None, "count": len(visible)},
    )
    return [signatures.signed_response_dict(db, doc) for doc in visible]


@router.get("/signed/{document_id}", response_model=SignedDocumentResponse)
def get_signed_document(
    document_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        document = signatures.get_signed_document(db, ctx, document_id)
        _classification_guard(
            db,
            ctx,
            request,
            classification=document.classification,
            entity_type="signed_document",
            entity_id=document.id,
            operation="GET_SIGNED_DOCUMENT_DENIED",
        )
    except HTTPException as exc:
        _audit_denied(request, ctx, "GET_SIGNED_DOCUMENT_DENIED", exc)
        raise
    return signatures.signed_response_dict(db, document)


@router.get("/signed/{document_id}/pdf")
def download_signed_pdf(
    document_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        document = signatures.get_signed_document(db, ctx, document_id)
        _classification_guard(
            db,
            ctx,
            request,
            classification=document.classification,
            entity_type="signed_document",
            entity_id=document.id,
            operation="DOWNLOAD_SIGNED_DOCUMENT_DENIED",
        )
        document, content = signatures.read_signed_pdf(db, ctx, document_id)
    except HTTPException as exc:
        _audit_denied(request, ctx, "DOWNLOAD_SIGNED_DOCUMENT_DENIED", exc)
        raise
    _audit(
        request,
        ctx=ctx,
        operation="DOWNLOAD_SIGNED_DOCUMENT",
        entity_type="signed_document",
        entity_id=document.id,
        details={"document_type": document.document_type.value, "version_number": document.version_number},
    )
    return _pdf_response(content, f"{document.identifier}.pdf")


@router.post("/signed/{document_id}/verify", response_model=IntegrityVerificationResponse)
def verify_signed_document(
    document_id: uuid.UUID,
    request: Request,
    db: db_dep,
    ctx: ctx_dep,
):
    try:
        document = signatures.get_signed_document(db, ctx, document_id)
        _classification_guard(
            db,
            ctx,
            request,
            classification=document.classification,
            entity_type="signed_document",
            entity_id=document.id,
            operation="VERIFY_SIGNED_DOCUMENT_DENIED",
        )
        result = signatures.verify_signed_document(db, ctx, document_id)
    except HTTPException as exc:
        _audit_denied(request, ctx, "VERIFY_SIGNED_DOCUMENT_DENIED", exc)
        raise
    _audit(
        request,
        ctx=ctx,
        operation="VERIFY_SIGNED_DOCUMENT",
        entity_type="signed_document",
        entity_id=document_id,
        details={"valid": result["valid"]},
    )
    return result
