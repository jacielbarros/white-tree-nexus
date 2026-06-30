"""Schemas Pydantic do repositório transversal de evidências (Feature 014)."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import Classification, EvidenceStatus, SgsiArtifactType


class EvidenceLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    target_type: SgsiArtifactType
    target_id: uuid.UUID
    active: bool


class EvidenceSummary(BaseModel):
    """Resumo da evidência (versão corrente). Nunca inclui `storage_key`."""

    id: uuid.UUID
    title: str
    description: str | None = None
    classification: Classification
    status: EvidenceStatus
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
    links: list[EvidenceLinkOut] = Field(default_factory=list)


class EvidenceVersionSummary(BaseModel):
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


class EvidenceEventSummary(BaseModel):
    id: uuid.UUID
    event_type: str
    outcome: str
    actor_id: uuid.UUID | None = None
    occurred_at: datetime
    details: dict[str, Any] | None = None


class EvidenceHistory(BaseModel):
    evidence: EvidenceSummary
    versions: list[EvidenceVersionSummary]
    events: list[EvidenceEventSummary]


class EvidenceLinkRequest(BaseModel):
    target_type: SgsiArtifactType
    target_id: uuid.UUID


class EvidenceInactivateRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)
