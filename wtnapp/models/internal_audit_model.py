"""Auditoria Interna (cláusula 9.2) — Feature 014, Fase 2.

Programa → auditoria → checklist → constatação. A trilha `internal_audit_event` é append-only
(triggers SQLite + PostgreSQL). O relatório de auditoria reusa o Documento Controlado
(`document_versions`, `DocType.internal_audit_report`) via `current_report_version_id`+`draft_status`.
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import (
    AuditChecklistResult,
    AuditFindingStatus,
    AuditFindingType,
    DocStatus,
    InternalAuditStatus,
    SgsiArtifactType,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class InternalAuditProgram(Base):
    """Programa de auditoria — agrupa auditorias por período/ciclo."""

    __tablename__ = "internal_audit_program"
    __table_args__ = (Index("ix_internal_audit_program_tenant_id", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    objective: Mapped[str | None] = mapped_column(Text, nullable=True)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class InternalAudit(Base):
    """Auditoria interna — escopo, critérios, auditor, período, ciclo de vida."""

    __tablename__ = "internal_audit"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_internal_audit_code"),
        Index("ix_internal_audit_tenant_id", "tenant_id"),
        Index("ix_internal_audit_program_id", "program_id"),
        Index("ix_internal_audit_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    program_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("internal_audit_program.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    criteria: Mapped[str] = mapped_column(Text, nullable=False)
    auditor_member_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[InternalAuditStatus] = mapped_column(
        SAEnum(InternalAuditStatus, native_enum=False, length=20),
        default=InternalAuditStatus.planned,
        nullable=False,
    )
    current_report_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20),
        default=DocStatus.draft,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class InternalAuditChecklistItem(Base):
    """Item auditado (vínculo opcional a controle/cláusula/risco) + resultado."""

    __tablename__ = "internal_audit_checklist_item"
    __table_args__ = (
        Index("ix_internal_audit_checklist_tenant_id", "tenant_id"),
        Index("ix_internal_audit_checklist_audit_id", "audit_id"),
        Index("ix_internal_audit_checklist_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("internal_audit.id"), nullable=False)
    target_type: Mapped[SgsiArtifactType | None] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[AuditChecklistResult] = mapped_column(
        SAEnum(AuditChecklistResult, native_enum=False, length=20),
        default=AuditChecklistResult.pendente,
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class InternalAuditFinding(Base):
    """Constatação — tipo, vínculo, promovível p/ NC formal (Feature 5b)."""

    __tablename__ = "internal_audit_finding"
    __table_args__ = (
        Index("ix_internal_audit_finding_tenant_id", "tenant_id"),
        Index("ix_internal_audit_finding_audit_id", "audit_id"),
        Index("ix_internal_audit_finding_type", "finding_type"),
        Index("ix_internal_audit_finding_target", "target_type", "target_id"),
        Index("ix_internal_audit_finding_promotable", "promotable"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("internal_audit.id"), nullable=False)
    checklist_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("internal_audit_checklist_item.id"), nullable=True
    )
    finding_type: Mapped[AuditFindingType] = mapped_column(
        SAEnum(AuditFindingType, native_enum=False, length=30), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[SgsiArtifactType | None] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    promotable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Reservado para a Feature 5b (promoção a Não Conformidade formal). Vazio nesta feature.
    nonconformity_ref: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    status: Mapped[AuditFindingStatus] = mapped_column(
        SAEnum(AuditFindingStatus, native_enum=False, length=20),
        default=AuditFindingStatus.active,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)


class InternalAuditEvent(Base):
    """Trilha append-only do domínio de auditoria interna."""

    __tablename__ = "internal_audit_event"
    __table_args__ = (
        Index("ix_internal_audit_event_tenant_id", "tenant_id"),
        Index("ix_internal_audit_event_audit_id", "audit_id"),
        Index("ix_internal_audit_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    audit_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("internal_audit.id"), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


_SQLITE_EVENT_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS internal_audit_event_no_update BEFORE UPDATE ON internal_audit_event "
    "BEGIN SELECT RAISE(ABORT, 'internal_audit_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS internal_audit_event_no_delete BEFORE DELETE ON internal_audit_event "
    "BEGIN SELECT RAISE(ABORT, 'internal_audit_event is append-only'); END;",
)
_PG_EVENT_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_internal_audit_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'internal_audit_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS internal_audit_event_append_only ON internal_audit_event;",
    "CREATE TRIGGER internal_audit_event_append_only BEFORE UPDATE OR DELETE ON internal_audit_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_internal_audit_event_append_only();",
)


@event.listens_for(InternalAuditEvent.__table__, "after_create")
def _create_event_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    stmts = _SQLITE_EVENT_TRIGGERS if dialect == "sqlite" else _PG_EVENT_STATEMENTS if dialect == "postgresql" else ()
    for stmt in stmts:
        connection.exec_driver_sql(stmt)
