"""Invitation — convite escopado por tenant. Só o hash do token é persistido (R7)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import InviteStatus, Role


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        # No máximo 1 convite PENDENTE por (tenant, email) — índice parcial (SQLite/PostgreSQL).
        Index(
            "uq_pending_invite",
            "tenant_id",
            "email",
            unique=True,
            sqlite_where=text("status = 'pending'"),
            postgresql_where=text("status = 'pending'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    role: Mapped[Role] = mapped_column(SAEnum(Role, native_enum=False, length=30), nullable=False)
    invited_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    status: Mapped[InviteStatus] = mapped_column(
        SAEnum(InviteStatus, native_enum=False, length=20), default=InviteStatus.pending, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
