"""Schemas do diagnostico de contexto."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from wtnapp.settings import DiagnosticStatus


class DiagnosticBase(BaseModel):
    status: DiagnosticStatus = DiagnosticStatus.draft
    sections: dict = Field(default_factory=dict)


class DiagnosticResponse(DiagnosticBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
