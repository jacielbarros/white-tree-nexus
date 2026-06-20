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
    # Nome e senha são obrigatórios apenas para usuários NOVOS; quem já tem conta
    # apenas confirma o vínculo (sem redefinir a senha). Validado no router.
    full_name: str | None = Field(default=None, max_length=200)
    password: str | None = None


class InviteLookupResponse(BaseModel):
    """Resolve um convite por token (público) p/ a tela de aceite decidir o que pedir."""

    org_name: str
    role: str
    email: str
    requires_password: bool


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
