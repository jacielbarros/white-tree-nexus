"""Schemas Pydantic do domínio de Não Conformidades (Feature 015)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import (
    CorrectiveActionStatus,
    NCOrigin,
    NCSeverity,
    NCStatus,
    SgsiArtifactType,
    VerificationResult,
)


class NCRequest(BaseModel):
    origin: NCOrigin
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    severity: NCSeverity
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None
    root_cause: str | None = None
    root_cause_method: str | None = None


class NCSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    origin: NCOrigin
    title: str
    severity: NCSeverity
    status: NCStatus
    source_finding_id: uuid.UUID | None = None
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None


class NCReadiness(BaseModel):
    can_close: bool
    has_effective_verification: bool
    overdue_actions: int
    open_actions: int


class NCDetail(NCSummary):
    description: str
    root_cause: str | None = None
    root_cause_method: str | None = None
    readiness: NCReadiness


class PromoteRequest(BaseModel):
    finding_id: uuid.UUID


class NCTransitionRequest(BaseModel):
    action: Literal["start", "send-verify", "close", "cancel"]


# ───────────────────────────── Ações corretivas ─────────────────────────────

class ActionRequest(BaseModel):
    description: str = Field(min_length=1)
    responsible_member_id: uuid.UUID
    due_date: date | None = None
    status: CorrectiveActionStatus = CorrectiveActionStatus.planned


class ActionSummary(BaseModel):
    id: uuid.UUID
    nonconformity_id: uuid.UUID
    description: str
    responsible_member_id: uuid.UUID
    due_date: date | None = None
    status: CorrectiveActionStatus
    overdue: bool


# ───────────────────────────── Verificação de eficácia ─────────────────────────────

class VerificationRequest(BaseModel):
    result: VerificationResult
    notes: str | None = None


class VerificationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    result: VerificationResult
    notes: str | None = None
    verified_by: uuid.UUID
    verified_at: datetime


class NcDashboard(BaseModel):
    nc_by_status: dict[str, int] = Field(default_factory=dict)
    nc_by_severity: dict[str, int] = Field(default_factory=dict)
    overdue_actions: int = 0
    improvements_by_status: dict[str, int] = Field(default_factory=dict)
