"""FormTemplate — template parametrizavel de formulario por organizacao."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, JSON, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import FormKind, TemplateStatus


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FormTemplate(Base):
    __tablename__ = "form_templates"
    __table_args__ = (
        Index("ix_form_templates_tenant_id", "tenant_id"),
        Index("ix_form_templates_kind", "kind"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    kind: Mapped[FormKind] = mapped_column(
        SAEnum(FormKind, native_enum=False, length=20), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    schema: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[TemplateStatus] = mapped_column(
        SAEnum(TemplateStatus, native_enum=False, length=20),
        default=TemplateStatus.draft,
        nullable=False,
    )
    created_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
