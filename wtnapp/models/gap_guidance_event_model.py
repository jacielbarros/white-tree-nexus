"""Gap Analysis — trilha append-only de edições de orientação/legenda (Feature 007).

Conteúdo de **plataforma** (sem `tenant_id`). Registra cada alteração feita pelo Super Admin
(antes→depois), imutável: gatilhos bloqueiam UPDATE/DELETE (SQLite + PostgreSQL).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Index, String, Text, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class GapGuidanceEvent(Base):
    __tablename__ = "gap_guidance_event"
    __table_args__ = (
        Index("ix_gap_guidance_event_target", "target_type", "target_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'seed_item' | 'legend'
    target_id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    field: Mapped[str] = mapped_column(String(40), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS gap_guidance_event_no_update BEFORE UPDATE ON gap_guidance_event "
    "BEGIN SELECT RAISE(ABORT, 'gap_guidance_event is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS gap_guidance_event_no_delete BEFORE DELETE ON gap_guidance_event "
    "BEGIN SELECT RAISE(ABORT, 'gap_guidance_event is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_gap_guidance_event_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'gap_guidance_event is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS gap_guidance_event_append_only ON gap_guidance_event;",
    "CREATE TRIGGER gap_guidance_event_append_only BEFORE UPDATE OR DELETE ON gap_guidance_event "
    "FOR EACH ROW EXECUTE FUNCTION wtn_gap_guidance_event_append_only();",
)


@event.listens_for(GapGuidanceEvent.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in statements:
        connection.exec_driver_sql(stmt)
