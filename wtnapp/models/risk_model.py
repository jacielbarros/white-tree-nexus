"""Registro de risco, tratamento, plano e histórico (Feature 012).

Cenário = ameaça + vulnerabilidade + 0..n ativos. Impacto derivado da CIA (override justificado),
nível pela matriz da metodologia, residual re-pontuado. Plano de Tratamento é Documento Controlado.
Trilha `risk_events` é append-only (triggers SQLite + PostgreSQL).
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
from wtnapp.settings import DocStatus, RiskStatus, RiskTreatmentOption


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Risk(Base):
    """Cenário de risco do SGSI."""

    __tablename__ = "risk"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_risk_tenant_code"),
        Index("ix_risk_tenant_id", "tenant_id"),
        Index("ix_risk_status", "status"),
        Index("ix_risk_owner_user_id", "owner_user_id"),
        Index("ix_risk_inherent_level_key", "inherent_level_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("org_threat.id"), nullable=False
    )
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("org_vulnerability.id"), nullable=False
    )

    probability_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_derived_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_is_override: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    impact_override_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    inherent_level_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    above_acceptance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[RiskStatus] = mapped_column(
        SAEnum(RiskStatus, native_enum=False, length=20),
        default=RiskStatus.identified,
        nullable=False,
    )

    treatment_option: Mapped[RiskTreatmentOption | None] = mapped_column(
        SAEnum(RiskTreatmentOption, native_enum=False, length=20), nullable=True
    )
    treatment_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    residual_probability_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_impact_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    residual_level_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    residual_above_acceptance: Mapped[bool | None] = mapped_column(Boolean, nullable=True)

    acceptance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    accepted_owner_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    accepted_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class RiskAssetLink(Base):
    """Ativo vinculado a um cenário de risco (0..n)."""

    __tablename__ = "risk_asset_link"
    __table_args__ = (
        UniqueConstraint("risk_id", "asset_item_id", name="uq_risk_asset_link"),
        Index("ix_risk_asset_link_tenant_id", "tenant_id"),
        Index("ix_risk_asset_link_risk_id", "risk_id"),
        Index("ix_risk_asset_link_asset_item_id", "asset_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    risk_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("risk.id"), nullable=False)
    asset_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class RiskTreatmentControl(Base):
    """Controle selecionado no tratamento (vínculo controle ← risco / insumo da SoA)."""

    __tablename__ = "risk_treatment_control"
    __table_args__ = (
        Index("ix_risk_treatment_control_tenant_id", "tenant_id"),
        Index("ix_risk_treatment_control_risk_id", "risk_id"),
        Index("ix_risk_treatment_control_gap_catalog_item_id", "gap_catalog_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    risk_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("risk.id"), nullable=False)
    gap_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_catalog_item.id"), nullable=True
    )
    custom_control_label: Mapped[str | None] = mapped_column(String(300), nullable=True)
    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class RiskPlan(Base):
    """Plano de Tratamento de Riscos — Documento Controlado (1 por org)."""

    __tablename__ = "risk_plan"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_risk_plan_tenant"),
        Index("ix_risk_plan_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.draft, nullable=False
    )
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class RiskEvent(Base):
    """Trilha append-only de decisões de risco (tabela `risk_events`)."""

    __tablename__ = "risk_events"
    __table_args__ = (
        Index("ix_risk_events_tenant_id", "tenant_id"),
        Index("ix_risk_events_risk_id", "risk_id"),
        Index("ix_risk_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    risk_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("risk.id"), nullable=True
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# --- Trilha append-only de `risk_events` (SQLite + PostgreSQL) ---

_SQLITE_EVENT_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS risk_events_no_update BEFORE UPDATE ON risk_events "
    "BEGIN SELECT RAISE(ABORT, 'risk_events is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS risk_events_no_delete BEFORE DELETE ON risk_events "
    "BEGIN SELECT RAISE(ABORT, 'risk_events is append-only'); END;",
)
_PG_EVENT_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_risk_events_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'risk_events is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS risk_events_append_only ON risk_events;",
    "CREATE TRIGGER risk_events_append_only BEFORE UPDATE OR DELETE ON risk_events "
    "FOR EACH ROW EXECUTE FUNCTION wtn_risk_events_append_only();",
)


def _append_only_statements(dialect: str) -> tuple[str, ...]:
    if dialect == "sqlite":
        return _SQLITE_EVENT_TRIGGERS
    if dialect == "postgresql":
        return _PG_EVENT_STATEMENTS
    return ()


@event.listens_for(RiskEvent.__table__, "after_create")
def _create_risk_event_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    for stmt in _append_only_statements(connection.dialect.name):
        connection.exec_driver_sql(stmt)
