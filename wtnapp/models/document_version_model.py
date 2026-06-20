"""Versoes imutaveis de documentos controlados SGSI."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum as SAEnum, ForeignKey, Integer, String, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.models.context_common import now_utc
from wtnapp.settings import Classification, DocStatus, DocType


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), index=True, nullable=False
    )
    document_type: Mapped[DocType] = mapped_column(
        SAEnum(DocType, native_enum=False, length=40), index=True, nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), index=True, nullable=False)
    identifier: Mapped[str] = mapped_column(String(40), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[DocStatus] = mapped_column(
        SAEnum(DocStatus, native_enum=False, length=20), default=DocStatus.in_force, nullable=False
    )
    classification: Mapped[Classification] = mapped_column(
        SAEnum(Classification, native_enum=False, length=30),
        default=Classification.uso_interno,
        nullable=False,
    )
    emitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, nullable=False)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    elaborated_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    change_nature: Mapped[str] = mapped_column(String(300), nullable=False, default="Emissao inicial")
    content_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS document_versions_no_update BEFORE UPDATE ON document_versions "
    "BEGIN SELECT RAISE(ABORT, 'document_versions is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS document_versions_no_delete BEFORE DELETE ON document_versions "
    "BEGIN SELECT RAISE(ABORT, 'document_versions is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_document_versions_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'document_versions is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS document_versions_append_only ON document_versions;",
    "CREATE TRIGGER document_versions_append_only BEFORE UPDATE OR DELETE ON document_versions "
    "FOR EACH ROW EXECUTE FUNCTION wtn_document_versions_append_only();",
)


@event.listens_for(DocumentVersion.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in statements:
        connection.exec_driver_sql(stmt)
