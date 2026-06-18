"""AuditLog — trilha append-only. NUNCA contém senhas/tokens/chaves/PII de conteúdo."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Uuid, event
from sqlalchemy.orm import Mapped, mapped_column

from wtnapp.models.base import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True)
    actor_role: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # Contexto de tenant; NULL para eventos de plataforma (ex.: bootstrap).
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), index=True, nullable=True)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str | None] = mapped_column(String(60), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(String(10), nullable=False)
    # Metadados de SEGURANÇA forense (não conteúdo/PII do tenant) — ver spec SEC-003.
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, index=True)


# --- Append-only (FR-031): bloqueia UPDATE/DELETE no nível do banco (SQLite + PostgreSQL) ---
_SQLITE_TRIGGERS = (
    "CREATE TRIGGER IF NOT EXISTS audit_logs_no_update BEFORE UPDATE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;",
    "CREATE TRIGGER IF NOT EXISTS audit_logs_no_delete BEFORE DELETE ON audit_logs "
    "BEGIN SELECT RAISE(ABORT, 'audit_logs is append-only'); END;",
)
_PG_STATEMENTS = (
    "CREATE OR REPLACE FUNCTION wtn_audit_append_only() RETURNS trigger AS $$ "
    "BEGIN RAISE EXCEPTION 'audit_logs is append-only'; END; $$ LANGUAGE plpgsql;",
    "DROP TRIGGER IF EXISTS audit_logs_append_only ON audit_logs;",
    "CREATE TRIGGER audit_logs_append_only BEFORE UPDATE OR DELETE ON audit_logs "
    "FOR EACH ROW EXECUTE FUNCTION wtn_audit_append_only();",
)


@event.listens_for(AuditLog.__table__, "after_create")
def _create_append_only_triggers(target, connection, **kw):  # pragma: no cover - infra
    dialect = connection.dialect.name
    statements = _SQLITE_TRIGGERS if dialect == "sqlite" else _PG_STATEMENTS if dialect == "postgresql" else ()
    for stmt in statements:
        connection.exec_driver_sql(stmt)
