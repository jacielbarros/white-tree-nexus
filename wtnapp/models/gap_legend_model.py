"""Gap Analysis — legenda global de Status/Prioridade (Feature 007).

Conteúdo de **plataforma** (sem `tenant_id`, somente leitura para a org, editável pelo Super Admin).
Definições objetivas das escalas, exibidas na tela do Gap para reduzir subjetividade.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapLegendEntry(Base):
    __tablename__ = "gap_legend_entry"
    __table_args__ = (
        UniqueConstraint("kind", "code", name="uq_gap_legend_kind_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)  # 'status' | 'priority'
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    label: Mapped[str] = mapped_column(String(60), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
