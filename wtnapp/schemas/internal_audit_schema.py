"""Schemas Pydantic da Auditoria Interna (Feature 014, Fase 2)."""

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.schemas.evidence_schema import EvidenceLinkOut
from wtnapp.settings import (
    AuditChecklistResult,
    AuditFindingStatus,
    AuditFindingType,
    Classification,
    DocStatus,
    InternalAuditStatus,
    SgsiArtifactType,
)


# ───────────────────────────── Programa ─────────────────────────────

class ProgramRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    objective: str | None = None
    period_start: date | None = None
    period_end: date | None = None


class ProgramSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    objective: str | None = None
    period_start: date | None = None
    period_end: date | None = None
    created_at: datetime


# ───────────────────────────── Auditoria ─────────────────────────────

class AuditRequest(BaseModel):
    program_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    scope: str = Field(min_length=1)
    criteria: str = Field(min_length=1)
    auditor_member_id: uuid.UUID
    period_start: date | None = None
    period_end: date | None = None


class AuditSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    program_id: uuid.UUID
    code: str
    title: str
    status: InternalAuditStatus
    auditor_member_id: uuid.UUID
    period_start: date | None = None
    period_end: date | None = None
    current_version_id: uuid.UUID | None = None
    draft_status: DocStatus


class AuditReadiness(BaseModel):
    can_approve_report: bool
    pending_items: int
    findings_count: int


class AuditDetail(AuditSummary):
    scope: str
    criteria: str
    readiness: AuditReadiness


class TransitionRequest(BaseModel):
    action: Literal["start", "complete", "cancel"]


# ───────────────────────────── Checklist ─────────────────────────────

class ChecklistItemRequest(BaseModel):
    criterion: str = Field(min_length=1)
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None
    result: AuditChecklistResult = AuditChecklistResult.pendente
    note: str | None = None
    order_index: int = 0


class ChecklistItemSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    audit_id: uuid.UUID
    criterion: str
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None
    result: AuditChecklistResult
    note: str | None = None
    order_index: int


class ChecklistItemUpdate(BaseModel):
    result: AuditChecklistResult
    note: str | None = None


class ChecklistImportRequest(BaseModel):
    source: Literal["soa", "gap"]
    only_applicable: bool = True


# ───────────────────────────── Constatações ─────────────────────────────

class FindingRequest(BaseModel):
    finding_type: AuditFindingType
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    checklist_item_id: uuid.UUID | None = None
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None


class FindingSummary(BaseModel):
    id: uuid.UUID
    audit_id: uuid.UUID
    finding_type: AuditFindingType
    title: str
    description: str
    checklist_item_id: uuid.UUID | None = None
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None
    promotable: bool
    nonconformity_ref: uuid.UUID | None = None
    status: AuditFindingStatus
    evidence_links: list[EvidenceLinkOut] = Field(default_factory=list)


# ───────────────────────────── Relatório (Documento Controlado) ─────────────────────────────

class ReportApproveRequest(BaseModel):
    sign: bool = False
    classification: Classification = Classification.uso_interno
    next_review_at: datetime | None = None
    change_nature: str = Field(default="Emissão do relatório de auditoria", max_length=300)


class ReportVersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    status: str
    classification: Classification
    signed: bool
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
