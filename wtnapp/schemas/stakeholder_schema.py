"""Schemas de partes interessadas."""

from uuid import UUID

from pydantic import BaseModel

from wtnapp.settings import DocStatus, EngagementStrategy, Level, RequirementType


class StakeholderRequirementPayload(BaseModel):
    type: RequirementType
    description: str
    how_addressed: str = ""


class StakeholderRequirementResponse(StakeholderRequirementPayload):
    id: UUID

    class Config:
        from_attributes = True


class StakeholderCreate(BaseModel):
    name: str
    type: str
    power: Level
    interest: Level
    requirements: list[StakeholderRequirementPayload] = []


class StakeholderUpdate(BaseModel):
    name: str | None = None
    type: str | None = None
    power: Level | None = None
    interest: Level | None = None
    requirements: list[StakeholderRequirementPayload] | None = None


class StakeholderResponse(BaseModel):
    id: UUID
    name: str
    type: str
    power: Level
    interest: Level
    strategy: EngagementStrategy
    requirements: list[StakeholderRequirementResponse] = []

    class Config:
        from_attributes = True


class StakeholderMapResponse(BaseModel):
    id: UUID
    draft_status: DocStatus
    current_version_id: UUID | None = None
    stakeholders: list[StakeholderResponse] = []
    review_overdue: bool = False

    class Config:
        from_attributes = True
