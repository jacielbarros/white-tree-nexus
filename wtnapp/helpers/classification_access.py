"""Checagem central de acesso por classificacao, complementar ao RBAC."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.models.classification_policy_model import ClassificationAccessPolicy
from wtnapp.settings import Classification


def can_read_classification(db: Session, ctx: OrgContext, classification: Classification | str | None) -> bool:
    policy = db.query(ClassificationAccessPolicy).filter(ClassificationAccessPolicy.tenant_id == ctx.tenant_id).first()
    if policy is None or not policy.rules or classification is None:
        return True
    allowed = policy.rules.get(str(classification.value if isinstance(classification, Classification) else classification))
    return allowed is None or ctx.role.value in allowed


def require_classification_read(db: Session, ctx: OrgContext, classification: Classification | str | None) -> None:
    if not can_read_classification(db, ctx, classification):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permissao insuficiente para a classificacao.")
