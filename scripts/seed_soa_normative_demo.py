#!/usr/bin/env python
r"""Seed idempotente de um cenário E2E para a SoA Normativa (Feature 013).

Promove o cenário do Módulo de Riscos (Feature 012) à Declaração de Aplicabilidade normativa:
1. garante o cenário de risco (reusa `scripts/seed_risk_demo.py` — org `risco-demo` com 1 risco
   em tratamento cujo controle vem do catálogo de Gap do Anexo A);
2. aprova o Plano de Tratamento de Riscos (gate duro → versão vigente in-force), de modo que a SoA
   possa ser emitida como **normativa (6.1.3 d)**;
3. consolida a SoA (passo Gap + passo dirigido por risco) e imprime os controles dirigidos por risco
   (razão `risk_treatment` + riscos estruturados `risk_links`) e o estado do gate (readiness).

Tudo é idempotente: rodar de novo não duplica nem quebra o estado existente.

Uso (raiz do projeto):
    .\.venv\Scripts\python.exe scripts\seed_soa_normative_demo.py
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from wtnapp.database.database import SessionLocal  # noqa: E402
from wtnapp.helpers.tenant_scope import OrgContext, Principal  # noqa: E402
from wtnapp.models.organization_model import Organization  # noqa: E402
from wtnapp.models.risk_model import RiskPlan  # noqa: E402
from wtnapp.models.soa_model import SoaItem  # noqa: E402
from wtnapp.models.user_model import User  # noqa: E402
from wtnapp.services import risk_treatment_service, soa_consolidation_service  # noqa: E402
from wtnapp.settings import DocStatus, Role  # noqa: E402

SLUG = "risco-demo"
EMAIL = "riscodemo@example.com"
PASSWORD = "Sup3rSecret!2345"


def _ctx(org_id, user) -> OrgContext:
    principal = Principal(user=user, jti="seed", exp_ts=0, tenant_ids=[org_id], is_super_admin=False)
    return OrgContext(principal=principal, tenant_id=org_id, role=Role.org_admin, is_super_admin=False, membership=None)


def _ensure_risk_scenario() -> int:
    """Reusa o seed do Módulo de Riscos (idempotente)."""
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "seed_risk_demo.py")],
        capture_output=True, text=True,
    )
    sys.stdout.write(proc.stdout)
    if proc.returncode != 0:
        sys.stderr.write(proc.stderr)
    return proc.returncode


def _approve_risk_plan(db, ctx) -> str:
    """Garante um Plano de Tratamento aprovado vigente (idempotente)."""
    plan = db.query(RiskPlan).filter_by(tenant_id=ctx.tenant_id).first()
    if plan is not None and plan.current_version_id is not None:
        return "já aprovado (vigente)"
    if plan is None or plan.draft_status == DocStatus.draft:
        risk_treatment_service.submit_plan(db, ctx)
    risk_treatment_service.approve_plan(db, ctx, {"change_nature": "Aprovação inicial do Plano (seed 013)"})
    return "aprovado nesta execução"


def main() -> int:
    if _ensure_risk_scenario() != 0:
        print("ERRO: falha ao preparar o cenário de risco.")
        return 1

    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=SLUG).first()
        user = db.query(User).filter_by(email=EMAIL).first()
        if org is None or user is None:
            print("ERRO: organização/usuário demo não encontrados.")
            return 1
        ctx = _ctx(org.id, user)

        plan_state = _approve_risk_plan(db, ctx)

        result = soa_consolidation_service.consolidate(db, org.id)

        # Filtra em Python (json não tem operador de comparação no Postgres).
        risk_items = [
            it
            for it in db.query(SoaItem)
            .filter(SoaItem.tenant_id == org.id)
            .order_by(SoaItem.ref_code)
            .all()
            if it.risk_links
        ]
        approved = bool(
            (db.query(RiskPlan).filter_by(tenant_id=org.id).first() or RiskPlan()).current_version_id
        )

        print()
        print("=== SoA Normativa (Feature 013) — seed E2E ===")
        print(f"org={org.slug} ({org.id})  admin={EMAIL}  senha={PASSWORD}")
        print(f"Plano de Tratamento de Riscos: {plan_state}")
        print(
            f"Consolidação: added={result['added']} preserved={result['preserved']} "
            f"risk_applied={result['risk_applied']} out_of_scope={result['out_of_scope']}"
        )
        print(f"Gate da esteira: {'SoA NORMATIVA (6.1.3 d)' if approved else 'Pré-SoA (consolidação do Gap)'}")
        print(f"Controles dirigidos por risco: {len(risk_items)}")
        for it in risk_items:
            codes = ", ".join(rl.get("risk_code") for rl in (it.risk_links or []))
            print(f"  - {it.ref_code}: aplicável={it.applicable} razões={it.inclusion_reasons} riscos=[{codes}]")
        print()
        print("Abra /app/soa (login acima) para ver a matriz, o banner Pré-SoA × normativa e emitir a versão.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
