"""Diagnostico incremental de contexto, um por tenant."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.models.context_common import now_utc
from wtnapp.settings import DiagnosticStatus


class Diagnostic(Base):
    __tablename__ = "diagnostics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, index=True, nullable=False
    )
    status: Mapped[DiagnosticStatus] = mapped_column(
        SAEnum(DiagnosticStatus, native_enum=False, length=20),
        default=DiagnosticStatus.draft,
        nullable=False,
    )
    sections: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)
