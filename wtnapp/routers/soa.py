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
from wtnapp.models.risk_model import RiskPlan
from wtnapp.models.soa_model import Soa, SoaItem, SoaItemEvent
from wtnapp.schemas.soa_schema import (
    DivergenceField,
    ReconcileRequest,
    RiskLink,
    SoaApproveRequest,
    SoaItemResponse,
    SoaItemUpdate,
    SoaReadiness,
    SoaResponse,
    SoaSummary,
    SoaVersionResponse,
)
from wtnapp.services import controlled_document_service as cds
from wtnapp.services import soa_consolidation_service as consolidation
from wtnapp.services import soa_export_service
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import SOA_KIND_LABELS, Classification, DocStatus, DocType, SoaKind

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


def _is_incomplete(item: SoaItem) -> bool:
    if item.applicable:
        return not (item.inclusion_reasons or [])
    return not (item.exclusion_justification or "").strip()


def _item_response(db: Session, item: SoaItem, feed_index: dict | None = None) -> SoaItemResponse:
    if feed_index is None:
        feed_index = consolidation.build_feed_index(db, item.tenant_id)
    divergence = [DivergenceField(**d) for d in consolidation.compute_divergence(db, item)]
    divergence += [DivergenceField(**d) for d in consolidation.compute_risk_divergence(db, item, feed_index)]
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
        risk_links=[RiskLink(**rl) for rl in (item.risk_links or [])],
        origin=consolidation.derive_origin(item),
        incomplete=_is_incomplete(item),
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


def _has_approved_risk_plan(db: Session, tenant_id) -> bool:
    """Existe Plano de Tratamento de Riscos com versão aprovada vigente (in-force)?"""
    plan = db.query(RiskPlan).filter_by(tenant_id=tenant_id).first()
    return bool(plan and plan.current_version_id)


def _readiness(db: Session, soa: Soa, items: list[SoaItem], out_of_scope: list[str]) -> SoaReadiness:
    approved = _has_approved_risk_plan(db, soa.tenant_id)
    kind = SoaKind.normative if approved else SoaKind.pre_soa
    pending: list[str] = []
    if not approved:
        pending.append("Plano de Tratamento de Riscos ainda não aprovado.")
    incomplete = [i.ref_code for i in items if _is_incomplete(i)]
    if incomplete:
        pending.append(f"{len(incomplete)} controle(s) sem razão de inclusão ou justificativa de exclusão.")
    return SoaReadiness(
        kind=kind.value,
        risk_plan_approved=approved,
        pending_for_normative=pending,
        out_of_scope_risk_notices=out_of_scope,
    )


def _soa_response(db: Session, soa: Soa) -> SoaResponse:
    items = _items_ordered(db, soa)
    feed_index = consolidation.build_feed_index(db, soa.tenant_id)
    responses = [_item_response(db, i, feed_index) for i in items]
    applicable = sum(1 for i in items if i.applicable)
    divergent = sum(1 for r in responses if r.divergence)
    risk_divergent = sum(1 for r in responses if any(d.source == "risk" for d in r.divergence))
    incomplete = sum(1 for r in responses if r.incomplete)
    # Controles tratados por risco fora do Anexo A da SoA (notice, sem criar item).
    catalog_ids = {i.catalog_item_id for i in items}
    out_of_scope = [
        e.get("ref_code") or str(gid)
        for gid, e in feed_index.items()
        if gid not in catalog_ids
    ]
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
            risk_divergent=risk_divergent,
            incomplete=incomplete,
        ),
        readiness=_readiness(db, soa, items, out_of_scope),
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
        kind=snapshot.get("soa_kind", SoaKind.pre_soa.value),
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
        details={
            "added": result["added"], "preserved": result["preserved"],
            "risk_applied": result.get("risk_applied", 0),
            "out_of_scope": result.get("out_of_scope", []),
        },
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

    applied = consolidation.reconcile(db, item, body.fields, source=body.source)
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
            "risk_links": list(i.risk_links or []),
            "origin": consolidation.derive_origin(i),
            "expected_evidence": i.expected_evidence,
            "evidence_refs": i.evidence_refs,
            "observations": i.observations,
        }
        for i in items
    ]
    applicable = sum(1 for i in items if i.applicable)
    summary = {"total": len(items), "applicable": applicable, "not_applicable": len(items) - applicable}

    # Gate duro (Feature 013): rótulo da versão conforme exista Plano de Tratamento aprovado vigente.
    risk_plan = db.query(RiskPlan).filter_by(tenant_id=ctx.tenant_id).first()
    soa_kind = SoaKind.normative if (risk_plan and risk_plan.current_version_id) else SoaKind.pre_soa
    risk_plan_version_number = None
    if risk_plan and risk_plan.current_version_id:
        rp_version = db.query(DocumentVersion).filter_by(id=risk_plan.current_version_id).first()
        risk_plan_version_number = rp_version.version_number if rp_version else None

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
        snap = {
            "items": item_snapshots, "summary": summary,
            "gap_assessment_id": str(soa.gap_assessment_id) if soa.gap_assessment_id else None,
            "soa_kind": soa_kind.value,
            "risk_plan_version_number": risk_plan_version_number,
        }
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
        details={"version_number": version.version_number, "signed": bool(signature),
                 "soa_kind": soa_kind.value},
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
