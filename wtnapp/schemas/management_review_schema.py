"""Schemas Pydantic da Análise Crítica pela Direção (9.3) — Feature 015."""

import uuid
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import Classification


class ReviewRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    review_date: date
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)


class ReviewSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    review_date: date
    draft_status: str
    current_version_id: uuid.UUID | None = None


class ReviewReadiness(BaseModel):
    can_approve: bool


class ReviewDetail(ReviewSummary):
    inputs: dict[str, Any]
    outputs: dict[str, Any]
    readiness: ReviewReadiness


class ReviewApproveRequest(BaseModel):
    sign: bool = False
    classification: Classification = Classification.uso_interno
    next_review_at: datetime | None = None
    change_nature: str = Field(default="Emissão da ata de análise crítica", max_length=300)


class ReviewVersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    status: str
    classification: Classification
    signed: bool
    approved_by: uuid.UUID | None = None
    approved_at: datetime | None = None
