"""Schemas da declaracao de escopo."""

from uuid import UUID

from pydantic import BaseModel

from wtnapp.settings import DocStatus, ScopeItemKind


class ScopeUpdate(BaseModel):
    interfaces_dependencies: str = ""
    context_version_ref: UUID | None = None
    stakeholder_version_ref: UUID | None = None


class ScopeItemCreate(BaseModel):
    kind: ScopeItemKind
    description: str
    justification: str


class ScopeItemResponse(ScopeItemCreate):
    id: UUID

    class Config:
        from_attributes = True


class ScopeResponse(ScopeUpdate):
    id: UUID
    draft_status: DocStatus
    current_version_id: UUID | None = None
    items: list[ScopeItemResponse] = []
    context_ref_obsolete: bool = False
    stakeholder_ref_obsolete: bool = False
    review_overdue: bool = False

    class Config:
        from_attributes = True
