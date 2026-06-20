"""FormSignaturePolicy — politica de assinatura configuravel por organizacao (1 por org)."""

import uuid

from sqlalchemy import Boolean, ForeignKey, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


class FormSignaturePolicy(Base):
    __tablename__ = "form_signature_policies"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), unique=True, nullable=False
    )
    # False = assinatura unica do preenchedor (padrao); True = exige contra-assinatura do atribuidor
    require_assigner_countersignature: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
