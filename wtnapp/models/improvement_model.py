"""Melhoria Contínua / PDCA (cláusula 10.1) — Feature 015 / 5b.

Melhorias/oportunidades (origem auditoria/NC/análise crítica/sugestão) com referência **read-only**
de realimentação a um artefato. Trilha `improvement_event` append-only (triggers SQLite + PG).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import ImprovementOrigin, ImprovementStatus, SgsiArtifactType


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Improvement(Base):
    """Melhoria/oportunidade (10.1) com realimentação read-only a um artefato."""

    __tablename__ = "improvement"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_improvement_code"),
        Index("ix_improvement_tenant_id", "tenant_id"),
        Index("ix_improvement_status", "status"),
        Index("ix_improvement_origin", "origin"),
        Index("ix_improvement_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    origin: Mapped[ImprovementOrigin] = mapped_column(SAEnum(ImprovementOrigin, native_enum=False, length=30), nullable=False)
    source_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[ImprovementStatus] = mapped_column(
        SAEnum(ImprovementStatus, native_enum=False, length=20), default=ImprovementStatus.proposed, nullable=False
    )
    target_type: Mapped[SgsiArtifactType | None] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class ImprovementEvent(Base):
    """Trilha append-only de melhorias."""

    __tablename__ = "improvement_event"
    __table_args__ = (
        Index("ix_improvement_event_tenant_id", "tenant_id"),
        Index("ix_improvement_event_improvement_id", "improvement_id"),
        Index("ix_improvement_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    improvement_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("improvement.id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS improvement_event_no_update BEFORE UPDATE ON improvement_event "
    "BEGIN SELECT RAISE(ABORT, 'improvement_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS improvement_event_no_delete BEFORE DELETE ON improvement_event "
    "BEGIN SELECT RAISE(ABORT, 'improvement_event is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_improvement_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'improvement_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS improvement_event_append_only ON improvement_event;",
    "CREATE TRIGGER improvement_event_append_only BEFORE UPDATE OR DELETE ON improvement_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_improvement_event_append_only();",
)


@event.listens_for(ImprovementEvent.__table__, "after_create")
def _create_improvement_event_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    stmts = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in stmts:
        connection.exec_driver_sql(stmt)
