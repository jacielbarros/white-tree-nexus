"""Catálogos de ameaças e vulnerabilidades (Feature 012).

Padrão do Gap: semente compartilhada de plataforma (sem `tenant_id`, somente leitura) + cópia
editável por organização (tenant-scoped) + vínculos a ativos do módulo de Ativos.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
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
)
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import ThreatCategory, ThreatOrigin, VulnerabilityCategory


def _now() -> datetime:
    return datetime.now(timezone.utc)


# --- Sementes de plataforma (SEM tenant_id — conteúdo compartilhado, somente leitura) ---


class ThreatSeedItem(Base):
    __tablename__ = "threat_seed_item"
    __table_args__ = (UniqueConstraint("code", name="uq_threat_seed_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ThreatCategory] = mapped_column(
        SAEnum(ThreatCategory, native_enum=False, length=20), nullable=False
    )
    origin: Mapped[ThreatOrigin | None] = mapped_column(
        SAEnum(ThreatOrigin, native_enum=False, length=20), nullable=True
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class VulnerabilitySeedItem(Base):
    __tablename__ = "vulnerability_seed_item"
    __table_args__ = (UniqueConstraint("code", name="uq_vulnerability_seed_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[VulnerabilityCategory] = mapped_column(
        SAEnum(VulnerabilityCategory, native_enum=False, length=20), nullable=False
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


# --- Cópia editável por organização (tenant-scoped + RLS) ---


class OrgThreat(Base):
    __tablename__ = "org_threat"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_threat_tenant_code"),
        Index("ix_org_threat_tenant_id", "tenant_id"),
        Index("ix_org_threat_seed_item_id", "seed_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    seed_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("threat_seed_item.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[ThreatCategory] = mapped_column(
        SAEnum(ThreatCategory, native_enum=False, length=20), nullable=False
    )
    origin: Mapped[ThreatOrigin | None] = mapped_column(
        SAEnum(ThreatOrigin, native_enum=False, length=20), nullable=True
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


class OrgVulnerability(Base):
    __tablename__ = "org_vulnerability"
    __table_args__ = (
        UniqueConstraint("tenant_id", "code", name="uq_org_vulnerability_tenant_code"),
        Index("ix_org_vulnerability_tenant_id", "tenant_id"),
        Index("ix_org_vulnerability_seed_item_id", "seed_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    seed_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("vulnerability_seed_item.id"), nullable=True
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[VulnerabilityCategory] = mapped_column(
        SAEnum(VulnerabilityCategory, native_enum=False, length=20), nullable=False
    )
    gap_catalog_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_catalog_item.id"), nullable=True
    )
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    archive_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )


# --- Vínculos a ativos (alimentam os placeholders do detalhe do ativo) ---


class AssetThreatLink(Base):
    __tablename__ = "asset_threat_link"
    __table_args__ = (
        UniqueConstraint("tenant_id", "asset_item_id", "threat_id", name="uq_asset_threat_link"),
        Index("ix_asset_threat_link_tenant_id", "tenant_id"),
        Index("ix_asset_threat_link_asset_item_id", "asset_item_id"),
        Index("ix_asset_threat_link_threat_id", "threat_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    asset_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    threat_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("org_threat.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class AssetVulnerabilityLink(Base):
    __tablename__ = "asset_vulnerability_link"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "asset_item_id", "vulnerability_id", name="uq_asset_vulnerability_link"
        ),
        Index("ix_asset_vulnerability_link_tenant_id", "tenant_id"),
        Index("ix_asset_vulnerability_link_asset_item_id", "asset_item_id"),
        Index("ix_asset_vulnerability_link_vulnerability_id", "vulnerability_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    asset_item_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("asset_items.id"), nullable=False
    )
    vulnerability_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("org_vulnerability.id"), nullable=False
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
