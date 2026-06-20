"""FormSignature — assinatura eletronica avancada (append-only) e OTP transiente."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum as SAEnum, ForeignKey, Index, Integer, String, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import SignerRole


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FormSignature(Base):
    __tablename__ = "form_signatures"
    __table_args__ = (
        Index("ix_form_signatures_tenant_id", "tenant_id"),
        Index("ix_form_signatures_assignment_id", "assignment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("form_assignments.id"), nullable=False
    )
    signer_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    signer_role: Mapped[SignerRole] = mapped_column(
        SAEnum(SignerRole, native_enum=False, length=20), nullable=False
    )
    signer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    algorithm: Mapped[str] = mapped_column(String(20), default="sha256", nullable=False)
    level: Mapped[str] = mapped_column(String(20), default="advanced", nullable=False)
    otp_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)


class FormSignatureOTP(Base):
    """OTP transiente para assinatura de respondente externo — nao e append-only."""

    __tablename__ = "form_signature_otps"
    __table_args__ = (Index("ix_form_signature_otps_assignment_id", "assignment_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("form_assignments.id"), nullable=False, unique=True
    )
    # hash do OTP — nunca o valor em claro
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS form_signatures_no_update "
    "BEFORE UPDATE ON form_signatures "
    "BEGIN SELECT RAISE(ABORT, 'form_signatures is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS form_signatures_no_delete "
    "BEFORE DELETE ON form_signatures "
    "BEGIN SELECT RAISE(ABORT, 'form_signatures is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_form_signatures_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'form_signatures is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS form_signatures_append_only ON form_signatures;",
    "CREATE TRIGGER form_signatures_append_only "
    "BEFORE UPDATE OR DELETE ON form_signatures "
    "FOR EACH ROW EXECUTE FUNCTION wtn_form_signatures_append_only();",
)


@event.listens_for(FormSignature.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = (
        _SQLITE_TRIGGERS if dialect == "sqlite"
        else _PG_STATEMENTS if dialect == "postgresql"
        else ()
    )
    for stmt in statements:
        connection.exec_driver_sql(stmt)
