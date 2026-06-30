"""Repositório transversal de evidências (Feature 014 / 5a).

Generaliza o módulo de evidências do Gap (Feature 008): a evidência é objeto de 1ª classe do
tenant, vinculável a 1..N artefatos via `evidence_link` (polimórfico). Versões e eventos de
custódia são append-only (triggers SQLite + PostgreSQL).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
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
from wtnapp.settings import Classification, EvidenceStatus, SgsiArtifactType


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Evidence(Base):
    """Registro lógico central da evidência (vínculos vivem em `evidence_link`)."""

    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_tenant_id", "tenant_id"),
        Index("ix_evidence_status", "status"),
        Index("ix_evidence_current_version_id", "current_version_id"),
        Index("ix_evidence_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30),
        default=Classification.uso_interno,
        nullable=False,
    )
    status: Mapped[EvidenceStatus] = mapped_column(
        SAEnum(EvidenceStatus, native_enum=False, length=20),
        default=EvidenceStatus.active,
        nullable=False,
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    inactivated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    inactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    inactivation_reason: Mapped[str | None] = mapped_column(String(300), nullable=True)


class EvidenceVersion(Base):
    """Versão imutável do arquivo de uma evidência (append-only)."""

    __tablename__ = "evidence_version"
    __table_args__ = (
        UniqueConstraint("tenant_id", "evidence_id", "version_number", name="uq_evidence_version_number"),
        Index("ix_evidence_version_tenant_id", "tenant_id"),
        Index("ix_evidence_version_evidence_id", "evidence_id"),
        Index("ix_evidence_version_hash", "content_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash_algorithm: Mapped[str] = mapped_column(String(20), default="sha256", nullable=False)
    encrypted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    encryption_scheme: Mapped[str] = mapped_column(String(40), default="fernet", nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    extension: Mapped[str] = mapped_column(String(20), nullable=False)
    uploaded_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class EvidenceLink(Base):
    """Vínculo polimórfico entre uma evidência e uma linha de artefato tenant-scoped."""

    __tablename__ = "evidence_link"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "evidence_id", "target_type", "target_id", name="uq_evidence_link_target"
        ),
        Index("ix_evidence_link_tenant_id", "tenant_id"),
        Index("ix_evidence_link_evidence_id", "evidence_id"),
        Index("ix_evidence_link_target", "tenant_id", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id"), nullable=False
    )
    target_type: Mapped[SgsiArtifactType] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EvidenceEvent(Base):
    """Evento append-only de cadeia de custódia."""

    __tablename__ = "evidence_event"
    __table_args__ = (
        Index("ix_evidence_event_tenant_id", "tenant_id"),
        Index("ix_evidence_event_evidence_id", "evidence_id"),
        Index("ix_evidence_event_target", "target_type", "target_id"),
        Index("ix_evidence_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id"), nullable=True
    )
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence_version.id"), nullable=True
    )
    link_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence_link.id"), nullable=True
    )
    target_type: Mapped[SgsiArtifactType | None] = mapped_column(
        SAEnum(SgsiArtifactType, native_enum=False, length=30), nullable=True
    )
    target_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


_SQLITE_VERSION_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS evidence_version_no_update BEFORE UPDATE ON evidence_version "
    "BEGIN SELECT RAISE(ABORT, 'evidence_version is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS evidence_version_no_delete BEFORE DELETE ON evidence_version "
    "BEGIN SELECT RAISE(ABORT, 'evidence_version is append-only'); END;",
)
_SQLITE_EVENT_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS evidence_event_no_update BEFORE UPDATE ON evidence_event "
    "BEGIN SELECT RAISE(ABORT, 'evidence_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS evidence_event_no_delete BEFORE DELETE ON evidence_event "
    "BEGIN SELECT RAISE(ABORT, 'evidence_event is append-only'); END;",
)
_PG_VERSION_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_evidence_version_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'evidence_version is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS evidence_version_append_only ON evidence_version;",
    "CREATE TRIGGER evidence_version_append_only BEFORE UPDATE OR DELETE ON evidence_version "
    "FOR EACH ROW EXECUTE FUNCTION wtn_evidence_version_append_only();",
)
_PG_EVENT_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_evidence_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'evidence_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS evidence_event_append_only ON evidence_event;",
    "CREATE TRIGGER evidence_event_append_only BEFORE UPDATE OR DELETE ON evidence_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_evidence_event_append_only();",
)


def _append_only_statements(dialect: str, kind: str) -> tuple[str, ...]:
    if kind == "version":
        return _SQLITE_VERSION_TRIGGERS if dialect == "sqlite" else _PG_VERSION_STATEMENTS if dialect == "postgresql" else ()
    return _SQLITE_EVENT_TRIGGERS if dialect == "sqlite" else _PG_EVENT_STATEMENTS if dialect == "postgresql" else ()


@event.listens_for(EvidenceVersion.__table__, "after_create")
def _create_version_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    for stmt in _append_only_statements(connection.dialect.name, "version"):
        connection.exec_driver_sql(stmt)


@event.listens_for(EvidenceEvent.__table__, "after_create")
def _create_event_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    for stmt in _append_only_statements(connection.dialect.name, "event"):
        connection.exec_driver_sql(stmt)
