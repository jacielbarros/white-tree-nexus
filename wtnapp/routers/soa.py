"""SoA router — consolidação, edição, divergência, versões (Documento Controlado) e exportação."""

import hashlib
import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.classification_access import require_classification_read
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.soa_model import Soa, SoaItem, SoaItemEvent
from wtnapp.schemas.soa_schema import (
    DivergenceField,
    ReconcileRequest,
    SoaApproveRequest,
    SoaItemResponse,
    SoaItemUpdate,
    SoaResponse,
    SoaSummary,
    SoaVersionResponse,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import soa_consolidation_service as consolidation
from wtnapp.services import soa_export_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import Classification, DocStatus, DocType

router = APIRouter(prefix="/soa", tags=["soa"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_soa"))]
manage_dep = Annotated[OrgContext, Depends(require_permission("manage_soa"))]
approve_dep = Annotated[OrgContext, Depends(require_permission("approve_soa"))]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _get_soa(db: Session, ctx: OrgContext) -> Soa:
    soa = scoped_query(db, Soa, ctx).first()
    if soa is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "SoA não encontrada. Consolide a partir do Gap Analysis.")
    return soa


def _item_response(db: Session, item: SoaItem) -> SoaItemResponse:
    divergence = [DivergenceField(**d) for d in consolidation.compute_divergence(db, item)]
    return SoaItemResponse(
        id=item.id,
        ref_code=item.ref_code,
        theme=item.theme.value if item.theme else None,
        name=item.name,
        applicable=item.applicable,
        inclusion_reasons=list(item.inclusion_reasons or []),
        inclusion_note=item.inclusion_note,
        exclusion_justification=item.exclusion_justification,
        implementation_status=item.implementation_status.value if item.implementation_status else None,
        responsible=item.responsible,
        deadline=item.deadline,
        risks_treated=item.risks_treated,
        expected_evidence=item.expected_evidence,
        evidence_refs=item.evidence_refs,
        observations=item.observations,
        gap_assessment_item_id=item.gap_assessment_item_id,
        divergence=divergence,
    )


def _items_ordered(db: Session, soa: Soa) -> list[SoaItem]:
    return (
        db.query(SoaItem)
        .filter(SoaItem.soa_id == soa.id)
        .order_by(SoaItem.ref_code)
        .all()
    )


def _soa_response(db: Session, soa: Soa) -> SoaResponse:
    items = _items_ordered(db, soa)
    responses = [_item_response(db, i) for i in items]
    applicable = sum(1 for i in items if i.applicable)
    divergent = sum(1 for r in responses if r.divergence)
    return SoaResponse(
        id=soa.id,
        draft_status=soa.draft_status.value,
        current_version_id=soa.current_version_id,
        gap_assessment_id=soa.gap_assessment_id,
        items=responses,
        summary=SoaSummary(
            total=len(items),
            applicable=applicable,
            not_applicable=len(items) - applicable,
            divergent=divergent,
        ),
    )


def _version_response(db: Session, v: DocumentVersion) -> SoaVersionResponse:
    snapshot = v.content_snapshot or {}
    return SoaVersionResponse(
        id=v.id,
        identifier=v.identifier,
        version_number=v.version_number,
        status=v.status.value,
        classification=v.classification.value,
        next_review_at=v.next_review_at,
        change_nature=v.change_nature,
        approved_by=v.approved_by,
        is_superseded=cds.is_superseded(db, v.id),
        signed=bool(snapshot.get("signature")),
        created_at=v.created_at,
    )


def _incomplete_refs(items: list[SoaItem]) -> list[str]:
    """Controles que impedem a aprovação (aplicável sem razão; N/A sem justificativa)."""
    out = []
    for i in items:
        if i.applicable and not (i.inclusion_reasons or []):
            out.append(i.ref_code)
        elif not i.applicable and not (i.exclusion_justification or "").strip():
            out.append(i.ref_code)
    return out


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.get("", response_model=SoaResponse)
def get_soa(db: db_dep, ctx: view_dep):
    soa = _get_soa(db, ctx)
    return _soa_response(db, soa)


@router.post("/consolidate", response_model=SoaResponse)
def consolidate_soa(db: db_dep, ctx: manage_dep, request: Request):
    result = consolidation.consolidate(db, ctx.tenant_id)
    soa = _get_soa(db, ctx)
    AuditService.log_from_request(
        request=request, operation="CONSOLIDATE",
        entity_type="soa", entity_id=str(soa.id),
        details={"added": result["added"], "preserved": result["preserved"]},
        actor_user_id=ctx.principal.user.id, tenant_id=ctx.tenant_id,
    )
    return _soa_response(db, soa)


@router.put("/items/{item_id}", response_model=SoaItemResponse)
def update_item(item_id: uuid.UUID, body: SoaItemUpdate, db: db_dep, ctx: manage_dep, request: Request):
    item = scoped_query(db, SoaItem, ctx).filter(SoaItem.id == item_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado.")

    data = body.model_dump(exclude_unset=True)

    # Estado resultante após aplicar o update
    applicable = data.get("applicable", item.applicable)
    reasons = data.get("inclusion_reasons", item.inclusion_reasons or [])
    exclusion = data.get("exclusion_justification", item.exclusion_justification)

    if applicable and not reasons:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Controle aplicável exige ao menos uma razão de inclusão tipada.",
        )
    if not applicable and not (exclusion or "").strip():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Controle não aplicável exige justificativa de exclusão.",
        )

    # Eventos append-only para campos rastreados
    for field in ("applicable", "implementation_status"):
        if field in data:
            old = getattr(item, field)
            new = data[field]
            old_s = old.value if hasattr(old, "value") else (str(old) if old is not None else None)
            new_s = new.value if hasattr(new, "value") else (str(new) if new is not None else None)
            if old_s != new_s:
                db.add(SoaItemEvent(
                    tenant_id=ctx.tenant_id, item_id=item.id, field=field,
                    old_value=old_s, new_value=new_s, actor_id=ctx.principal.user.id,
                ))

    for field, value in data.items():
        if field == "inclusion_reasons" and value is not None:
            value = [r.value if hasattr(r, "value") else r for r in value]
        setattr(item, field, value)
    item.updated_by = ctx.principal.user.id
    db.commit()
    db.refresh(item)

    AuditService.log_from_request(
        request=request, operation="UPDATE",
        entity_type="soa_item", entity_id=str(item.id),
        details={"fields_updated": list(data.keys())},
        actor_user_id=ctx.principal.user.id, tenant_id=ctx.tenant_id,
    )
    return _item_response(db, item)


@router.post("/items/{item_id}/reconcile", response_model=SoaItemResponse)
def reconcile_item(item_id: uuid.UUID, body: ReconcileRequest, db: db_dep, ctx: manage_dep, request: Request):
    item = scoped_query(db, SoaItem, ctx).filter(SoaItem.id == item_id).first()
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item não encontrado.")

    applied = consolidation.reconcile(db, item, body.fields)
    for field in applied:
        db.add(SoaItemEvent(
            tenant_id=ctx.tenant_id, item_id=item.id, field=field,
            old_value=None, new_value="reconciled", actor_id=ctx.principal.user.id,
        ))
    item.updated_by = ctx.principal.user.id
    db.commit()
    db.refresh(item)

    AuditService.log_from_request(
        request=request, operation="RECONCILE",
        entity_type="soa_item", entity_id=str(item.id),
        details={"fields": applied}, actor_user_id=ctx.principal.user.id, tenant_id=ctx.tenant_id,
    )
    return _item_response(db, item)


@router.get("/divergences", response_model=list[SoaItemResponse])
def list_divergences(db: db_dep, ctx: view_dep):
    soa = _get_soa(db, ctx)
    out = []
    for item in _items_ordered(db, soa):
        resp = _item_response(db, item)
        if resp.divergence:
            out.append(resp)
    return out


@router.post("/submit-review")
def submit_review(db: db_dep, ctx: manage_dep, request: Request):
    soa = _get_soa(db, ctx)
    result = cds.submit_review(db, soa)
    AuditService.log_from_request(
        request=request, operation="SUBMIT_REVIEW",
        entity_type="soa", entity_id=str(soa.id),
        actor_user_id=ctx.principal.user.id, tenant_id=ctx.tenant_id,
    )
    return {"status": result.draft_status.value}


@router.post("/approve", response_model=SoaVersionResponse, status_code=201)
def approve_soa(body: SoaApproveRequest, db: db_dep, ctx: approve_dep, request: Request):
    soa = _get_soa(db, ctx)

    if soa.draft_status != DocStatus.in_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Envie a SoA para revisão antes de aprovar.")

    items = _items_ordered(db, soa)
    incomplete = _incomplete_refs(items)
    if incomplete:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            {"detail": "SoA incompleta: há controles sem razão de inclusão ou justificativa de exclusão.",
             "incomplete": incomplete},
        )

    item_snapshots = [
        {
            "ref_code": i.ref_code,
            "theme": i.theme.value if i.theme else None,
            "name": i.name,
            "applicable": i.applicable,
            "inclusion_reasons": list(i.inclusion_reasons or []),
            "inclusion_note": i.inclusion_note,
            "exclusion_justification": i.exclusion_justification,
            "implementation_status": i.implementation_status.value if i.implementation_status else None,
            "responsible": i.responsible,
            "deadline": i.deadline.isoformat() if i.deadline else None,
            "risks_treated": i.risks_treated,
            "expected_evidence": i.expected_evidence,
            "evidence_refs": i.evidence_refs,
            "observations": i.observations,
        }
        for i in items
    ]
    applicable = sum(1 for i in items if i.applicable)
    summary = {"total": len(items), "applicable": applicable, "not_applicable": len(items) - applicable}

    signature = None
    if body.sign:
        canonical = json.dumps(item_snapshots, sort_keys=True, ensure_ascii=False)
        content_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        from datetime import datetime, timezone
        signature = {
            "signer_user_id": str(ctx.principal.user.id),
            "signer_name": ctx.principal.user.full_name or str(ctx.principal.user.id),
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": content_hash,
            "algorithm": "sha256",
            "level": "advanced",
        }

    def _snapshot():
        snap = {"items": item_snapshots, "summary": summary, "gap_assessment_id": str(soa.gap_assessment_id) if soa.gap_assessment_id else None}
        if signature:
            snap["signature"] = signature
        return snap

    version = cds.approve_document(
        db=db, artifact=soa, doc_type=DocType.soa, actor_id=ctx.principal.user.id,
        classification=Classification(body.classification), next_review_at=body.next_review_at,
        change_nature=body.change_nature, snapshot_factory=_snapshot,
    )
    AuditService.log_from_request(
        request=request, operation="APPROVE_SOA",
        entity_type="soa", entity_id=str(soa.id),
        details={"version_number": version.version_number, "signed": bool(signature)},
        actor_user_id=ctx.principal.user.id, tenant_id=ctx.tenant_id,
    )
    return _version_response(db, version)


