"""Integração do motor de formulários com o Diagnóstico (US5 — T029).

Quando uma FormAssignment do kind=diagnostic é concluída (status=completed),
este serviço persiste as respostas como a seção "form_intake" do Diagnostic vigente.

Fail-soft: nao levanta excecao para nao bloquear a conclusao da atribuicao.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.form_assignment_model import FormAssignment
from wtnapp.services.audit_service import AuditService
from wtnapp.settings import AuditOutcome, DiagnosticStatus, FormKind

logger = logging.getLogger(__name__)


def apply_diagnostic_intake(
    db: Session,
    assignment: FormAssignment,
    actor_user_id=None,
    request=None,
) -> None:
    """Converte respostas de diagnóstico concluídas no Diagnostic vigente da org.

    Idempotente: reaplicar com o mesmo assignment_id substitui a secao form_intake.
    """
    if assignment.kind != FormKind.diagnostic:
        return

    try:
        intake_section = {
            "source": "form_assignment",
            "assignment_id": str(assignment.id),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "answers": assignment.answers or {},
        }

        diagnostic = db.query(Diagnostic).filter(
            Diagnostic.tenant_id == assignment.tenant_id
        ).first()

        if diagnostic is None:
            diagnostic = Diagnostic(
                tenant_id=assignment.tenant_id,
                status=DiagnosticStatus.completed,
                sections={"form_intake": intake_section},
                updated_by=actor_user_id,
            )
            db.add(diagnostic)
        else:
            sections = dict(diagnostic.sections or {})
            sections["form_intake"] = intake_section
            diagnostic.sections = sections
            diagnostic.status = DiagnosticStatus.completed
            diagnostic.updated_by = actor_user_id

        db.commit()

        if request and actor_user_id:
            AuditService.log_from_request(
                request=request,
                operation="DIAGNOSTIC_INTAKE",
                outcome=AuditOutcome.success,
                actor_user_id=actor_user_id,
                tenant_id=assignment.tenant_id,
                entity_type="diagnostic",
                entity_id=str(diagnostic.id) if diagnostic.id else None,
                details={"source_assignment": str(assignment.id)},
            )
    except Exception:
        logger.warning(
            "diagnostic_intake falhou (best-effort) para assignment %s",
            assignment.id,
            exc_info=True,
        )
