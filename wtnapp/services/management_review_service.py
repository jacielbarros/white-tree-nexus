"""Análise Crítica pela Direção (9.3) como Documento Controlado — Feature 015.

Coleção (uma por reunião). Reusa `controlled_document_service` (versões + aprovação) e
`signature_service` (assinatura opcional). Gate duro de completude na aprovação (FR-022).
"""

import hashlib
import json
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.management_review_model import ManagementReview
from wtnapp.services import controlled_document_service as cds
from wtnapp.settings import Classification, DocStatus, DocType


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _non_empty(value: dict) -> bool:
    return any(v not in (None, "", [], {}) for v in (value or {}).values())


def is_complete(review: ManagementReview) -> bool:
    """Gate duro (FR-022): entradas e saídas/decisões obrigatórias preenchidas."""
    return _non_empty(review.inputs) and _non_empty(review.outputs)


def get_review(db: Session, ctx: OrgContext, review_id: uuid.UUID) -> ManagementReview:
    review = scoped_query(db, ManagementReview, ctx).filter(ManagementReview.id == review_id).first()
    if review is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return review


def create_review(db: Session, ctx: OrgContext, data) -> ManagementReview:
    review = ManagementReview(
        tenant_id=ctx.tenant_id, title=data.title, review_date=data.review_date,
        inputs=data.inputs or {}, outputs=data.outputs or {}, created_by=ctx.principal.user.id,
    )
    db.add(review)
    db.flush()
    return review


def update_review(db: Session, ctx: OrgContext, review: ManagementReview, data) -> ManagementReview:
    review.title = data.title
    review.review_date = data.review_date
    review.inputs = data.inputs or {}
    review.outputs = data.outputs or {}
    return review


def build_snapshot(review: ManagementReview) -> dict:
    return {
        "title": review.title,
        "review_date": review.review_date.isoformat() if review.review_date else None,
        "inputs": dict(review.inputs or {}),
        "outputs": dict(review.outputs or {}),
    }


def submit_review(db: Session, ctx: OrgContext, review: ManagementReview) -> ManagementReview:
    if not is_complete(review):
        raise HTTPException(status.HTTP_409_CONFLICT, "Análise crítica incompleta: preencha entradas e saídas/decisões.")
    return cds.submit_review(db, review)


def approve(db: Session, ctx: OrgContext, review: ManagementReview, *, sign: bool, classification: Classification, next_review_at, change_nature: str) -> DocumentVersion:
    if review.draft_status != DocStatus.in_review:
        raise HTTPException(status.HTTP_409_CONFLICT, "Envie a ata para revisão antes de aprovar.")
    if not is_complete(review):
        raise HTTPException(status.HTTP_409_CONFLICT, "Análise crítica incompleta: preencha entradas e saídas/decisões.")
    snapshot = build_snapshot(review)

    signature = None
    if sign:
        canonical = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
        signature = {
            "signer_user_id": str(ctx.principal.user.id),
            "signer_name": ctx.principal.user.full_name or str(ctx.principal.user.id),
            "signed_at": _now().isoformat(),
            "content_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            "algorithm": "sha256",
            "level": "advanced",
        }

    def _snapshot():
        snap = dict(snapshot)
        if signature:
            snap["signature"] = signature
        return snap

    return cds.approve_document(
        db=db, artifact=review, doc_type=DocType.management_review, actor_id=ctx.principal.user.id,
        classification=classification, next_review_at=next_review_at, change_nature=change_nature,
        snapshot_factory=_snapshot,
    )
