"""Schemas de atribuicao, eventos e assinaturas de formulario."""

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, model_validator

from wtnapp.settings import AssignmentEventType, AssignmentStatus, FormKind, SignerRole


class AssignmentCreate(BaseModel):
    template_id: uuid.UUID
    respondent_user_id: uuid.UUID | None = None
    respondent_email: str | None = None
    respondent_name: str | None = None
    deadline_at: datetime | None = None
    instructions: str | None = None

    @model_validator(mode="after")
    def _check_respondent_exclusivity(self):
        has_user = self.respondent_user_id is not None
        has_email = bool(self.respondent_email and self.respondent_email.strip())
        if has_user == has_email:
            raise ValueError(
                "Informe respondent_user_id (membro) OU respondent_email (externo), nao ambos nem nenhum."
            )
        return self


class AnswersUpdate(BaseModel):
    answers: dict[str, Any]


class ReturnRequest(BaseModel):
    reason: str | None = None


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    kind: FormKind
    title: str
    fields_snapshot: list[Any]
    status: AssignmentStatus
    respondent_user_id: uuid.UUID | None
    respondent_email: str | None
    deadline_at: datetime | None
    overdue: bool = False
    answers: dict[str, Any]
    current_version_id: uuid.UUID | None
    claimed_at: datetime | None
    submitted_at: datetime | None
    signed_at: datetime | None
    instructions: str | None = None

    @model_validator(mode="after")
    def _compute_overdue(self):
        """Campo derivado: verdadeiro se o prazo venceu e a atribuicao ainda nao foi concluida/cancelada."""
        if self.deadline_at is not None and self.status not in (
            AssignmentStatus.signed,
            AssignmentStatus.completed,
            AssignmentStatus.cancelled,
        ):
            dl = self.deadline_at
            if dl.tzinfo is None:
                dl = dl.replace(tzinfo=timezone.utc)
            self.overdue = dl < datetime.now(timezone.utc)
        return self


class AssignmentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    event: AssignmentEventType
    actor_user_id: uuid.UUID | None
    actor_label: str | None
    at: datetime
    note: str | None


class SignatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    signer_role: SignerRole
    signer_name: str
    signed_at: datetime
    content_hash: str
    level: str
    otp_verified: bool


class VerifyResult(BaseModel):
    valid: bool
    content_hash: str | None
    signed_at: datetime | None


class ExternalSignRequest(BaseModel):
    otp: str
    signer_name: str


class SignaturePolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    require_assigner_countersignature: bool


class SignaturePolicyUpdate(BaseModel):
    require_assigner_countersignature: bool
