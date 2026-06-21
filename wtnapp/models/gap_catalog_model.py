"""Gap Analysis — catálogo editável por organização (cópia da org do seed)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import GapDimension, GapTheme


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapCatalogItem(Base):
    __tablename__ = "gap_catalog_item"
    __table_args__ = (
        UniqueConstraint("tenant_id", "ref_code", name="uq_gap_catalog_item_tenant_ref"),
        Index("ix_gap_catalog_item_tenant_id", "tenant_id"),
        Index("ix_gap_catalog_item_dimension", "dimension"),
        Index("ix_gap_catalog_item_theme", "theme"),
        Index("ix_gap_catalog_item_seed_item_id", "seed_item_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    seed_item_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("gap_seed_item.id"), nullable=True
    )
    dimension: Mapped[GapDimension] = mapped_column(
        SAEnum(GapDimension, native_enum=False, length=20), nullable=False
    )
    ref_code: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    theme: Mapped[GapTheme | None] = mapped_column(
        SAEnum(GapTheme, native_enum=False, length=20), nullable=True
    )
    objective: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_discontinued: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    group_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