@router.get("/versions", response_model=list[SoaVersionResponse])
def list_versions(db: db_dep, ctx: view_dep):
    soa = _get_soa(db, ctx)
    versions = cds.list_versions(db, ctx.tenant_id, DocType.soa, soa.id)
    return [_version_response(db, v) for v in versions]


@router.get("/versions/{version_id}/export")
def export_version(version_id: uuid.UUID, db: db_dep, ctx: view_dep, request: Request):
    soa = _get_soa(db, ctx)
    version = (
        db.query(DocumentVersion)
        .filter(
            DocumentVersion.id == version_id,
            DocumentVersion.tenant_id == ctx.tenant_id,
            DocumentVersion.document_type == DocType.soa,
            DocumentVersion.document_id == soa.id,
        )
        .first()
    )
    if version is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versão não encontrada.")

    # Acesso por classificação (complementar ao RBAC)
    require_classification_read(db, ctx, version.classification)

    pdf = soa_export_service.render_pdf(version)
    AuditService.log_from_request(
        request=request, operation="EXPORT",
        entity_type="soa_version", entity_id=str(version.id),
        details={"version_number": version.version_number}, actor_user_id=ctx.principal.user.id,
        tenant_id=ctx.tenant_id,
    )
    filename = f"SoA-v{version.version_number}.pdf"
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
