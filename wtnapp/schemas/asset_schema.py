"""Schemas Pydantic — Gestão de Ativos / Processos / Escopo (Feature 011)."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from wtnapp.settings import (
    AssetRecordStatus,
    AssetRelationshipType,
    AssetReviewStatus,
    AssetScopeStatus,
    AssetType,
    CiaLevel,
)


# --- Item ---

class AssetItemBase(BaseModel):
    name: str
    item_type: AssetType
    description: Optional[str] = None
    business_unit: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    custodian_user_id: Optional[uuid.UUID] = None
    record_status: AssetRecordStatus = AssetRecordStatus.active
    scope_status: AssetScopeStatus
    scope_justification: Optional[str] = None
    location: Optional[str] = None
    related_system_id: Optional[uuid.UUID] = None
    related_process_id: Optional[uuid.UUID] = None
    related_supplier_id: Optional[uuid.UUID] = None
    has_personal_data: bool = False
    has_sensitive_data: bool = False
    compliance_notes: Optional[str] = None
    confidentiality: Optional[CiaLevel] = None
    integrity: Optional[CiaLevel] = None
    availability: Optional[CiaLevel] = None
    criticality: Optional[CiaLevel] = None
    last_review_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    context_origin_type: Optional[str] = None
    context_origin_id: Optional[uuid.UUID] = None


class AssetItemCreate(AssetItemBase):
    # Override manual de criticidade (registra ajuste); duplicidade permitida com justificativa.
    criticality_is_manual: bool = False
    allow_duplicate: bool = False
    reason: Optional[str] = None


class AssetItemUpdate(AssetItemBase):
    criticality_is_manual: bool = False
    allow_duplicate: bool = False
    reason: Optional[str] = None


class AssetItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    item_type: AssetType
    description: Optional[str] = None
    business_unit: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    owner_user_id: Optional[uuid.UUID] = None
    custodian_user_id: Optional[uuid.UUID] = None
    record_status: AssetRecordStatus
    scope_status: AssetScopeStatus
    scope_justification: Optional[str] = None
    location: Optional[str] = None
    related_system_id: Optional[uuid.UUID] = None
    related_process_id: Optional[uuid.UUID] = None
    related_supplier_id: Optional[uuid.UUID] = None
    has_personal_data: bool
    has_sensitive_data: bool
    compliance_notes: Optional[str] = None
    confidentiality: Optional[CiaLevel] = None
    integrity: Optional[CiaLevel] = None
    availability: Optional[CiaLevel] = None
    criticality: Optional[CiaLevel] = None
    criticality_is_manual: bool
    last_review_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    context_origin_type: Optional[str] = None
    context_origin_id: Optional[uuid.UUID] = None
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    created_by: uuid.UUID
    updated_by: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime

    # Derivados (calculados no serviço, não persistidos).
    review_status: AssetReviewStatus = AssetReviewStatus.undefined
    criticality_computed: Optional[CiaLevel] = None
    criticality_divergent: bool = False
    cia_complete: bool = False
    pending_fields: list[str] = []


class AssetArchiveRequest(BaseModel):
    reason: str


# --- Relacionamentos ---

class RelationshipCreate(BaseModel):
    relationship_type: AssetRelationshipType
    target_item_id: uuid.UUID
    description: Optional[str] = None


class RelationshipResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    source_item_id: uuid.UUID
    relationship_type: AssetRelationshipType
    target_item_id: uuid.UUID
    description: Optional[str] = None
    created_at: datetime
    # Enriquecido para a UI.
    source_code: Optional[str] = None
    source_name: Optional[str] = None
    target_code: Optional[str] = None
    target_name: Optional[str] = None
    direction: Optional[str] = None  # "outgoing" | "incoming" (relativo ao item consultado)


# --- Vínculo com Gap ---

class GapLinkCreate(BaseModel):
    gap_catalog_item_id: uuid.UUID
    note: Optional[str] = None


class GapLinkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    gap_catalog_item_id: uuid.UUID
    note: Optional[str] = None
    created_at: datetime
    # Enriquecido a partir do catálogo da org.
    gap_ref_code: Optional[str] = None
    gap_name: Optional[str] = None
    gap_is_discontinued: Optional[bool] = None


# --- Histórico ---

class AssetItemEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_id: uuid.UUID
    event_type: str
    field_name: Optional[str] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    reason: Optional[str] = None
    actor_id: Optional[uuid.UUID] = None
    occurred_at: datetime
    details: Optional[dict] = None


# --- Detalhe agregado ---

class AssetItemDetail(BaseModel):
    item: AssetItemResponse
    relationships: list[RelationshipResponse] = []
    gap_links: list[GapLinkResponse] = []


# --- Métricas ---

class AssetSummaryResponse(BaseModel):
    total: int
    assets: int
    processes: int
    suppliers: int
    in_scope: int
    critical: int
    without_responsible: int
    cia_incomplete: int


class AssetDashboardResponse(BaseModel):
    by_type: dict[str, int]
    by_criticality: dict[str, int]
    by_scope: dict[str, int]
    by_review_status: dict[str, int]
    with_personal_data: int
    critical_without_review: int
    without_responsible: int


# --- Origem de contexto (US5) ---

class ContextSourceResponse(BaseModel):
    origin_type: str          # stakeholder | context_issue | scope
    origin_id: uuid.UUID
    label: str
    description: Optional[str] = None
    suggested_item_type: Optional[AssetType] = None
