"""Não Conformidades & Ações Corretivas (cláusula 10.2) — Feature 015 / 5b.

NC → ação corretiva → verificação de eficácia, com trilha `nonconformity_event` append-only
(triggers SQLite + PostgreSQL). A NC pode ser **promovida** de uma constatação de auditoria (5a).
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Date,
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
from wtnapp.settings import (
    CorrectiveActionStatus,
    NCOrigin,
    NCSeverity,
    NCStatus,
    SgsiArtifactType,
    VerificationResult,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class NonConformity(Base):
    """Registro central de uma não conformidade (10.2)."""

    __tablename__ = "nonconformity"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_nonconformity_code"),
        Index("ix_nonconformity_tenant_id", "tenant_id"),
        Index("ix_nonconformity_status", "status"),
        Index("ix_nonconformity_severity", "severity"),
        Index("ix_nonconformity_source_finding_id", "source_finding_id"),
        Index("ix_nonconformity_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    origin: Mapped[NCOrigin] = mapped_column(SAEnum(NCOrigin, native_enum=False, length=30), nullable=False)
    source_finding_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("internal_audit_finding.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[NCSeverity] = mapped_column(SAEnum(NCSeverity, native_enum=False, length=20), nullable=False)
    target_type: Mapped[SgsiArtifactType | None] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(Text, nullable=True)
    root_cause_method: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[NCStatus] = mapped_column(
        SAEnum(NCStatus, native_enum=False, length=20), default=NCStatus.open, nullable=False
    )
    opened_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    closed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class CorrectiveAction(Base):
    """Ação corretiva vinculada a uma NC (responsável=membro + prazo)."""

    __tablename__ = "corrective_action"
    __table_args__ = (
        Index("ix_corrective_action_tenant_id", "tenant_id"),
        Index("ix_corrective_action_nonconformity_id", "nonconformity_id"),
        Index("ix_corrective_action_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    nonconformity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("nonconformity.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsible_member_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[CorrectiveActionStatus] = mapped_column(
        SAEnum(CorrectiveActionStatus, native_enum=False, length=20),
        default=CorrectiveActionStatus.planned,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class NonConformityVerification(Base):
    """Verificação de eficácia de uma NC (governa o gate de encerramento)."""

    __tablename__ = "nonconformity_verification"
    __table_args__ = (
        Index("ix_nc_verification_tenant_id", "tenant_id"),
        Index("ix_nc_verification_nonconformity_id", "nonconformity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    nonconformity_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("nonconformity.id"), nullable=False)
    result: Mapped[VerificationResult] = mapped_column(SAEnum(VerificationResult, native_enum=False, length=20), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class NonConformityEvent(Base):
    """Trilha append-only do domínio de NC (NC/ação/verificação)."""

    __tablename__ = "nonconformity_event"
    __table_args__ = (
        Index("ix_nonconformity_event_tenant_id", "tenant_id"),
        Index("ix_nonconformity_event_nc_id", "nonconformity_id"),
        Index("ix_nonconformity_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    nonconformity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("nonconformity.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS nonconformity_event_no_update BEFORE UPDATE ON nonconformity_event "
    "BEGIN SELECT RAISE(ABORT, 'nonconformity_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS nonconformity_event_no_delete BEFORE DELETE ON nonconformity_event "
    "BEGIN SELECT RAISE(ABORT, 'nonconformity_event is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_nonconformity_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'nonconformity_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS nonconformity_event_append_only ON nonconformity_event;",
    "CREATE TRIGGER nonconformity_event_append_only BEFORE UPDATE OR DELETE ON nonconformity_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_nonconformity_event_append_only();",
)


@event.listens_for(NonConformityEvent.__table__, "after_create")
def _create_nc_event_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    stmts = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in stmts:
        connection.exec_driver_sql(stmt)
