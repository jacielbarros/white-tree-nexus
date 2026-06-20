"""Schemas da Analise de Contexto e documentos controlados."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from wtnapp.settings import Classification, DocStatus, IssueFramework, IssueOrigin, Level


class ContextIssueBase(BaseModel):
    origin: IssueOrigin
    framework: IssueFramework
    category: str
    description: str
    impact: Level


class ContextIssueCreate(ContextIssueBase):
    pass


class ContextIssueUpdate(BaseModel):
    origin: IssueOrigin | None = None
    framework: IssueFramework | None = None
    category: str | None = None
    description: str | None = None
    impact: Level | None = None


class ContextIssueResponse(ContextIssueBase):
    id: UUID

    class Config:
        from_attributes = True


class ContextAnalysisUpdate(BaseModel):
    intended_outcomes: str = ""
    methodology: str | None = None


class ContextAnalysisResponse(ContextAnalysisUpdate):
    id: UUID
    draft_status: DocStatus
    current_version_id: UUID | None = None
    issues: list[ContextIssueResponse] = []
    review_overdue: bool = False

    class Config:
        from_attributes = True


class DocumentApproval(BaseModel):
    classification: Classification = Classification.uso_interno
    next_review_at: datetime | None = None
    change_nature: str = "Emissao inicial"


class DocumentVersionResponse(BaseModel):
    id: UUID
    identifier: str
    version_number: int
    status: DocStatus
    classification: Classification
    emitted_at: datetime
    next_review_at: datetime | None = None
    approved_by: UUID | None = None

    class Config:
        from_attributes = True
