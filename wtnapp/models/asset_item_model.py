"""Gestão de Ativos / Processos / Escopo (Feature 011).

Inventário tenant-scoped: itens (ativos/processos/escopo), relacionamentos flexíveis entre itens,
vínculo a gaps do catálogo da org e trilha de histórico append-only por item.
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
    String,
    Text,
    UniqueConstraint,
    Uuid,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import (
    AssetRecordStatus,
    AssetRelationshipType,
    AssetScopeStatus,
    AssetType,
    CiaLevel,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AssetItem(Base):
    """Item de ativo/processo/escopo do SGSI."""

    __tablename__ = "asset_items"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_asset_items_tenant_code"),
        Index("ix_asset_items_tenant_id", "tenant_id"),
        Index("ix_asset_items_item_type", "item_type"),
        Index("ix_asset_items_scope_status", "scope_status"),
        Index("ix_asset_items_responsible_user_id", "responsible_user_id"),
        Index("ix_asset_items_next_review_at", "next_review_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    item_type: Mapped[AssetType] = mapped_column(
        SAEnum(AssetType, native_enum=False, length=30), nullable=False
    )
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    business_unit: Mapped[str | None] = mapped_column(String(160), nullable=True)

    responsible_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    custodian_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    record_status: Mapped[AssetRecordStatus] = mapped_column(
        SAEnum(AssetRecordStatus, native_enum=False, length=20),
        default=AssetRecordStatus.active,
        nullable=False,
    )
    scope_status: Mapped[AssetScopeStatus] = mapped_column(
        SAEnum(AssetScopeStatus, native_enum=False, length=20), nullable=False
    )
    scope_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)

    related_system_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=True
    )
    related_process_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=True
    )
    related_supplier_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=True
    )

    has_personal_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_sensitive_data: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    compliance_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    confidentiality: Mapped[CiaLevel | None] = mapped_column(
        SAEnum(CiaLevel, native_enum=False, length=20), nullable=True
    )
    integrity: Mapped[CiaLevel | None] = mapped_column(
        SAEnum(CiaLevel, native_enum=False, length=20), nullable=True
    )
    availability: Mapped[CiaLevel | None] = mapped_column(
        SAEnum(CiaLevel, native_enum=False, length=20), nullable=True
    )
    criticality: Mapped[CiaLevel | None] = mapped_column(
        SAEnum(CiaLevel, native_enum=False, length=20), nullable=True
    )
    criticality_is_manual: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    last_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    context_origin_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    context_origin_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)

    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    archived_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class AssetRelationship(Base):
    """Relacionamento direcional entre dois itens do mesmo tenant."""

    __tablename__ = "asset_relationships"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "source_item_id", "relationship_type", "target_item_id",
            name="uq_asset_relationship",
        ),
        Index("ix_asset_relationships_tenant_id", "tenant_id"),
        Index("ix_asset_relationships_source_item_id", "source_item_id"),
        Index("ix_asset_relationships_target_item_id", "target_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    source_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    relationship_type: Mapped[AssetRelationshipType] = mapped_column(
        SAEnum(AssetRelationshipType, native_enum=False, length=30), nullable=False
    )
    target_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class AssetGapLink(Base):
    """Vínculo entre um item e um gap do catálogo da organização."""

    __tablename__ = "asset_gap_links"
    __table_args__ = (
        UniqueConstraint("tenant_id", "item_id", "gap_catalog_item_id", name="uq_asset_gap_link"),
        Index("ix_asset_gap_links_tenant_id", "tenant_id"),
        Index("ix_asset_gap_links_item_id", "item_id"),
        Index("ix_asset_gap_links_gap_catalog_item_id", "gap_catalog_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    gap_catalog_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_catalog_item.id"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class AssetItemEvent(Base):
    """Trilha de histórico append-only de alterações relevantes de um item."""

    __tablename__ = "asset_item_events"
    __table_args__ = (
        Index("ix_asset_item_events_tenant_id", "tenant_id"),
        Index("ix_asset_item_events_item_id", "item_id"),
        Index("ix_asset_item_events_event_type", "event_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)


# --- Trilha append-only de eventos do item (SQLite + PostgreSQL) ---

_SQLITE_EVENT_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS asset_item_events_no_update BEFORE UPDATE ON asset_item_events "
    "BEGIN SELECT RAISE(ABORT, 'asset_item_events is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS asset_item_events_no_delete BEFORE DELETE ON asset_item_events "
    "BEGIN SELECT RAISE(ABORT, 'asset_item_events is append-only'); END;",
)
_PG_EVENT_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_asset_item_events_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'asset_item_events is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS asset_item_events_append_only ON asset_item_events;",
    "CREATE TRIGGER asset_item_events_append_only BEFORE UPDATE OR DELETE ON asset_item_events "
    "FOR EACH ROW EXECUTE FUNCTION wtn_asset_item_events_append_only();",
)


def _append_only_statements(dialect: str) -> tuple[str, ...]:
    if dialect == "sqlite":
        return _SQLITE_EVENT_TRIGGERS
    if dialect == "postgresql":
        return _PG_EVENT_STATEMENTS
    return ()


@event.listens_for(AssetItemEvent.__table__, "after_create")
def _create_event_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    for stmt in _append_only_statements(connection.dialect.name):
        connection.exec_driver_sql(stmt)
