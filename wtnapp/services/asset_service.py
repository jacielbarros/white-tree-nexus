"""Regras de negócio do módulo de Ativos / Processos / Escopo (Feature 011).

Geração de código, cálculo de criticidade, derivação da situação de revisão, validações
condicionais de escopo, verificação de duplicidade/membros e trilha de histórico append-only.
"""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.asset_item_model import AssetItem, AssetItemEvent
from wtnapp.models.membership_model import Membership
from wtnapp.schemas.asset_schema import AssetItemResponse
from wtnapp.settings import (
    ASSET_CODE_PREFIXES,
    CIA_ORDER,
    AssetItemEventType,
    AssetRecordStatus,
    AssetReviewStatus,
    AssetScopeStatus,
    AssetType,
    CiaLevel,
    MembershipStatus,
    ASSET_REVIEW_DUE_SOON_DAYS,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


# --- Criticidade -----------------------------------------------------------------

def compute_criticality(
    confidentiality: CiaLevel | None,
    integrity: CiaLevel | None,
    availability: CiaLevel | None,
) -> CiaLevel | None:
    """Maior valor entre C, I e A. Retorna None se algum dos três faltar."""
    values = [confidentiality, integrity, availability]
    if any(v is None for v in values):
        return None
    return max(values, key=lambda v: CIA_ORDER.index(v))


# --- Situação de revisão (derivada) ---------------------------------------------

def derive_review_status(next_review_at: datetime | None, *, now: datetime | None = None) -> AssetReviewStatus:
    next_review_at = _aware(next_review_at)
    if next_review_at is None:
        return AssetReviewStatus.undefined
    now = now or _now()
    if next_review_at < now:
        return AssetReviewStatus.overdue
    delta_days = (next_review_at - now).days
    if delta_days <= ASSET_REVIEW_DUE_SOON_DAYS:
        return AssetReviewStatus.due_soon
    return AssetReviewStatus.up_to_date


# --- Código interno --------------------------------------------------------------

def generate_code(db: Session, tenant_id: uuid.UUID, item_type: AssetType) -> str:
    """Prefixo do tipo + sequência por tipo dentro da org (ex.: ATV-0001). Imutável."""
    prefix = ASSET_CODE_PREFIXES[item_type]
    rows = (
        db.query(AssetItem.code)
        .filter(AssetItem.tenant_id == tenant_id, AssetItem.item_type == item_type)
        .all()
    )
    max_n = 0
    for (code,) in rows:
        try:
            n = int(str(code).rsplit("-", 1)[1])
        except (ValueError, IndexError):
            continue
        max_n = max(max_n, n)
    return f"{prefix}-{max_n + 1:04d}"


# --- Validações ------------------------------------------------------------------

def _cia_complete(c: CiaLevel | None, i: CiaLevel | None, a: CiaLevel | None) -> bool:
    return c is not None and i is not None and a is not None


def pending_fields(item: AssetItem) -> list[str]:
    pending: list[str] = []
    if item.responsible_user_id is None:
        pending.append("responsible")
    if not _cia_complete(item.confidentiality, item.integrity, item.availability):
        pending.append("cia")
    return pending


def validate_scope(payload, *, responsible_user_id, c, i, a, scope_justification) -> None:
    """Regras condicionais de escopo (FR-009/FR-010/FR-011)."""
    scope = payload.scope_status
    if scope == AssetScopeStatus.in_scope:
        missing: list[str] = []
        if responsible_user_id is None:
            missing.append("responsável")
        if not _cia_complete(c, i, a):
            missing.append("classificação CIA (Confidencialidade, Integridade e Disponibilidade)")
        if missing:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Item dentro do escopo exige: {', '.join(missing)}.",
            )
    elif scope == AssetScopeStatus.out_of_scope:
        if not (scope_justification or "").strip():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Item fora do escopo exige justificativa de exclusão.",
            )


def validate_members(db: Session, ctx: OrgContext, user_ids: list[uuid.UUID | None]) -> None:
    """Responsável/dono/custodiante devem ser membros ativos do tenant."""
    ids = {uid for uid in user_ids if uid is not None}
    if not ids:
        return
    found = {
        m.user_id
        for m in db.query(Membership).filter(
            Membership.tenant_id == ctx.tenant_id,
            Membership.user_id.in_(ids),
            Membership.status == MembershipStatus.active,
        )
    }
    missing = ids - found
    if missing:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Responsável/dono/custodiante deve ser um membro ativo da organização.",
        )


