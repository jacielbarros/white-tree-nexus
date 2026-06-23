"""Pydantic schemas for printable/signed documents."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from wtnapp.settings import (
    Classification,
    DocumentPreviewStatus,
    PrintTemplateScope,
    PrintTemplateStatus,
    PrintableDocumentType,
    SignedDocumentStatus,
)


class PrintTemplateCreate(BaseModel):
    document_type: PrintableDocumentType
    name: str = Field(min_length=3, max_length=160)
    description: str | None = Field(default=None, max_length=500)
    default_classification: Classification = Classification.uso_interno


class PrintTemplateVersionCreate(BaseModel):
    layout_schema: dict[str, Any]
    allowed_variables: dict[str, Any] = Field(default_factory=dict)
    required_sections: list[str] = Field(default_factory=list)


class PrintTemplateVersionResponse(BaseModel):
    id: uuid.UUID
    template_id: uuid.UUID
    version_number: int
    renderer: str
    layout_schema: dict[str, Any]
    allowed_variables: dict[str, Any]
    required_sections: list[str]
    content_hash: str
    is_current: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class PrintTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    scope: PrintTemplateScope
    document_type: PrintableDocumentType
    name: str
    description: str | None
    status: PrintTemplateStatus
    default_classification: Classification
    current_version_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime | None

    class Config:
        from_attributes = True


class DocumentPreviewCreate(BaseModel):
    document_type: PrintableDocumentType
    source_artifact_id: uuid.UUID | None = None
    template_version_id: uuid.UUID | None = None
    classification: Classification | None = None


class DocumentPreviewResponse(BaseModel):
    id: uuid.UUID
    document_type: PrintableDocumentType
    source_artifact_id: uuid.UUID | None
    template_version_id: uuid.UUID
    classification: Classification
    status: DocumentPreviewStatus
    snapshot_hash: str
    preview_pdf_hash: str
    expires_at: datetime
    created_at: datetime
    warnings: list[str] = Field(default_factory=list)

    class Config:
        from_attributes = True


class SignPreviewRequest(BaseModel):
    confirm_snapshot_hash: str | None = None


class SignedDocumentResponse(BaseModel):
    id: uuid.UUID
    document_type: PrintableDocumentType
    source_artifact_id: uuid.UUID | None
    template_version_id: uuid.UUID
    version_number: int
    status: SignedDocumentStatus
    classification: Classification
    identifier: str
    pdf_hash: str
    snapshot_hash: str
    size_bytes: int
    signed_by: uuid.UUID
    signed_at: datetime

    class Config:
        from_attributes = True


class IntegrityVerificationResponse(BaseModel):
    valid: bool
    identifier: str
    pdf_hash: str
    snapshot_hash: str
    verified_at: datetime
