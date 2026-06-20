"""Schemas da politica de classificacao."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ClassificationPolicyPayload(BaseModel):
    rules: dict[str, list[str]] = Field(default_factory=dict)


class ClassificationPolicyResponse(ClassificationPolicyPayload):
    model_config = ConfigDict(from_attributes=True)

    id: UUID | None = None
