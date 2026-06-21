"""Gap Assignment — condução atribuível de avaliação de gap (US5)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapAssignment(Base):
    """Atribuição de condutor de análise gap — membro interno ou externo via token."""

    __tablename__ = "gap_assignment"
    __table_args__ = (
        Index("ix_gap_assignment_tenant_id", "tenant_id"),
        Index("ix_gap_assignment_assessment_id", "assessment_id"),
        Index("ix_gap_assignment_status", "status"),
        CheckConstraint(
            "(respondent_user_id IS NOT NULL AND respondent_token_hash IS NULL) OR "
            "(respondent_user_id IS NULL AND respondent_token_hash IS NOT NULL)",
            name="ck_gap_assignment_respondent",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_assessment.id"), nullable=False
    )
    scope: Mapped[str] = mapped_column(String(20), nullable=False, default="whole")
    scope_theme: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    respondent_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    respondent_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    respondent_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
