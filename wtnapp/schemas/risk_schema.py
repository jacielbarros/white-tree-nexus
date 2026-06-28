"""Schemas Pydantic do módulo de Gestão de Riscos (Feature 012)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, Field

from wtnapp.settings import (
    RiskStatus,
    RiskTreatmentOption,
    ThreatCategory,
    ThreatOrigin,
    VulnerabilityCategory,
)


# --- Metodologia ---

class MethodologyResponse(BaseModel):
    is_configured: bool
    probability_scale: list[dict]
    impact_scale: list[dict]
    risk_levels: list[dict]
    risk_matrix: dict[str, str]
    acceptance: dict[str, bool]
    cia_impact_map: dict[str, int]


class MethodologyUpdate(BaseModel):
    probability_scale: list[dict]
    impact_scale: list[dict]
    risk_levels: list[dict]
    risk_matrix: dict[str, str]
    acceptance: dict[str, bool]
    cia_impact_map: dict[str, int]


# --- Catálogo ---

class ThreatCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category: ThreatCategory
    origin: ThreatOrigin | None = None


class ThreatResponse(BaseModel):
    id: uuid.UUID
    code: str
    seed_item_id: uuid.UUID | None
    name: str
    description: str | None
    category: ThreatCategory
    origin: ThreatOrigin | None
    is_custom: bool
    is_archived: bool

    class Config:
        from_attributes = True


class VulnerabilityCreate(BaseModel):
    name: str = Field(min_length=1, max_length=300)
    description: str | None = None
    category: VulnerabilityCategory
    gap_catalog_item_id: uuid.UUID | None = None


class VulnerabilityResponse(BaseModel):
    id: uuid.UUID
    code: str
    seed_item_id: uuid.UUID | None
    name: str
    description: str | None
    category: VulnerabilityCategory
    gap_catalog_item_id: uuid.UUID | None
    is_custom: bool
    is_archived: bool

    class Config:
        from_attributes = True


class ArchiveRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class AdoptResult(BaseModel):
    added: int
    unchanged: int
    reactivated: int


class LinkAssetRequest(BaseModel):
    asset_item_id: uuid.UUID


# --- Risco ---

class RiskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = Field(min_length=1)
    threat_id: uuid.UUID
    vulnerability_id: uuid.UUID
    asset_item_ids: list[uuid.UUID] = Field(default_factory=list)


class RiskEvaluate(BaseModel):
    probability_level: int | None = Field(default=None, ge=1, le=5)
    impact_level: int | None = Field(default=None, ge=1, le=5)
    impact_override_reason: str | None = None
    owner_user_id: uuid.UUID | None = None
    reason: str | None = None


class RiskResponse(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    description: str
    threat_id: uuid.UUID
    vulnerability_id: uuid.UUID
    asset_item_ids: list[uuid.UUID] = Field(default_factory=list)
    probability_level: int | None
    impact_level: int | None
    impact_derived_level: int | None
    impact_is_override: bool
    inherent_level_key: str | None
    above_acceptance: bool | None
    owner_user_id: uuid.UUID | None
    status: RiskStatus
    treatment_option: RiskTreatmentOption | None
    residual_probability_level: int | None
    residual_impact_level: int | None
    residual_level_key: str | None
    residual_above_acceptance: bool | None
    is_archived: bool

    class Config:
        from_attributes = True


# --- Tratamento ---

class TreatmentUpdate(BaseModel):
    treatment_option: RiskTreatmentOption
    treatment_note: str | None = None
    residual_probability_level: int | None = Field(default=None, ge=1, le=5)
    residual_impact_level: int | None = Field(default=None, ge=1, le=5)
    reason: str | None = None


class ControlCreate(BaseModel):
    gap_catalog_item_id: uuid.UUID | None = None
    custom_control_label: str | None = None
    responsible_user_id: uuid.UUID | None = None
    due_date: date | None = None
    note: str | None = None


class ControlResponse(BaseModel):
    id: uuid.UUID
    risk_id: uuid.UUID
    gap_catalog_item_id: uuid.UUID | None
    custom_control_label: str | None
    responsible_user_id: uuid.UUID | None
    due_date: date | None
    note: str | None

    class Config:
        from_attributes = True


class AcceptRequest(BaseModel):
    acceptance_reason: str = Field(min_length=1)
    accepted_owner_user_id: uuid.UUID


# --- Plano ---

class PlanResponse(BaseModel):
    id: uuid.UUID
    draft_status: str
    current_version_id: uuid.UUID | None

    class Config:
        from_attributes = True


class PlanApprove(BaseModel):
    classification: str | None = None
    next_review_at: datetime | None = None
    change_nature: str | None = None
    sign: bool = False


# --- SoA-feed / métricas / histórico ---

class SoaFeedItem(BaseModel):
    gap_catalog_item_id: uuid.UUID
    ref_code: str | None
    inclusion_reason: str
    risk_ids: list[uuid.UUID]
    risk_codes: list[str]


class HeatmapCell(BaseModel):
    probability: int
    impact: int
    level_key: str | None
    count: int


class RiskEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    field_name: str | None
    old_value: str | None
    new_value: str | None
    reason: str | None
    actor_id: uuid.UUID | None
    occurred_at: datetime

    class Config:
        from_attributes = True
