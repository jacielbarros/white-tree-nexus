"""Gap Guidance Service (Feature 007) — leitura agregada e edição (Super Admin) da orientação.

Conteúdo de plataforma (sem `tenant_id`): orientação por item do catálogo-base + legenda global.
Edição registra trilha append-only (`gap_guidance_event`) com antes→depois por campo.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.models.gap_guidance_event_model import GapGuidanceEvent
from wtnapp.models.gap_legend_model import GapLegendEntry
from wtnapp.models.gap_seed_model import GapSeedItem
from wtnapp.schemas.gap_guidance_schema import (
    GuidanceResponse,
    ItemGuidance,
    ItemGuidanceUpdate,
    Legend,
    LegendEntry,
    LegendEntryUpdate,
)


def _ser(value: Any) -> str | None:
    """Serializa valores (listas/strings) para a trilha (texto)."""
    if value is None:
        return None
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


# ── Leitura ──────────────────────────────────────────────────────────────────


def get_guidance(db: Session) -> GuidanceResponse:
    items = db.query(GapSeedItem).order_by(GapSeedItem.order).all()
    legend = db.query(GapLegendEntry).order_by(GapLegendEntry.order).all()
    return GuidanceResponse(
        items=[
            ItemGuidance(
                seed_item_id=s.id,
                ref_code=s.ref_code,
                referencia=s.referencia or "",
                objetivo=s.objective or "",
                como_avaliar=list(s.como_avaliar or []),
                evidencias_esperadas=list(s.evidencias_esperadas or []),
                nota=s.nota,
            )
            for s in items
        ],
        legend=Legend(
            status=[LegendEntry.model_validate(e) for e in legend if e.kind == "status"],
            priority=[LegendEntry.model_validate(e) for e in legend if e.kind == "priority"],
        ),
    )


# ── Edição (Super Admin) ──────────────────────────────────────────────────────


def update_item_guidance(
    db: Session, seed_item_id: uuid.UUID, patch: ItemGuidanceUpdate, actor_id: uuid.UUID | None
) -> GapSeedItem:
    item = db.get(GapSeedItem, seed_item_id)
    if item is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item de orientação não encontrado.")

    # (field exibido na trilha, atributo no modelo, valor novo)
    changes = [
        ("referencia", "referencia", patch.referencia),
        ("objetivo", "objective", patch.objetivo),
        ("como_avaliar", "como_avaliar", patch.como_avaliar),
        ("evidencias_esperadas", "evidencias_esperadas", patch.evidencias_esperadas),
        ("nota", "nota", patch.nota),
    ]
    for field, attr, new in changes:
        if new is None:  # campo ausente → não altera (nota não é "limpável" por este endpoint)
            continue
        old = getattr(item, attr)
        if old == new:
            continue
        db.add(GapGuidanceEvent(
            target_type="seed_item", target_id=item.id, field=field,
            old_value=_ser(old), new_value=_ser(new), actor_id=actor_id,
        ))
        setattr(item, attr, new)

    db.commit()
    db.refresh(item)
    return item


def update_legend(
    db: Session, entry_id: uuid.UUID, patch: LegendEntryUpdate, actor_id: uuid.UUID | None
) -> GapLegendEntry:
    entry = db.get(GapLegendEntry, entry_id)
    if entry is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entrada de legenda não encontrada.")

    for field, new in (("label", patch.label), ("definition", patch.definition)):
        if new is None:
            continue
        old = getattr(entry, field)
        if old == new:
            continue
        db.add(GapGuidanceEvent(
            target_type="legend", target_id=entry.id, field=field,
            old_value=_ser(old), new_value=_ser(new), actor_id=actor_id,
        ))
        setattr(entry, field, new)

    db.commit()
    db.refresh(entry)
    return entry


def list_events(db: Session, limit: int = 200) -> list[GapGuidanceEvent]:
    return (
        db.query(GapGuidanceEvent)
        .order_by(GapGuidanceEvent.created_at.desc())
        .limit(limit)
        .all()
    )
