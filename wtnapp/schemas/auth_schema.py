"""Schemas Pydantic v2 de autenticação e contexto do usuário."""

import uuid

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MembershipInfo(BaseModel):
    tenant_id: uuid.UUID
    org_name: str
    role: str


class MeResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    is_super_admin: bool
    memberships: list[MembershipInfo]


class OrgContextResponse(BaseModel):
    tenant_id: uuid.UUID
    role: str
    is_super_admin: bool


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str
