"""Schemas de convite e vínculo (membership)."""

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from wtnapp.settings import Role


class InvitationCreate(BaseModel):
    email: EmailStr
    role: Role


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    role: str
    status: str
    expires_at: datetime


class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str = Field(min_length=1, max_length=200)
    password: str


class MembershipResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: str
    status: str
    locked: bool


class RoleChangeRequest(BaseModel):
    role: Role


class MembershipStatusChange(BaseModel):
    status: Literal["active", "disabled"]
