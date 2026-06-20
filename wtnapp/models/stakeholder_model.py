"""Mapa de Partes Interessadas (ISO 27001 4.2)."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.models.context_common import now_utc
from wtnapp.settings import DocStatus, EngagementStrategy, Level, RequirementType


class StakeholderMap(Base):
    __tablename__ = "stakeholder_maps"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, index=True, nullable=False
    )
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.draft, nullable=False
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class Stakeholder(Base):
    __tablename__ = "stakeholders"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    map_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("stakeholder_maps.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    power: Mapped[Level] = mapped_column(SAEnum(Level, native_enum=False, length=20), nullable=False)
    interest: Mapped[Level] = mapped_column(SAEnum(Level, native_enum=False, length=20), nullable=False)
    strategy: Mapped[EngagementStrategy] = mapped_column(
        SAEnum(EngagementStrategy, native_enum=False, length=40), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)


class StakeholderRequirement(Base):
    __tablename__ = "stakeholder_requirements"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    stakeholder_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("stakeholders.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[RequirementType] = mapped_column(
        SAEnum(RequirementType, native_enum=False, length=30), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    how_addressed: Mapped[str] = mapped_column(Text, default="", nullable=False)
