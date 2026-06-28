"""Metodologia de risco — uma configuração por organização (Feature 012).

Escalas (prob/impacto), matriz prob×impacto → nível, critério de aceitação por nível e mapa
CIA→impacto vivem em colunas JSON. Quando a org não tem linha, o serviço usa o default 5x5.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RiskMethodology(Base):
    """Configuração de metodologia de risco (1 por org)."""

    __tablename__ = "risk_methodology"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_risk_methodology_tenant"),
        Index("ix_risk_methodology_tenant_id", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    is_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    probability_scale: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    impact_scale: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_levels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_matrix: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    acceptance: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    cia_impact_map: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
