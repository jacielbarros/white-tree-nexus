"""DTOs de leitura do Dashboard de Conformidade (Feature 006).

Camada de agregação — não há entidade de domínio nova. Estes schemas descrevem o payload do
endpoint `GET /dashboard`, composto a partir dos módulos existentes (Contexto, Gap, SoA).
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel


class DashboardCardStatus(str, Enum):
    """Vocabulário normalizado de status de card (research D4)."""

    not_started = "not_started"
    draft = "draft"
    in_review = "in_review"
    in_force = "in_force"
    needs_review = "needs_review"  # aprovado, porém análise crítica vencida
    error = "error"  # falha ao agregar este módulo (fail-open por card)


class DashboardModuleId(str, Enum):
    context = "context"
    gap = "gap"
    soa = "soa"
    risk = "risk"  # Gestão de Riscos (Feature 012)
    internal_audit = "internal_audit"  # Evidências & Auditoria Interna (Feature 014)
    action_plan = "action_plan"  # placeholder (Módulo 5b)
    evidence = "evidence"  # placeholder legado (compat)


class NextAction(BaseModel):
    label: str
    route: str
    fragment: Optional[str] = None


class ModuleCard(BaseModel):
    id: DashboardModuleId
    title: str
    status: DashboardCardStatus
    progress_pct: Optional[float] = None
    responsible: Optional[str] = None
    deadline: Optional[date] = None
    overdue: bool = False
    next_action: NextAction
    not_started: bool = False
    placeholder: bool = False


class DashboardKpis(BaseModel):
    # Conformidade consolidada da JORNADA COMPLETA (cláusulas 4–10 + Anexo A) — número-âncora.
    overall_adherence: Optional[float] = None  # 0–1
    controls_evaluated: int = 0                 # itens avaliados (jornada completa)
    controls_total: int = 0                     # total de itens da jornada
    # Decomposição da conformidade consolidada por dimensão (para não mascarar).
    conformance_clause: Optional[float] = None
    conformance_annex: Optional[float] = None
    critical_gaps: int = 0
    modules_approved: int = 0
    modules_total: int = 0


class AdherencePoint(BaseModel):
    date: date
    adherence: float  # 0–1
    version: int


class DashboardResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    kpis: DashboardKpis
    cards: list[ModuleCard]
    adherence_trend: Optional[list[AdherencePoint]] = None  # P2; null se < 2 baselines
    generated_at: datetime
