"""Melhorias/oportunidades (10.1) — Feature 015. CRUD + status; código IMP-####.

A referência de realimentação (`target_type`/`target_id`) é **read-only**: não cria nem altera o
artefato consumido.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.improvement_model import Improvement, ImprovementEvent
from wtnapp.settings import AuditOutcome, IMPROVEMENT_CODE_PREFIX


def _now() -> datetime:
    return datetime.now(timezone.utc)


def log_event(db: Session, *, ctx: OrgContext, improvement_id, event_type: str, outcome=AuditOutcome.success, details=None):
    db.add(ImprovementEvent(
        tenant_id=ctx.tenant_id, improvement_id=improvement_id, event_type=event_type,
        outcome=outcome.value, actor_id=ctx.principal.user.id, details=details or {},
    ))


def _next_code(db: Session, ctx: OrgContext) -> str:
    count = scoped_query(db, Improvement, ctx).count()
    return f"{IMPROVEMENT_CODE_PREFIX}{count + 1:04d}"


def _validate_target(db: Session, ctx: OrgContext, target_type, target_id) -> None:
    if target_type is None and target_id is None:
        return
    if target_type is None or target_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe tipo e id do alvo, ou nenhum.")
    from wtnapp.services.evidence_service import target_exists  # noqa: PLC0415

    if not target_exists(db, ctx, target_type, target_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")


def get_improvement(db: Session, ctx: OrgContext, improvement_id: uuid.UUID) -> Improvement:
    imp = scoped_query(db, Improvement, ctx).filter(Improvement.id == improvement_id).first()
    if imp is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso nao encontrado.")
    return imp


def list_improvements(db: Session, ctx: OrgContext, *, status_filter=None, origin=None) -> list[Improvement]:
    query = scoped_query(db, Improvement, ctx)
    if status_filter is not None:
        query = query.filter(Improvement.status == status_filter)
    if origin is not None:
        query = query.filter(Improvement.origin == origin)
    return query.order_by(Improvement.created_at.desc()).all()


def create_improvement(db: Session, ctx: OrgContext, data) -> Improvement:
    _validate_target(db, ctx, data.target_type, data.target_id)
    imp = Improvement(
        tenant_id=ctx.tenant_id, code=_next_code(db, ctx), title=data.title, description=data.description,
        origin=data.origin, source_ref=data.source_ref, status=data.status,
        target_type=data.target_type, target_id=data.target_id, created_by=ctx.principal.user.id,
    )
    db.add(imp)
    db.flush()
    log_event(db, ctx=ctx, improvement_id=imp.id, event_type="created")
    return imp


def update_improvement(db: Session, ctx: OrgContext, imp: Improvement, data) -> Improvement:
    _validate_target(db, ctx, data.target_type, data.target_id)
    imp.title = data.title
    imp.description = data.description
    imp.origin = data.origin
    imp.source_ref = data.source_ref
    imp.status = data.status
    imp.target_type = data.target_type
    imp.target_id = data.target_id
    log_event(db, ctx=ctx, improvement_id=imp.id, event_type="updated", details={"status": data.status.value})
    return imp
