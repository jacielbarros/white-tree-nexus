"""Schemas de template de formulario."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from wtnapp.settings import FormKind, TemplateStatus


class FormTemplateCreate(BaseModel):
    kind: FormKind
    title: str
    schema: list[dict[str, Any]]


class FormTemplateUpdate(BaseModel):
    title: str | None = None
    schema: list[dict[str, Any]] | None = None
    status: TemplateStatus | None = None


class FormTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: FormKind
    title: str
    schema: list[dict[str, Any]]
    status: TemplateStatus
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
