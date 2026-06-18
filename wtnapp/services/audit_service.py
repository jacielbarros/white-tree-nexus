"""AuditService — trilha append-only com sessão própria (persiste mesmo em rollback).

Falha em silêncio (loga warning) — auditoria nunca derruba a operação principal.
NUNCA passar senhas, tokens, chaves ou PII de conteúdo em `details`.
"""

import logging
import uuid
from typing import Any

from wtnapp.settings import AuditOutcome

logger = logging.getLogger(__name__)


class AuditService:
    @staticmethod
    def log_from_request(
        *,
        operation: str,
        request: Any = None,
        outcome: AuditOutcome | str = AuditOutcome.success,
        actor_user_id: uuid.UUID | None = None,
        actor_role: str | None = None,
        tenant_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | uuid.UUID | None = None,
        details: dict | None = None,
    ) -> None:
        # Import tardio: usa a SessionLocal corrente (testes podem reapontar o engine).
        from wtnapp.database import database
        from wtnapp.models.audit_log_model import AuditLog

        ip = user_agent = None
        if request is not None:
            try:
                ip = request.client.host if request.client else None
                user_agent = request.headers.get("user-agent")
            except Exception:  # pragma: no cover - defensivo
                pass

        outcome_value = outcome.value if isinstance(outcome, AuditOutcome) else str(outcome)
        session = database.SessionLocal()
        try:
            session.add(
                AuditLog(
                    operation=operation,
                    outcome=outcome_value,
                    actor_user_id=actor_user_id,
                    actor_role=actor_role,
                    tenant_id=tenant_id,
                    entity_type=entity_type,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    ip=ip,
                    user_agent=user_agent,
                    details=details,
                )
            )
            session.commit()
        except Exception:
            logger.warning("falha ao gravar audit log (operation=%s)", operation, exc_info=True)
            session.rollback()
        finally:
            session.close()
