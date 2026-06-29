"""Statement of Applicability (SoA) — artefato único por org, itens e histórico append-only."""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Text,
    UniqueConstraint, Uuid, event,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import DocStatus, GapTheme, SoaImplementationStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Soa(Base):
    """Declaração de Aplicabilidade — artefato único por organização (Documento Controlado)."""

    __tablename__ = "soa"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_soa_tenant"),
        Index("ix_soa_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    gap_assessment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_assessment.id"), nullable=True
    )
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), nullable=False, default=DocStatus.draft
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class SoaItem(Base):
    """Um controle do Anexo A na SoA da organização."""

    __tablename__ = "soa_item"
    __table_args__ = (
        UniqueConstraint("soa_id", "catalog_item_id", name="uq_soa_item_catalog"),
        Index("ix_soa_item_tenant_id", "tenant_id"),
        Index("ix_soa_item_soa_id", "soa_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    soa_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("soa.id"), nullable=False)
    catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_catalog_item.id"), nullable=False
    )
    gap_assessment_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_assessment_item.id"), nullable=True
    )
    ref_code: Mapped[str] = mapped_column(String(20), nullable=False)
    theme: Mapped[GapTheme | None] = mapped_column(
        SAEnum(GapTheme, native_enum=False, length=20), nullable=True
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # lista de SoaInclusionReason (valores); ≥1 quando applicable
    inclusion_reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    inclusion_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    exclusion_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    implementation_status: Mapped[SoaImplementationStatus | None] = mapped_column(
        SAEnum(SoaImplementationStatus, native_enum=False, length=20), nullable=True
    )
    responsible: Mapped[str | None] = mapped_column(String(200), nullable=True)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    risks_treated: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Feature 013: riscos tratados estruturados — projeção do soa-feed: list[{risk_id, risk_code}]
    risk_links: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    expected_evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_refs: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class SoaItemEvent(Base):
    """Histórico de alterações de item da SoA — append-only (gatilho bloqueia UPDATE/DELETE)."""

    __tablename__ = "soa_item_event"
    __table_args__ = (
        Index("ix_soa_item_event_tenant_id", "tenant_id"),
        Index("ix_soa_item_event_item_id", "item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("soa_item.id"), nullable=False)
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    new_value: Mapped[str | None] = mapped_column(String(120), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS soa_item_event_no_update BEFORE UPDATE ON soa_item_event "
    "BEGIN SELECT RAISE(ABORT, 'soa_item_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS soa_item_event_no_delete BEFORE DELETE ON soa_item_event "
    "BEGIN SELECT RAISE(ABORT, 'soa_item_event is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_soa_item_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'soa_item_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS soa_item_event_append_only ON soa_item_event;",
    "CREATE TRIGGER soa_item_event_append_only BEFORE UPDATE OR DELETE ON soa_item_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_soa_item_event_append_only();",
)


@event.listens_for(SoaItemEvent.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in statements:
        connection.exec_driver_sql(stmt)
