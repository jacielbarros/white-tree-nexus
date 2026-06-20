"""FormAssignment — instancia do workflow: template atribuido a um preenchedor."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import CheckConstraint, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import AssignmentStatus, FormKind


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FormAssignment(Base):
    __tablename__ = "form_assignments"
    __table_args__ = (
        # Exatamente um de respondent_user_id ou respondent_token_hash (F3 da analise)
        CheckConstraint(
            "(respondent_user_id IS NOT NULL AND respondent_token_hash IS NULL) OR "
            "(respondent_user_id IS NULL AND respondent_token_hash IS NOT NULL)",
            name="ck_form_assignments_respondent",
        ),
        Index("ix_form_assignments_tenant_id", "tenant_id"),
        Index("ix_form_assignments_status", "status"),
        Index("ix_form_assignments_template_id", "template_id"),
        Index("ix_form_assignments_respondent_user_id", "respondent_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("form_templates.id"), nullable=False
    )
    kind: Mapped[FormKind] = mapped_column(
        SAEnum(FormKind, native_enum=False, length=20), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    fields_snapshot: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[AssignmentStatus] = mapped_column(
        SAEnum(AssignmentStatus, native_enum=False, length=20),
        default=AssignmentStatus.pending,
        nullable=False,
    )
    respondent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    respondent_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    respondent_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # hash do token de acesso externo — nunca o token em claro
    respondent_token_hash: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True, index=True
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    answers: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    assigned_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
