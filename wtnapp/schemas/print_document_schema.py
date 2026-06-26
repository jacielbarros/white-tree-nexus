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
    SignatureCoordinateSystem,
    SignatureMethod,
    SignaturePlacementOrigin,
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


class PrintTemplateVariableCreate(BaseModel):
    document_type: PrintableDocumentType
    variable_key: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z][A-Za-z0-9_]{0,79}$")
    label: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    value_type: str = Field(default="string", max_length=30)
    required_by_default: bool = False
    optional_by_default: bool = True
    sort_order: int = Field(default=100, ge=0, le=10000)


class PrintTemplateVariableUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    value_type: str | None = Field(default=None, max_length=30)
    required_by_default: bool | None = None
    optional_by_default: bool | None = None
    status: str | None = Field(default=None, pattern=r"^(active|inactive)$")
    sort_order: int | None = Field(default=None, ge=0, le=10000)


class PrintTemplateVariableResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    scope: str
    document_type: PrintableDocumentType
    variable_key: str
    label: str
    description: str | None
    value_type: str
    required_by_default: bool
    optional_by_default: bool
    status: str
    sort_order: int
    created_at: datetime
    updated_at: datetime | None

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
    pdf_page_metrics: list[dict[str, Any]] = Field(default_factory=list)
    default_signature_placement: dict[str, Any] | None = None

    class Config:
        from_attributes = True


class SignPreviewRequest(BaseModel):
    confirm_snapshot_hash: str | None = None
    confirmed_placement_id: uuid.UUID | None = None


class PdfPageMetric(BaseModel):
    page_number: int = Field(ge=1)
    width_points: float = Field(gt=0)
    height_points: float = Field(gt=0)
    rotation: int = 0


class SignatureBlockedArea(BaseModel):
    page: int | str
    x_points: float
    y_points: float
    width_points: float = Field(gt=0)
    height_points: float = Field(gt=0)
    reason: str | None = Field(default=None, max_length=160)


class SignaturePlacementBase(BaseModel):
    page_number: int = Field(ge=1)
    x_points: float = Field(ge=0)
    y_points: float = Field(ge=0)
    width_points: float = Field(gt=0)
    height_points: float = Field(gt=0)
    page_width_points: float = Field(gt=0)
    page_height_points: float = Field(gt=0)
    coordinate_system: SignatureCoordinateSystem = SignatureCoordinateSystem.pdf_points_bottom_left
    origin: SignaturePlacementOrigin = SignaturePlacementOrigin.user


class SignaturePlacementCreate(SignaturePlacementBase):
    confirm_snapshot_hash: str = Field(min_length=64, max_length=64)


class SignaturePlacementResponse(SignaturePlacementBase):
    id: uuid.UUID
    preview_id: uuid.UUID
    placement_revision: int
    placement_hash: str
    created_by: uuid.UUID
    created_at: datetime

    class Config:
        from_attributes = True


class PreviewLayoutResponse(BaseModel):
    preview_id: uuid.UUID
    document_type: PrintableDocumentType
    snapshot_hash: str
    page_metrics: list[PdfPageMetric]
    blocked_areas: list[SignatureBlockedArea] = Field(default_factory=list)
    default_placement: SignaturePlacementBase
    latest_placement: SignaturePlacementResponse | None = None


class SignedPlacementResponse(SignaturePlacementBase):
    id: uuid.UUID
    signed_document_id: uuid.UUID
    placement_id: uuid.UUID
    placement_hash: str
    created_at: datetime

    class Config:
        from_attributes = True


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
    signature_method: SignatureMethod = SignatureMethod.internal_electronic_signature
    visual_signature_present: bool = True
    signature_placement: SignedPlacementResponse | None = None

    class Config:
        from_attributes = True


class IntegrityVerificationResponse(BaseModel):
    valid: bool
    identifier: str
    pdf_hash: str
    snapshot_hash: str
    verified_at: datetime
