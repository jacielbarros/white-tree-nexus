"""Indicadores simples do módulo NC/Ações Corretivas + Melhoria (Feature 015, US7).

Contagens/agrupamentos tenant-scoped — sem motor de KPIs (9.1 fora de escopo).
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext, scoped_query
from wtnapp.models.improvement_model import Improvement
from wtnapp.models.nonconformity_model import CorrectiveAction, NonConformity
from wtnapp.services import nonconformity_service as nc_svc


def _counts(query, column) -> dict[str, int]:
    return {str(getattr(v, "value", v)): c for v, c in query.group_by(column).with_entities(column, func.count()).all()}


def build_metrics(db: Session, ctx: OrgContext) -> dict:
    nc_by_status = _counts(scoped_query(db, NonConformity, ctx), NonConformity.status)
    nc_by_severity = _counts(scoped_query(db, NonConformity, ctx), NonConformity.severity)
    overdue_actions = sum(1 for a in scoped_query(db, CorrectiveAction, ctx).all() if nc_svc.is_overdue(a))
    improvements_by_status = _counts(scoped_query(db, Improvement, ctx), Improvement.status)
    return {
        "nc_by_status": nc_by_status,
        "nc_by_severity": nc_by_severity,
        "overdue_actions": overdue_actions,
        "improvements_by_status": improvements_by_status,
    }
