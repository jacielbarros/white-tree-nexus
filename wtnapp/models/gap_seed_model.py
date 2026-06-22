"""Gap Analysis — tabelas de seed da plataforma (compartilhadas, sem tenant_id, somente leitura)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, Index, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import GapDimension, GapTheme


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapSeedVersion(Base):
    __tablename__ = "gap_seed_version"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class GapSeedItem(Base):
    __tablename__ = "gap_seed_item"
    __table_args__ = (
        UniqueConstraint("seed_version_id", "ref_code", name="uq_gap_seed_item_version_ref"),
        Index("ix_gap_seed_item_seed_version_id", "seed_version_id"),
        Index("ix_gap_seed_item_dimension", "dimension"),
        Index("ix_gap_seed_item_theme", "theme"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seed_version_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), nullable=False
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
    # Orientação de avaliação (Feature 007) — conteúdo de plataforma, PT-BR original.
    referencia: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    como_avaliar: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    evidencias_esperadas: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
