"""Deterministic source-artifact snapshots for printable documents."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.context_analysis_model import ContextAnalysis, ContextIssue
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.gap_seed_model import GapSeedItem
from wtnapp.models.organization_model import Organization
from wtnapp.models.scope_model import ScopeItem, ScopeStatement
from wtnapp.models.soa_model import Soa, SoaItem
from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement
from wtnapp.services.gap_metrics_service import compute_dashboard, list_gaps
from wtnapp.services.print_template_service import sha256_canonical
from wtnapp.settings import PrintableDocumentType


@dataclass(frozen=True)
class SnapshotBundle:
    document_type: PrintableDocumentType
    source_artifact_type: str
    source_artifact_id: uuid.UUID | None
    source_document_version_id: uuid.UUID | None
    source_payload: dict[str, Any]
    snapshot: dict[str, Any]
    variables: dict[str, Any]
    artifact_fingerprint: str
    snapshot_hash: str


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


def _date_iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _org_name(db: Session, ctx: OrgContext) -> str:
    org = db.get(Organization, ctx.tenant_id)
    return org.name if org else str(ctx.tenant_id)


def _missing(missing_sections: list[str]) -> None:
    raise HTTPException(
        status.HTTP_422_UNPROCESSABLE_ENTITY,
        {
            "detail": "Dados minimos ausentes para gerar o documento.",
            "missing_sections": missing_sections,
        },
    )


def _base_variables(
    *,
    db: Session,
    ctx: OrgContext,
    document_title: str,
    classification: str,
    source_reference: str | None,
) -> dict[str, Any]:
    return {
        "organization_name": _org_name(db, ctx),
        "document_title": document_title,
        "generated_at": _now_iso(),
        "classification": classification,
        "document_status": "Preview",
        "source_reference": source_reference,
    }


def _wrap_bundle(
    *,
    db: Session,
    ctx: OrgContext,
    document_type: PrintableDocumentType,
    source_artifact_type: str,
    source_artifact_id: uuid.UUID | None,
    source_document_version_id: uuid.UUID | None,
    source_payload: dict[str, Any],
    document_title: str,
    classification: str,
    source_reference: str | None = None,
) -> SnapshotBundle:
    artifact_fingerprint = sha256_canonical(source_payload)
    variables = _base_variables(
        db=db,
        ctx=ctx,
        document_title=document_title,
        classification=classification,
        source_reference=source_reference,
    )
    snapshot = {
        "document_type": document_type.value,
        "tenant_id": str(ctx.tenant_id),
        "source": source_payload,
        "variables": variables,
    }
    return SnapshotBundle(
        document_type=document_type,
        source_artifact_type=source_artifact_type,
        source_artifact_id=source_artifact_id,
        source_document_version_id=source_document_version_id,
        source_payload=source_payload,
        snapshot=snapshot,
        variables=variables,
        artifact_fingerprint=artifact_fingerprint,
        snapshot_hash=sha256_canonical(snapshot),
    )


def _context_snapshot(db: Session, ctx: OrgContext, classification: str) -> SnapshotBundle:
    diagnostic = scoped_query(db, Diagnostic, ctx).first()
    analysis = scoped_query(db, ContextAnalysis, ctx).first()
    stakeholder_map = scoped_query(db, StakeholderMap, ctx).first()
    scope = scoped_query(db, ScopeStatement, ctx).first()
    missing: list[str] = []
    if diagnostic is None or not (diagnostic.sections or {}):
        missing.append("diagnostic")
    if analysis is None:
        missing.append("analysis")
    if stakeholder_map is None:
        missing.append("stakeholders")
    if scope is None:
        missing.append("scope")
    if missing:
        _missing(missing)

    stakeholders = (
        scoped_query(db, Stakeholder, ctx)
        .filter(Stakeholder.map_id == stakeholder_map.id)
        .order_by(Stakeholder.name)
        .all()
    )
    scope_items = (
        scoped_query(db, ScopeItem, ctx)
        .filter(ScopeItem.scope_id == scope.id)
        .order_by(ScopeItem.kind, ScopeItem.description)
        .all()
    )
    if not stakeholders:
        _missing(["stakeholders"])
    if not scope_items:
        _missing(["scope"])

    stakeholder_rows = []
    for stakeholder in stakeholders:
        requirements = (
            scoped_query(db, StakeholderRequirement, ctx)
            .filter(StakeholderRequirement.stakeholder_id == stakeholder.id)
            .order_by(StakeholderRequirement.type)
            .all()
        )
        stakeholder_rows.append(
            {
                "name": stakeholder.name,
                "type": stakeholder.type,
                "power": _enum_value(stakeholder.power),
                "interest": _enum_value(stakeholder.interest),
                "strategy": _enum_value(stakeholder.strategy),
                "requirements": [
                    {
                        "type": _enum_value(req.type),
                        "description": req.description,
                        "how_addressed": req.how_addressed,
                    }
                    for req in requirements
                ],
            }
        )

    issues = (
        scoped_query(db, ContextIssue, ctx)
        .filter(ContextIssue.analysis_id == analysis.id)
        .order_by(ContextIssue.origin, ContextIssue.category, ContextIssue.description)
        .all()
    )
    source = {
        "diagnostic": {
            "status": _enum_value(diagnostic.status),
            "sections": diagnostic.sections,
            "updated_at": _date_iso(diagnostic.updated_at),
        },
        "analysis": {
            "id": str(analysis.id),
            "intended_outcomes": analysis.intended_outcomes,
            "methodology": analysis.methodology,
            "draft_status": _enum_value(analysis.draft_status),
            "current_version_id": str(analysis.current_version_id) if analysis.current_version_id else None,
            "issues": [
                {
                    "origin": _enum_value(issue.origin),
                    "framework": _enum_value(issue.framework),
                    "category": issue.category,
                    "description": issue.description,
                    "impact": _enum_value(issue.impact),
                }
                for issue in issues
            ],
        },
        "stakeholders": stakeholder_rows,
        "scope": {
            "id": str(scope.id),
            "interfaces_dependencies": scope.interfaces_dependencies,
            "items": [
                {
                    "kind": _enum_value(item.kind),
                    "description": item.description,
                    "justification": item.justification,
                }
                for item in scope_items
            ],
            "current_version_id": str(scope.current_version_id) if scope.current_version_id else None,
        },
    }
    return _wrap_bundle(
        db=db,
        ctx=ctx,
        document_type=PrintableDocumentType.context_report,
        source_artifact_type="context_report",
        source_artifact_id=analysis.id,
        source_document_version_id=None,
        source_payload=source,
        document_title="Relatorio de Contexto da Organizacao",
        classification=classification,
        source_reference="Clausula 4",
    )


def _gap_item_snapshot(db: Session, item: GapAssessmentItem) -> dict[str, Any]:
    cat = db.get(GapCatalogItem, item.catalog_item_id)
    seed = db.get(GapSeedItem, cat.seed_item_id) if cat and cat.seed_item_id else None
    return {
        "id": str(item.id),
        "ref_code": cat.ref_code if cat else "",
        "dimension": _enum_value(cat.dimension) if cat else "",
        "theme": _enum_value(cat.theme) if cat and cat.theme else None,
        "name": cat.name if cat else "",
        "objective": cat.objective if cat else "",
        "guidance": {
            "reference": seed.referencia if seed else "",
            "how_to_evaluate": list(seed.como_avaliar or []) if seed else [],
            "expected_evidence": list(seed.evidencias_esperadas or []) if seed else [],
            "note": seed.nota if seed else None,
        },
        "status": _enum_value(item.status),
        "priority": _enum_value(item.priority),
        "findings": item.findings,
        "actions": item.actions,
        "responsible": item.responsible,
        "deadline": _date_iso(item.deadline),
        "evidence_ref": item.evidence_ref,
        "notes": item.notes,
        "maturity_level": item.maturity_level,
        "effort_estimate": item.effort_estimate,
        "soa_ref": item.soa_ref,
        "updated_at": _date_iso(item.updated_at),
    }


def _gap_snapshot(db: Session, ctx: OrgContext, classification: str) -> SnapshotBundle:
    assessment = scoped_query(db, GapAssessment, ctx).first()
    if assessment is None:
        _missing(["gap_assessment"])
    items = (
        scoped_query(db, GapAssessmentItem, ctx)
        .filter(GapAssessmentItem.assessment_id == assessment.id)
        .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
        .order_by(GapCatalogItem.order)
        .all()
    )
    if not items:
        _missing(["gap_items"])
    dashboard = compute_dashboard(db, ctx.tenant_id, assessment.id)
    gaps = list_gaps(db, ctx.tenant_id, assessment.id, "priority")
    source = {
        "assessment": {
            "id": str(assessment.id),
            "draft_status": _enum_value(assessment.draft_status),
            "current_version_id": str(assessment.current_version_id) if assessment.current_version_id else None,
            "dashboard": dashboard,
        },
        "items": [_gap_item_snapshot(db, item) for item in items],
        "prioritized_gaps": [_gap_item_snapshot(db, item) for item in gaps],
    }
    return _wrap_bundle(
        db=db,
        ctx=ctx,
        document_type=PrintableDocumentType.gap_report,
        source_artifact_type="gap_assessment",
        source_artifact_id=assessment.id,
        source_document_version_id=assessment.current_version_id,
        source_payload=source,
        document_title="Relatorio de Gap Analysis",
        classification=classification,
        source_reference="Gap Analysis",
    )


def _soa_snapshot(db: Session, ctx: OrgContext, classification: str) -> SnapshotBundle:
    soa = scoped_query(db, Soa, ctx).first()
    if soa is None:
        _missing(["soa"])
    items = (
        scoped_query(db, SoaItem, ctx)
        .filter(SoaItem.soa_id == soa.id)
        .order_by(SoaItem.ref_code)
        .all()
    )
    if not items:
        _missing(["soa_items"])
    applicable = sum(1 for item in items if item.applicable)
    source = {
        "soa": {
            "id": str(soa.id),
            "draft_status": _enum_value(soa.draft_status),
            "current_version_id": str(soa.current_version_id) if soa.current_version_id else None,
            "gap_assessment_id": str(soa.gap_assessment_id) if soa.gap_assessment_id else None,
        },
        "summary": {
            "total": len(items),
            "applicable": applicable,
            "not_applicable": len(items) - applicable,
        },
        "items": [
            {
                "id": str(item.id),
                "ref_code": item.ref_code,
                "theme": _enum_value(item.theme),
                "name": item.name,
                "applicable": item.applicable,
                "inclusion_reasons": list(item.inclusion_reasons or []),
                "inclusion_note": item.inclusion_note,
                "exclusion_justification": item.exclusion_justification,
                "implementation_status": _enum_value(item.implementation_status),
                "responsible": item.responsible,
                "deadline": _date_iso(item.deadline),
                "risks_treated": item.risks_treated,
                "expected_evidence": item.expected_evidence,
                "evidence_refs": item.evidence_refs,
                "observations": item.observations,
            }
            for item in items
        ],
    }
    return _wrap_bundle(
        db=db,
        ctx=ctx,
        document_type=PrintableDocumentType.soa_report,
        source_artifact_type="soa",
        source_artifact_id=soa.id,
        source_document_version_id=soa.current_version_id,
        source_payload=source,
        document_title="Declaracao de Aplicabilidade (SoA)",
        classification=classification,
        source_reference="SoA",
    )


def build_snapshot(
    db: Session,
    ctx: OrgContext,
    document_type: PrintableDocumentType,
    classification: str,
) -> SnapshotBundle:
    if document_type == PrintableDocumentType.context_report:
        return _context_snapshot(db, ctx, classification)
    if document_type == PrintableDocumentType.gap_report:
        return _gap_snapshot(db, ctx, classification)
    if document_type == PrintableDocumentType.soa_report:
        return _soa_snapshot(db, ctx, classification)
    raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tipo documental nao suportado no MVP.")
