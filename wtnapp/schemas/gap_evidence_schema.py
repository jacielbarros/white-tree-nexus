"""Schemas Pydantic for Gap Analysis evidence attachments."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import Classification, GapEvidenceStatus


class GapEvidenceSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    assessment_item_id: uuid.UUID
    title: str
    description: str | None = None
    classification: Classification
    status: GapEvidenceStatus
    current_version_id: uuid.UUID
    file_name: str
    mime_type: str | None = None
    extension: str
    size_bytes: int
    content_hash: str
    hash_algorithm: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    created_at: datetime
    can_download: bool


class GapEvidenceVersionSummary(BaseModel):
    id: uuid.UUID
    version_number: int
    classification: Classification
    file_name: str
    mime_type: str | None = None
    extension: str
    size_bytes: int
    content_hash: str
    hash_algorithm: str
    uploaded_by: uuid.UUID
    uploaded_at: datetime
    is_current: bool


class GapEvidenceEventSummary(BaseModel):
    id: uuid.UUID
    event_type: str
    outcome: str
    actor_id: uuid.UUID | None = None
    occurred_at: datetime
    details: dict[str, Any] | None = None


class GapEvidenceHistory(BaseModel):
    evidence: GapEvidenceSummary
    versions: list[GapEvidenceVersionSummary]
    events: list[GapEvidenceEventSummary]


class GapEvidenceInactivateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)