def validate_related_items(db: Session, ctx: OrgContext, related_ids: list[uuid.UUID | None]) -> None:
    """`related_system/process/supplier` devem pertencer ao tenant ativo."""
    ids = {rid for rid in related_ids if rid is not None}
    if not ids:
        return
    found = {
        row.id
        for row in scoped_query(db, AssetItem, ctx).filter(AssetItem.id.in_(ids)).all()
    }
    if ids - found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")


def check_duplicate(
    db: Session,
    ctx: OrgContext,
    *,
    name: str,
    item_type: AssetType,
    allow_duplicate: bool,
    reason: str | None,
    exclude_id: uuid.UUID | None = None,
) -> None:
    """Bloqueia nome repetido no mesmo tipo, salvo allow_duplicate + justificativa (FR-033)."""
    query = scoped_query(db, AssetItem, ctx).filter(
        AssetItem.item_type == item_type,
        AssetItem.name == name,
    )
    if exclude_id is not None:
        query = query.filter(AssetItem.id != exclude_id)
    exists = db.query(query.exists()).scalar()
    if exists and not (allow_duplicate and (reason or "").strip()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Já existe um item com este nome neste tipo. Use um identificador distinto ou justifique a duplicidade.",
        )


# --- Histórico append-only -------------------------------------------------------

def log_event(
    db: Session,
    ctx: OrgContext,
    item_id: uuid.UUID,
    event_type: AssetItemEventType,
    *,
    field_name: str | None = None,
    old_value: str | None = None,
    new_value: str | None = None,
    reason: str | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        AssetItemEvent(
            tenant_id=ctx.tenant_id,
            item_id=item_id,
            event_type=event_type.value,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            actor_id=ctx.principal.user.id,
            details=details or {},
        )
    )


def _val(v) -> str | None:
    if v is None:
        return None
    if hasattr(v, "value"):
        return str(v.value)
    return str(v)


def snapshot(item: AssetItem) -> dict:
    """Estado relevante para diffing de histórico."""
    return {
        "scope_status": item.scope_status,
        "criticality": item.criticality,
        "responsible_user_id": item.responsible_user_id,
        "name": item.name,
        "record_status": item.record_status,
    }


def diff_and_log(db: Session, ctx: OrgContext, before: dict, item: AssetItem, reason: str | None) -> None:
    """Compara estado anterior×novo e grava eventos. Exige justificativa nas mudanças críticas."""
    changed_other = False

    # Escopo
    if before["scope_status"] != item.scope_status:
        if item.scope_status == AssetScopeStatus.out_of_scope:
            if not (reason or "").strip():
                raise HTTPException(
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                    "Exclusão de escopo exige justificativa.",
                )
            log_event(
                db, ctx, item.id, AssetItemEventType.scope_exclusion,
                field_name="scope_status", old_value=_val(before["scope_status"]),
                new_value=_val(item.scope_status), reason=reason,
            )
        else:
            log_event(
                db, ctx, item.id, AssetItemEventType.scope_change,
                field_name="scope_status", old_value=_val(before["scope_status"]),
                new_value=_val(item.scope_status), reason=reason,
            )

    # Criticidade
    if before["criticality"] != item.criticality:
        if not (reason or "").strip():
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Mudança de criticidade exige justificativa.",
            )
        log_event(
            db, ctx, item.id, AssetItemEventType.criticality_change,
            field_name="criticality", old_value=_val(before["criticality"]),
            new_value=_val(item.criticality), reason=reason,
        )

    # Responsável
    if before["responsible_user_id"] != item.responsible_user_id:
        log_event(
            db, ctx, item.id, AssetItemEventType.responsible_change,
            field_name="responsible_user_id", old_value=_val(before["responsible_user_id"]),
            new_value=_val(item.responsible_user_id), reason=reason,
        )

    # Demais campos (nome etc.)
    if before["name"] != item.name:
        changed_other = True
        log_event(
            db, ctx, item.id, AssetItemEventType.updated,
            field_name="name", old_value=_val(before["name"]), new_value=_val(item.name),
        )

    return changed_other


# --- Serialização ----------------------------------------------------------------

def build_response(item: AssetItem) -> AssetItemResponse:
    computed = compute_criticality(item.confidentiality, item.integrity, item.availability)
    divergent = bool(
        item.criticality_is_manual
        and computed is not None
        and item.criticality is not None
        and item.criticality != computed
    )
    resp = AssetItemResponse.model_validate(item)
    resp.review_status = derive_review_status(item.next_review_at)
    resp.criticality_computed = computed
    resp.criticality_divergent = divergent
    resp.cia_complete = _cia_complete(item.confidentiality, item.integrity, item.availability)
    resp.pending_fields = pending_fields(item)
    return resp
