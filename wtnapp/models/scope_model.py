"""Declaracao de Escopo do SGSI (ISO 27001 4.3)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.models.context_common import now_utc
from wtnapp.settings import DocStatus, ScopeItemKind


class ScopeStatement(Base):
    __tablename__ = "scope_statements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, index=True, nullable=False
    )
    interfaces_dependencies: Mapped[str] = mapped_column(Text, default="", nullable=False)
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.draft, nullable=False
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    context_version_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    stakeholder_version_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class ScopeItem(Base):
    __tablename__ = "scope_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    scope_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("scope_statements.id", ondelete="CASCADE"), index=True, nullable=False
    )
    kind: Mapped[ScopeItemKind] = mapped_column(
        SAEnum(ScopeItemKind, native_enum=False, length=20), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
