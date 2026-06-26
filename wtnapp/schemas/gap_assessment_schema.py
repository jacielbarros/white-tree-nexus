"""Schemas Pydantic para avaliação Gap Analysis."""

import uuid
from datetime import date, datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from wtnapp.settings import GapPriority, GapStatus


class AssessmentItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    catalog_item_id: uuid.UUID
    ref_code: str
    dimension: str
    theme: Optional[str] = None
    name: str
    status: GapStatus
    findings: Optional[str] = None
    actions: Optional[str] = None
    priority: Optional[GapPriority] = None
    responsible: Optional[str] = None
    deadline: Optional[date] = None
    evidence_ref: Optional[str] = None
    notes: Optional[str] = None
    exclusion_justification: Optional[str] = None
    maturity_level: Optional[int] = None
    effort_estimate: Optional[str] = None
    soa_ref: Optional[str] = None


class AssessmentResponse(BaseModel):
    id: uuid.UUID
    seed_version: Optional[str] = None
    draft_status: str
    current_version_id: Optional[uuid.UUID] = None
    items: list[AssessmentItemResponse] = []


class AssessmentItemUpdate(BaseModel):
    status: Optional[GapStatus] = None
    findings: Optional[str] = None
    actions: Optional[str] = None
    priority: Optional[GapPriority] = None
    responsible: Optional[str] = None
    deadline: Optional[date] = None
    evidence_ref: Optional[str] = None
    notes: Optional[str] = None
    exclusion_justification: Optional[str] = None
    maturity_level: Optional[int] = None
    effort_estimate: Optional[str] = None


class DimensionMetric(BaseModel):
    conformance: Optional[float] = None       # consolidada (denom = total - N/A)
    adherence_evaluated: Optional[float] = None  # só dos avaliados
    evaluated: int = 0
    total: int = 0


class DashboardResponse(BaseModel):
    # Âncora honesta (jornada completa = cláusulas + Anexo A).
    consolidated_conformance: Optional[float] = None
    total_items: int = 0
    evaluated_items: int = 0
    dimensions: dict[str, DimensionMetric] = {}
    # Aderência dos avaliados (apoio) + distribuições já existentes.
    overall_adherence: Optional[float] = None
    by_dimension: dict[str, Optional[float]] = {}
    by_clause: dict[str, Optional[float]] = {}
    by_theme: dict[str, Optional[float]] = {}
    status_distribution: dict[str, int] = {}
    completeness: float = 0.0


class BaselineApproveRequest(BaseModel):
    classification: str = "uso_interno"
    change_nature: str


class BaselineResponse(BaseModel):
    id: uuid.UUID
    version_number: int
    status: str
    classification: str
    emitted_at: Optional[datetime] = None
    overall_adherence: Optional[float] = None


class BaselineComparisonResponse(BaseModel):
    from_baseline: BaselineResponse
    to_baseline: BaselineResponse
    overall_delta: Optional[float] = None
    by_dimension_delta: dict[str, Optional[float]] = {}
