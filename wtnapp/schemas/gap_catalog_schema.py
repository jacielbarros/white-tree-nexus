"""Schemas Pydantic para o catálogo Gap Analysis."""

import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict


class CatalogItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    dimension: str
    ref_code: str
    name: str
    theme: Optional[str] = None
    objective: str
    order: int
    is_custom: bool
    is_discontinued: bool
    group_label: Optional[str] = None


class CatalogItemCreate(BaseModel):
    dimension: str
    ref_code: str
    name: str
    theme: Optional[str] = None
    objective: Optional[str] = ""
    group_label: Optional[str] = None
    order: int = 0


class CatalogItemUpdate(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    group_label: Optional[str] = None
    order: Optional[int] = None


class CatalogAdoptRequest(BaseModel):
    seed_version: str
