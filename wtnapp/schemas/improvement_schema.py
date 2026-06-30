"""Schemas Pydantic de Melhorias + visão de ciclo PDCA (10.1) — Feature 015."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import ImprovementOrigin, ImprovementStatus, SgsiArtifactType


class ImprovementRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1)
    origin: ImprovementOrigin
    source_ref: uuid.UUID | None = None
    status: ImprovementStatus = ImprovementStatus.proposed
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None


class ImprovementSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    title: str
    description: str
    origin: ImprovementOrigin
    source_ref: uuid.UUID | None = None
    status: ImprovementStatus
    target_type: SgsiArtifactType | None = None
    target_id: uuid.UUID | None = None


class PdcaEntry(BaseModel):
    occurred_at: datetime
    phase: Literal["check", "act", "plan"]
    kind: Literal["finding", "nonconformity", "corrective_action", "management_review", "improvement"]
    ref_id: uuid.UUID
    label: str
    detail: str
