#!/usr/bin/env python
r"""Seed idempotente de um cenário E2E para o Módulo de Riscos (Feature 012).

Cria (se ainda não existir) uma organização demo com um Admin, o Gap Analysis adotado (para os
controles do Anexo A), os catálogos de ameaças/vulnerabilidades adotados, alguns ativos com CIA e
um punhado de riscos avaliados — um deles já em tratamento (mitigar) com controle do catálogo de Gap.

Reaproveita os serviços do módulo (geração de código `RSK-####`, derivação de impacto da CIA e
cálculo de nível pela metodologia 5x5 padrão).

Uso (raiz do projeto):
    .\.venv\Scripts\python.exe scripts\seed_risk_demo.py
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from wtnapp.database.database import SessionLocal  # noqa: E402
from wtnapp.helpers.tenant_scope import OrgContext, Principal  # noqa: E402
from wtnapp.models.asset_item_model import AssetItem  # noqa: E402
from wtnapp.models.gap_catalog_model import GapCatalogItem  # noqa: E402
from wtnapp.models.membership_model import Membership  # noqa: E402
from wtnapp.models.organization_model import Organization  # noqa: E402
from wtnapp.models.risk_catalog_model import OrgThreat, OrgVulnerability  # noqa: E402
from wtnapp.models.risk_model import Risk  # noqa: E402
from wtnapp.models.user_model import User  # noqa: E402
from wtnapp.services import crypto_service, risk_catalog_service, risk_service, risk_treatment_service  # noqa: E402
from wtnapp.services.gap_seed_service import adopt_seed as gap_adopt_seed, load_seed as gap_load_seed  # noqa: E402
from wtnapp.settings import (  # noqa: E402
    AssetScopeStatus,
    AssetType,
    CiaLevel,
    GapDimension,
    MembershipStatus,
    OrgStatus,
    RiskTreatmentOption,
    Role,
    UserStatus,
)

EMAIL = "riscodemo@example.com"
PASSWORD = "Sup3rSecret!2345"
SLUG = "risco-demo"

# (nome, tipo, C, I, A) — ativos demo
ASSETS = [
    ("Base de clientes", AssetType.database, CiaLevel.alta, CiaLevel.media, CiaLevel.media),
    ("Portal de atendimento", AssetType.system, CiaLevel.media, CiaLevel.alta, CiaLevel.critica),
]

# (título, descrição, probabilidade, índice do ativo) — riscos demo
RISKS = [
    ("Vazamento da base de clientes", "Acesso não autorizado expõe dados da base de clientes.", 4, 0),
    ("Indisponibilidade do portal", "Falha técnica torna o portal de atendimento indisponível.", 3, 1),
    ("Alteração indevida de cadastros", "Mudança não autorizada compromete a integridade dos dados.", 2, 0),
]


def _ctx(org_id, user) -> OrgContext:
    principal = Principal(user=user, jti="seed", exp_ts=0, tenant_ids=[org_id], is_super_admin=False)
    return OrgContext(principal=principal, tenant_id=org_id, role=Role.org_admin, is_super_admin=False, membership=None)


def main() -> int:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=SLUG).first()
        if org is None:
            org = Organization(name="Risco Demo", slug=SLUG, status=OrgStatus.active)
            db.add(org)
            db.commit()
            db.refresh(org)

        user = db.query(User).filter_by(email=EMAIL).first()
        if user is None:
            user = User(
                email=EMAIL,
                full_name="Risco Demo Admin",
                password_hash=crypto_service.hash_password(PASSWORD),
                status=UserStatus.active,
                password_changed_at=datetime.now(timezone.utc),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        if db.query(Membership).filter_by(tenant_id=org.id, user_id=user.id).first() is None:
            db.add(Membership(tenant_id=org.id, user_id=user.id, role=Role.org_admin, status=MembershipStatus.active))
            db.commit()

        ctx = _ctx(org.id, user)

        # Gap adotado (controles do Anexo A) + catálogos de risco adotados (idempotentes).
        gap_load_seed(db)
        db.commit()
        gap_adopt_seed(db, org.id, "2022.1")
        risk_catalog_service.adopt_threats(db, org.id)
        risk_catalog_service.adopt_vulnerabilities(db, org.id)

        # Ativos com CIA (idempotente por nome).
        asset_ids: list = []
        for idx, (name, atype, c, i, a) in enumerate(ASSETS, start=1):
            asset = db.query(AssetItem).filter_by(tenant_id=org.id, name=name).first()
            if asset is None:
                asset = AssetItem(
                    tenant_id=org.id, code=f"ATV-{idx:04d}", item_type=atype, name=name,
                    scope_status=AssetScopeStatus.in_scope, confidentiality=c, integrity=i, availability=a,
                    created_by=user.id,
                )
                db.add(asset)
                db.commit()
                db.refresh(asset)
            asset_ids.append(asset.id)

        threat = db.query(OrgThreat).filter_by(tenant_id=org.id).order_by(OrgThreat.code).first()
        vuln = db.query(OrgVulnerability).filter_by(tenant_id=org.id).order_by(OrgVulnerability.code).first()

        # Riscos avaliados (idempotente por título).
        created = 0
        first_risk = None
        for title, desc, prob, asset_idx in RISKS:
            existing = db.query(Risk).filter_by(tenant_id=org.id, title=title).first()
            if existing is not None:
                first_risk = first_risk or existing
                continue
            risk = risk_service.create_risk(db, ctx, {
                "title": title, "description": desc, "threat_id": threat.id,
                "vulnerability_id": vuln.id, "asset_item_ids": [asset_ids[asset_idx]],
            })
            risk_service.evaluate_risk(db, ctx, risk.id, {
                "probability_level": prob, "owner_user_id": user.id,
            })
            first_risk = first_risk or risk
            created += 1

        # Um risco em tratamento (mitigar) com controle do catálogo de Gap da org.
        if first_risk is not None and first_risk.treatment_option is None:
            gap = (
                db.query(GapCatalogItem)
                .filter_by(tenant_id=org.id, dimension=GapDimension.annex_a)
                .order_by(GapCatalogItem.order)
                .first()
            )
            if gap is not None:
                risk_treatment_service.set_treatment(db, ctx, first_risk.id, {
                    "treatment_option": RiskTreatmentOption.mitigate,
                    "residual_probability_level": 2, "residual_impact_level": 2,
                    "reason": "Aplicar controle do Anexo A para reduzir a exposição.",
                })
                risk_treatment_service.add_control(db, ctx, first_risk.id, {
                    "gap_catalog_item_id": gap.id, "responsible_user_id": user.id, "due_date": date(2026, 12, 31),
                })

        total = db.query(Risk).filter_by(tenant_id=org.id).count()
        print(f"OK: org={org.slug} ({org.id})  admin={EMAIL}  senha={PASSWORD}")
        print(f"    riscos: {total} ({created} criados nesta execução); 1 em tratamento com controle do Anexo A")
        print(f"    ameaça base={threat.code if threat else '-'}  vuln base={vuln.code if vuln else '-'}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
