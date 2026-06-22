"""Dashboard de Conformidade (Feature 006) — endpoint único de leitura agregada.

Read-only, tenant-scoped. Sem audit log no caminho de sucesso (decisão SEC-003): a home é carregada
a cada navegação; tentativas não autorizadas já são auditadas pelas dependencies centrais
(`get_org_context` ⇒ CROSS_TENANT_DENIED; `require_permission` ⇒ PERMISSION_DENIED).
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from wtnapp.database.database import get_db
from wtnapp.helpers.permissions import require_permission
from wtnapp.helpers.tenant_scope import OrgContext
from wtnapp.schemas.dashboard_schema import DashboardResponse
from wtnapp.services.dashboard_service import build_dashboard

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

db_dep = Annotated[Session, Depends(get_db)]
view_dep = Annotated[OrgContext, Depends(require_permission("view_dashboard"))]


@router.get("", response_model=DashboardResponse)
def get_dashboard(db: db_dep, ctx: view_dep) -> DashboardResponse:
    return build_dashboard(db, ctx)
