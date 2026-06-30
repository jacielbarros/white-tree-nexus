"""Análise Crítica pela Direção (cláusula 9.3) — Feature 015 / 5b.

Coleção: **uma por reunião**. Documento Controlado — versões imutáveis em `document_versions`
(`DocType.management_review`) via `current_version_id` + `draft_status` (padrão SoA/risk plan/audit
report). Sem trilha própria (usa `document_versions` + audit logs).
"""

import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Enum as SAEnum, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import DocStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ManagementReview(Base):
    """Ata de análise crítica de uma reunião (Documento Controlado)."""

    __tablename__ = "management_review"
    __table_args__ = (
        Index("ix_management_review_tenant_id", "tenant_id"),
        Index("ix_management_review_date", "review_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    review_date: Mapped[date] = mapped_column(Date, nullable=False)
    inputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    # Ponteiro p/ versão em vigor (contrato de `controlled_document_service.approve_document`).
    current_version_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    draft_status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.draft, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now, nullable=False)
