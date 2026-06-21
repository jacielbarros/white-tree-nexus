"""Schemas Pydantic do módulo SoA (Feature 005)."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from wtnapp.settings import SoaImplementationStatus, SoaInclusionReason


class DivergenceField(BaseModel):
    field: str
    soa_value: Any | None = None
    gap_value: Any | None = None


class SoaItemUpdate(BaseModel):
    applicable: bool | None = None
    inclusion_reasons: list[SoaInclusionReason] | None = None
    inclusion_note: str | None = None
    exclusion_justification: str | None = None
    implementation_status: SoaImplementationStatus | None = None
    responsible: str | None = None
    deadline: date | None = None
    risks_treated: str | None = None
    expected_evidence: str | None = None
    evidence_refs: str | None = None
    observations: str | None = None


class SoaItemResponse(BaseModel):
    id: uuid.UUID
    ref_code: str
    theme: str | None = None
    name: str
    applicable: bool
    inclusion_reasons: list[str] = []
    inclusion_note: str | None = None
    exclusion_justification: str | None = None
    implementation_status: str | None = None
    responsible: str | None = None
    deadline: date | None = None
    risks_treated: str | None = None
    expected_evidence: str | None = None
    evidence_refs: str | None = None
    observations: str | None = None
    gap_assessment_item_id: uuid.UUID | None = None
    divergence: list[DivergenceField] = []


class SoaSummary(BaseModel):
    total: int
    applicable: int
    not_applicable: int
    divergent: int


class SoaResponse(BaseModel):
    id: uuid.UUID
    draft_status: str
    current_version_id: uuid.UUID | None = None
    gap_assessment_id: uuid.UUID | None = None
    items: list[SoaItemResponse]
    summary: SoaSummary


class ReconcileRequest(BaseModel):
    fields: list[str] = []


class SoaApproveRequest(BaseModel):
    classification: str = "uso_interno"
    next_review_at: datetime | None = None
    change_nature: str = "Emissão inicial"
    sign: bool = False


class SoaVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    identifier: str
    version_number: int
    status: str
    classification: str
    next_review_at: datetime | None = None
    change_nature: str
    approved_by: uuid.UUID | None = None
    is_superseded: bool = False
    signed: bool = False
    created_at: datetime
