"""Schemas Pydantic v2 de organização e bootstrap."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    slug: str = Field(pattern=r"^[a-z0-9-]+$", min_length=1, max_length=60)


class OrgStatusChange(BaseModel):
    action: Literal["suspend", "reactivate"]


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    status: str
    created_at: datetime


class BootstrapRequest(BaseModel):
    bootstrap_token: str
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str
