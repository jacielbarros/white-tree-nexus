"""DTOs da Orientação de Avaliação por Item (Feature 007).

Conteúdo de plataforma: orientação por item do catálogo-base + legenda global. Leitura por org
(view_gap); edição pelo Super Admin.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ItemGuidance(BaseModel):
    seed_item_id: uuid.UUID
    ref_code: str
    referencia: str
    objetivo: str
    como_avaliar: list[str]
    evidencias_esperadas: list[str]
    nota: Optional[str] = None


class LegendEntry(BaseModel):
    id: uuid.UUID
    code: str
    label: str
    definition: str
    order: int

    class Config:
        from_attributes = True


class Legend(BaseModel):
    status: list[LegendEntry]
    priority: list[LegendEntry]


class GuidanceResponse(BaseModel):
    items: list[ItemGuidance]
    legend: Legend


class ItemGuidanceUpdate(BaseModel):
    referencia: Optional[str] = None
    objetivo: Optional[str] = None
    como_avaliar: Optional[list[str]] = None
    evidencias_esperadas: Optional[list[str]] = None
    nota: Optional[str] = None


class LegendEntryUpdate(BaseModel):
    label: Optional[str] = None
    definition: Optional[str] = None


class GuidanceEvent(BaseModel):
    id: uuid.UUID
    target_type: str
    target_id: uuid.UUID
    field: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    created_at: datetime

    class Config:
        from_attributes = True
