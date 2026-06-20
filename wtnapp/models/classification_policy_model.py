"""Politica por organizacao para restringir leitura por classificacao."""

import uuid

from sqlalchemy import JSON, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


class ClassificationAccessPolicy(Base):
    __tablename__ = "classification_access_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, index=True, nullable=False
    )
    rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
