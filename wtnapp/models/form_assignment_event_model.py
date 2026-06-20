"""FormAssignmentEvent — trilha append-only de cada evento do workflow por atribuicao."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Index, String, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base
from wtnapp.settings import AssignmentEventType


def _now() -> datetime:
    return datetime.now(timezone.utc)


class FormAssignmentEvent(Base):
    __tablename__ = "form_assignment_events"
    __table_args__ = (
        Index("ix_form_assignment_events_tenant_id", "tenant_id"),
        Index("ix_form_assignment_events_assignment_id", "assignment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    assignment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("form_assignments.id"), nullable=False
    )
    event: Mapped[AssignmentEventType] = mapped_column(
        SAEnum(AssignmentEventType, native_enum=False, length=30), nullable=False
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    actor_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS form_assignment_events_no_update "
    "BEFORE UPDATE ON form_assignment_events "
    "BEGIN SELECT RAISE(ABORT, 'form_assignment_events is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS form_assignment_events_no_delete "
    "BEFORE DELETE ON form_assignment_events "
    "BEGIN SELECT RAISE(ABORT, 'form_assignment_events is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_form_assignment_events_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'form_assignment_events is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS form_assignment_events_append_only ON form_assignment_events;",
    "CREATE TRIGGER form_assignment_events_append_only "
    "BEFORE UPDATE OR DELETE ON form_assignment_events "
    "FOR EACH ROW EXECUTE FUNCTION wtn_form_assignment_events_append_only();",
)


@event.listens_for(FormAssignmentEvent.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = (
        _SQLITE_TRIGGERS if dialect == "sqlite"
        else _PG_STATEMENTS if dialect == "postgresql"
        else ()
    )
    for stmt in statements:
        connection.exec_driver_sql(stmt)
