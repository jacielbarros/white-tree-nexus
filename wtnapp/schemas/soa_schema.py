"""Schemas Pydantic do módulo SoA (Feature 005)."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from wtnapp.settings import SoaImplementationStatus, SoaInclusionReason


class RiskLink(BaseModel):
    """Risco tratado estruturado — projeção do soa-feed (Feature 013)."""

    risk_id: uuid.UUID
    risk_code: str


class DivergenceField(BaseModel):
    field: str
    # Fonte da divergência: "gap" (Feature 005) ou "risk" (Feature 013)
    source: str = "gap"
    soa_value: Any | None = None
    # Valor vivo da fonte (Gap ou insumo de risco)
    source_value: Any | None = None
    # DEPRECATED — alias de source_value quando source == "gap" (compat de frontend)
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
    risk_links: list[RiskLink] = []                  # Feature 013 — riscos estruturados
    origin: str = "none"                              # Feature 013 — risk | manual | risk+manual | none
    incomplete: bool = False                          # Feature 013 — aplicável sem razão (FR-009a)
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
    risk_divergent: int = 0                           # Feature 013
    incomplete: int = 0                               # Feature 013


class SoaReadiness(BaseModel):
    """Estado do gate da esteira — Pré-SoA vs. SoA normativa (Feature 013)."""

    kind: str                                         # pre_soa | normative (se aprovada agora)
    risk_plan_approved: bool = False
    pending_for_normative: list[str] = []
    out_of_scope_risk_notices: list[str] = []


class SoaResponse(BaseModel):
    id: uuid.UUID
    draft_status: str
    current_version_id: uuid.UUID | None = None
    gap_assessment_id: uuid.UUID | None = None
    items: list[SoaItemResponse]
    summary: SoaSummary
    readiness: SoaReadiness | None = None             # Feature 013


class ReconcileRequest(BaseModel):
    fields: list[str] = []
    source: str = "all"                               # Feature 013 — gap | risk | all


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
    kind: str = "pre_soa"                             # Feature 013 — rótulo congelado da versão
    created_at: datetime
