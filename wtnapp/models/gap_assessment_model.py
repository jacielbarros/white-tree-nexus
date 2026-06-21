"""Gap Analysis — avaliação (matriz) e itens individuais com histórico append-only."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Date, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import DocStatus, GapPriority, GapStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapAssessment(Base):
    """Artefato único por organização (1 em vigor + baselines como DocumentVersion)."""

    __tablename__ = "gap_assessment"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_gap_assessment_tenant"),
        Index("ix_gap_assessment_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    seed_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_seed_version.id"), nullable=True
    )
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20),
        nullable=False,
        default=DocStatus.draft,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class GapAssessmentItem(Base):
    """Avaliação de um item do catálogo da org."""

    __tablename__ = "gap_assessment_item"
    __table_args__ = (
        UniqueConstraint("assessment_id", "catalog_item_id", name="uq_gap_assessment_item_catalog"),
        Index("ix_gap_assessment_item_tenant_id", "tenant_id"),
        Index("ix_gap_assessment_item_assessment_id", "assessment_id"),
        Index("ix_gap_assessment_item_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    assessment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_assessment.id"), nullable=False
    )
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_catalog_item.id"), nullable=False
    )
    status: Mapped[GapStatus] = mapped_column(
        SAEnum(GapStatus, native_enum=False, length=20),
        nullable=False,
        default=GapStatus.not_filled,
    )
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    actions: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[GapPriority | None] = mapped_column(
        SAEnum(GapPriority, native_enum=False, length=20), nullable=True
    )
    responsible: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    evidence_ref: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # obrigatória quando status=not_applicable
    exclusion_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    maturity_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    effort_estimate: Mapped[str | None] = mapped_column(String(60), nullable=True)
    soa_ref: Mapped[str | None] = mapped_column(String(60), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class GapAssessmentItemEvent(Base):
    """Histórico de alterações de item — append-only (gatilho bloqueia UPDATE/DELETE)."""

    __tablename__ = "gap_assessment_item_event"
    __table_args__ = (
        Index("ix_gap_assessment_item_event_tenant_id", "tenant_id"),
        Index("ix_gap_assessment_item_event_item_id", "item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_assessment_item.id"), nullable=False
    )
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
