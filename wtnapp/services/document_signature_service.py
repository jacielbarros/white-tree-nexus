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
    DocumentSignaturePlacement,
    PrintTemplate,
    PrintTemplateVersion,
    SignedDocument,
    SignedDocumentSignaturePlacement,
    SignedDocumentSnapshot,
)
from wtnapp.models.organization_model import Organization
from wtnapp.schemas.print_document_schema import (
    DocumentPreviewCreate,
    PreviewLayoutResponse,
    SignPreviewRequest,
    SignaturePlacementCreate,
)
from wtnapp.services import print_render_service
from wtnapp.services.print_snapshot_service import build_snapshot
from wtnapp.services.print_template_service import (
    canonical_json,
    resolve_active_template_version,
    resolve_variables,
    sha256_canonical,
    signature_appearance_policy,
    signature_policy_hash,
)
from wtnapp.settings import (
    AuditOutcome,
    Classification,
    DocumentAccessEventType,
    DocumentPreviewStatus,
    OrgStatus,
    PrintableDocumentType,
    SignatureCoordinateSystem,
    SignatureMethod,
    SignaturePlacementOrigin,
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


def _ensure_org_available(db: Session, ctx: OrgContext) -> None:
    org = db.get(Organization, ctx.tenant_id)
    if org is None or org.status == OrgStatus.suspended:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Organizacao indisponivel.")


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


def _placement_base_dict(placement: DocumentSignaturePlacement | SignedDocumentSignaturePlacement) -> dict[str, Any]:
    return {
        "page_number": placement.page_number,
        "x_points": placement.x_points,
        "y_points": placement.y_points,
        "width_points": placement.width_points,
        "height_points": placement.height_points,
        "page_width_points": placement.page_width_points,
        "page_height_points": placement.page_height_points,
        "coordinate_system": placement.coordinate_system.value if hasattr(placement.coordinate_system, "value") else placement.coordinate_system,
        "origin": placement.origin.value if hasattr(placement.origin, "value") else placement.origin,
    }


def _placement_hash(value: dict[str, Any]) -> str:
    return sha256_canonical(
        {
            "page_number": int(value["page_number"]),
            "x_points": round(float(value["x_points"]), 4),
            "y_points": round(float(value["y_points"]), 4),
            "width_points": round(float(value["width_points"]), 4),
            "height_points": round(float(value["height_points"]), 4),
            "page_width_points": round(float(value["page_width_points"]), 4),
            "page_height_points": round(float(value["page_height_points"]), 4),
            "coordinate_system": str(value.get("coordinate_system") or SignatureCoordinateSystem.pdf_points_bottom_left.value),
            "origin": str(value.get("origin") or SignaturePlacementOrigin.user.value),
        }
    )


def _page_metric_for(preview: DocumentPreview, page_number: int) -> dict[str, Any] | None:
    for page in preview.pdf_page_metrics or []:
        if int(page.get("page_number", 0)) == page_number:
            return page
    return None


def _rect_intersects(a: dict[str, float], b: dict[str, float]) -> bool:
    return not (
        a["x"] + a["width"] <= b["x"]
        or b["x"] + b["width"] <= a["x"]
        or a["y"] + a["height"] <= b["y"]
        or b["y"] + b["height"] <= a["y"]
    )


def _validate_placement_dict(
    *,
    preview: DocumentPreview,
    placement: dict[str, Any],
    policy: dict[str, Any],
) -> None:
    if str(placement.get("coordinate_system")) != SignatureCoordinateSystem.pdf_points_bottom_left.value:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Sistema de coordenadas invalido.")
    page_number = int(placement["page_number"])
    page = _page_metric_for(preview, page_number)
    if page is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pagina do PDF invalida.")
    values = {
        "x": float(placement["x_points"]),
        "y": float(placement["y_points"]),
        "width": float(placement["width_points"]),
        "height": float(placement["height_points"]),
        "page_width": float(placement["page_width_points"]),
        "page_height": float(placement["page_height_points"]),
    }
    if values["x"] < 0 or values["y"] < 0 or values["width"] <= 0 or values["height"] <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dimensoes do selo invalidas.")
    if values["width"] < float(policy["min_width_points"]) or values["height"] < float(policy["min_height_points"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selo menor que o permitido.")
    if values["width"] > float(policy["max_width_points"]) or values["height"] > float(policy["max_height_points"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selo maior que o permitido.")
    page_width = float(page["width_points"])
    page_height = float(page["height_points"])
    tolerance = 0.5
    if abs(values["page_width"] - page_width) > tolerance or abs(values["page_height"] - page_height) > tolerance:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dimensoes da pagina nao correspondem ao preview.")
    if values["x"] + values["width"] > page_width + tolerance or values["y"] + values["height"] > page_height + tolerance:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Posicao do selo fora da pagina.")
    seal_rect = {"x": values["x"], "y": values["y"], "width": values["width"], "height": values["height"]}
    for area in policy.get("blocked_areas") or []:
        blocked_page = area.get("page", "all")
        if blocked_page != "all" and int(blocked_page) != page_number:
            continue
        blocked_rect = {
            "x": float(area["x_points"]),
            "y": float(area["y_points"]),
            "width": float(area["width_points"]),
            "height": float(area["height_points"]),
        }
        if _rect_intersects(seal_rect, blocked_rect):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Selo invade area bloqueada do documento.")


def _next_placement_revision(db: Session, preview: DocumentPreview) -> int:
    return (
        db.query(func.max(DocumentSignaturePlacement.placement_revision))
        .filter(
            DocumentSignaturePlacement.tenant_id == preview.tenant_id,
            DocumentSignaturePlacement.preview_id == preview.id,
        )
        .scalar()
        or 0
    ) + 1


def _latest_placement(db: Session, ctx: OrgContext, preview_id: uuid.UUID) -> DocumentSignaturePlacement | None:
    return (
        scoped_query(db, DocumentSignaturePlacement, ctx)
        .filter(DocumentSignaturePlacement.preview_id == preview_id)
        .order_by(DocumentSignaturePlacement.placement_revision.desc())
        .first()
    )


def placement_response_dict(placement: DocumentSignaturePlacement) -> dict[str, Any]:
    return {
        **_placement_base_dict(placement),
        "id": placement.id,
        "preview_id": placement.preview_id,
        "placement_revision": placement.placement_revision,
        "placement_hash": placement.placement_hash,
        "created_by": placement.created_by,
        "created_at": placement.created_at,
    }


def signed_placement_response_dict(placement: SignedDocumentSignaturePlacement | None) -> dict[str, Any] | None:
    if placement is None:
        return None
    return {
        **_placement_base_dict(placement),
        "id": placement.id,
        "signed_document_id": placement.signed_document_id,
        "placement_id": placement.placement_id,
        "placement_hash": placement.placement_hash,
        "created_at": placement.created_at,
    }


def create_preview(
    db: Session,
    ctx: OrgContext,
    payload: DocumentPreviewCreate,
) -> DocumentPreview:
    _ensure_org_available(db, ctx)
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
        page_metrics = print_render_service.extract_page_metrics(pdf, payload.document_type.value)
        appearance_policy = signature_appearance_policy(version)
        default_placement = print_render_service.default_signature_placement(
            page_metrics=page_metrics,
            policy=appearance_policy,
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
        pdf_page_metrics=page_metrics,
        signature_policy_hash=signature_policy_hash(version),
        default_signature_placement=default_placement,
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
    _ensure_org_available(db, ctx)
    preview = scoped_query(db, DocumentPreview, ctx).filter(DocumentPreview.id == preview_id).first()
    if preview is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    check_view_permission(ctx, preview.document_type)
    return preview


def _validate_preview_current(db: Session, ctx: OrgContext, preview: DocumentPreview) -> None:
    if preview.status != DocumentPreviewStatus.active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Preview nao esta ativo.")
    if _aware(preview.expires_at) < _now():
        _mark_preview(preview, DocumentPreviewStatus.expired)
        db.commit()
        raise HTTPException(status.HTTP_409_CONFLICT, "Preview expirado. Gere uma nova pre-visualizacao.")
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


def preview_layout(db: Session, ctx: OrgContext, preview_id: uuid.UUID) -> PreviewLayoutResponse:
    preview = get_preview(db, ctx, preview_id)
    _validate_preview_current(db, ctx, preview)
    version = db.get(PrintTemplateVersion, preview.template_version_id)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Template do preview indisponivel.")
    policy = signature_appearance_policy(version)
    default_placement = preview.default_signature_placement or print_render_service.default_signature_placement(
        page_metrics=preview.pdf_page_metrics,
        policy=policy,
    )
    latest = _latest_placement(db, ctx, preview.id)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.preview_inline_viewed,
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": preview.document_type.value, "layout": True},
    )
    db.commit()
    return PreviewLayoutResponse(
        preview_id=preview.id,
        document_type=preview.document_type,
        snapshot_hash=preview.snapshot_hash,
        page_metrics=preview.pdf_page_metrics,
        blocked_areas=policy.get("blocked_areas") or [],
        default_placement=default_placement,
        latest_placement=placement_response_dict(latest) if latest else None,
    )


def read_preview_pdf(
    db: Session,
    ctx: OrgContext,
    preview_id: uuid.UUID,
    *,
    inline: bool = False,
) -> tuple[DocumentPreview, bytes]:
    preview = get_preview(db, ctx, preview_id)
    if inline:
        _validate_preview_current(db, ctx, preview)
    try:
        content = read_pdf(preview.preview_storage_key)
    except DocumentStorageUnavailable as exc:
        raise _storage_http_error(exc)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.preview_inline_viewed if inline else DocumentAccessEventType.preview_downloaded,
        entity_type="document_preview",
        entity_id=preview.id,
        details={"document_type": preview.document_type.value, "classification": preview.classification.value},
    )
    db.commit()
    return preview, content


def list_signature_placements(db: Session, ctx: OrgContext, preview_id: uuid.UUID) -> list[DocumentSignaturePlacement]:
    preview = get_preview(db, ctx, preview_id)
    check_sign_permission(ctx, preview.document_type)
    return (
        scoped_query(db, DocumentSignaturePlacement, ctx)
        .filter(DocumentSignaturePlacement.preview_id == preview.id)
        .order_by(DocumentSignaturePlacement.placement_revision)
        .all()
    )


def confirm_signature_placement(
    db: Session,
    ctx: OrgContext,
    preview_id: uuid.UUID,
    payload: SignaturePlacementCreate,
) -> DocumentSignaturePlacement:
    preview = get_preview(db, ctx, preview_id)
    check_sign_permission(ctx, preview.document_type)
    _validate_preview_current(db, ctx, preview)
    if payload.confirm_snapshot_hash != preview.snapshot_hash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Hash confirmado nao corresponde ao preview.")
    version = db.get(PrintTemplateVersion, preview.template_version_id)
    if version is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Template do preview indisponivel.")
    policy = signature_appearance_policy(version)
    payload_dict = payload.model_dump(mode="json")
    _validate_placement_dict(preview=preview, placement=payload_dict, policy=policy)
    placement = DocumentSignaturePlacement(
        tenant_id=ctx.tenant_id,
        preview_id=preview.id,
        document_type=preview.document_type,
        source_artifact_type=preview.source_artifact_type,
        source_artifact_id=preview.source_artifact_id,
        placement_revision=_next_placement_revision(db, preview),
        page_number=payload.page_number,
        x_points=payload.x_points,
        y_points=payload.y_points,
        width_points=payload.width_points,
        height_points=payload.height_points,
        page_width_points=payload.page_width_points,
        page_height_points=payload.page_height_points,
        coordinate_system=payload.coordinate_system,
        origin=payload.origin,
        template_version_id=preview.template_version_id,
        snapshot_hash=preview.snapshot_hash,
        artifact_fingerprint=preview.artifact_fingerprint,
        signature_policy_hash=preview.signature_policy_hash,
        placement_hash=_placement_hash(payload_dict),
        created_by=ctx.principal.user.id,
    )
    db.add(placement)
    db.flush()
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.placement_confirmed,
        entity_type="document_signature_placement",
        entity_id=placement.id,
        details={
            "document_type": preview.document_type.value,
            "preview_id": str(preview.id),
            "placement_hash": placement.placement_hash,
            "origin": placement.origin.value,
        },
    )
    db.commit()
    db.refresh(placement)
    return placement


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
    _validate_preview_current(db, ctx, preview)
    if body.confirm_snapshot_hash and body.confirm_snapshot_hash != preview.snapshot_hash:
        raise HTTPException(status.HTTP_409_CONFLICT, "Hash confirmado nao corresponde ao preview.")


def _placement_from_request_or_default(
    db: Session,
    ctx: OrgContext,
    preview: DocumentPreview,
    body: SignPreviewRequest,
    template_version: PrintTemplateVersion,
) -> DocumentSignaturePlacement:
    policy = signature_appearance_policy(template_version)
    if body.confirmed_placement_id:
        placement = (
            scoped_query(db, DocumentSignaturePlacement, ctx)
            .filter(
                DocumentSignaturePlacement.id == body.confirmed_placement_id,
                DocumentSignaturePlacement.preview_id == preview.id,
            )
            .first()
        )
        if placement is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Posicao de assinatura nao encontrada.")
        _validate_placement_dict(preview=preview, placement=_placement_base_dict(placement), policy=policy)
        if placement.snapshot_hash != preview.snapshot_hash or placement.artifact_fingerprint != preview.artifact_fingerprint:
            raise HTTPException(status.HTTP_409_CONFLICT, "Posicao de assinatura incompativel com o preview.")
        return placement

    default_placement = preview.default_signature_placement or print_render_service.default_signature_placement(
        page_metrics=preview.pdf_page_metrics,
        policy=policy,
    )
    default_placement = {
        **default_placement,
        "origin": default_placement.get("origin") or SignaturePlacementOrigin.default.value,
    }
    _validate_placement_dict(preview=preview, placement=default_placement, policy=policy)
    placement = DocumentSignaturePlacement(
        tenant_id=ctx.tenant_id,
        preview_id=preview.id,
        document_type=preview.document_type,
        source_artifact_type=preview.source_artifact_type,
        source_artifact_id=preview.source_artifact_id,
        placement_revision=_next_placement_revision(db, preview),
        page_number=int(default_placement["page_number"]),
        x_points=float(default_placement["x_points"]),
        y_points=float(default_placement["y_points"]),
        width_points=float(default_placement["width_points"]),
        height_points=float(default_placement["height_points"]),
        page_width_points=float(default_placement["page_width_points"]),
        page_height_points=float(default_placement["page_height_points"]),
        coordinate_system=SignatureCoordinateSystem.pdf_points_bottom_left,
        origin=SignaturePlacementOrigin(str(default_placement.get("origin") or SignaturePlacementOrigin.default.value)),
        template_version_id=preview.template_version_id,
        snapshot_hash=preview.snapshot_hash,
        artifact_fingerprint=preview.artifact_fingerprint,
        signature_policy_hash=preview.signature_policy_hash,
        placement_hash=_placement_hash(default_placement),
        created_by=ctx.principal.user.id,
    )
    db.add(placement)
    db.flush()
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.placement_confirmed,
        entity_type="document_signature_placement",
        entity_id=placement.id,
        details={
            "document_type": preview.document_type.value,
            "preview_id": str(preview.id),
            "placement_hash": placement.placement_hash,
            "origin": placement.origin.value,
        },
    )
    return placement


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
    placement = _placement_from_request_or_default(db, ctx, preview, body, template_version)
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
        "signature_method": SignatureMethod.internal_electronic_signature.value,
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
            signature_placement=_placement_base_dict(placement),
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
            signature_method=SignatureMethod.internal_electronic_signature,
            signature_provider="wtn_internal",
            visual_signature_present=True,
            auth_context={"method": "authenticated_session", "super_admin_context": ctx.is_super_admin},
            ip=request.client.host if request and request.client else None,
            user_agent=request.headers.get("user-agent") if request else None,
        )
    )
    db.add(
        SignedDocumentSignaturePlacement(
            tenant_id=ctx.tenant_id,
            signed_document_id=signed.id,
            placement_id=placement.id,
            page_number=placement.page_number,
            x_points=placement.x_points,
            y_points=placement.y_points,
            width_points=placement.width_points,
            height_points=placement.height_points,
            page_width_points=placement.page_width_points,
            page_height_points=placement.page_height_points,
            coordinate_system=placement.coordinate_system,
            origin=placement.origin,
            placement_hash=placement.placement_hash,
        )
    )
    _mark_preview(preview, DocumentPreviewStatus.signed)
    log_event(
        db,
        ctx=ctx,
        event_type=DocumentAccessEventType.signed,
        entity_type="signed_document",
        entity_id=signed.id,
        details={
            "document_type": preview.document_type.value,
            "version_number": version_number,
            "signature_method": SignatureMethod.internal_electronic_signature.value,
            "placement_hash": placement.placement_hash,
        },
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


def get_signed_placement(
    db: Session,
    ctx: OrgContext,
    document_id: uuid.UUID,
) -> SignedDocumentSignaturePlacement | None:
    document = get_signed_document(db, ctx, document_id)
    return (
        scoped_query(db, SignedDocumentSignaturePlacement, ctx)
        .filter(SignedDocumentSignaturePlacement.signed_document_id == document.id)
        .first()
    )


def signed_response_dict(db: Session, document: SignedDocument) -> dict[str, Any]:
    status_value = SignedDocumentStatus.obsolete if is_obsolete(db, document) else SignedDocumentStatus.signed
    signature = (
        db.query(DocumentSignature)
        .filter(DocumentSignature.tenant_id == document.tenant_id, DocumentSignature.signed_document_id == document.id)
        .first()
    )
    placement = (
        db.query(SignedDocumentSignaturePlacement)
        .filter(
            SignedDocumentSignaturePlacement.tenant_id == document.tenant_id,
            SignedDocumentSignaturePlacement.signed_document_id == document.id,
        )
        .first()
    )
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
        "signature_method": signature.signature_method if signature else SignatureMethod.internal_electronic_signature,
        "visual_signature_present": signature.visual_signature_present if signature else True,
        "signature_placement": signed_placement_response_dict(placement),
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
        details={
            "document_type": document.document_type.value,
            "version_number": document.version_number,
            "signature_method": SignatureMethod.internal_electronic_signature.value,
        },
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
