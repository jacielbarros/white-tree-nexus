#!/usr/bin/env python
r"""Seed idempotente de um cenário E2E para a SoA (Feature 005).

Cria (se ainda não existir) uma organização demo com um Admin e o Gap Analysis adotado e
avaliado (alguns controles do Anexo A), de modo que a tela de SoA tenha insumo para consolidar.

Uso (raiz do projeto):
    .\.venv\Scripts\python.exe scripts\seed_soa_demo.py
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from wtnapp.database.database import SessionLocal  # noqa: E402
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem  # noqa: E402
from wtnapp.models.gap_catalog_model import GapCatalogItem  # noqa: E402
from wtnapp.models.membership_model import Membership  # noqa: E402
from wtnapp.models.organization_model import Organization  # noqa: E402
from wtnapp.models.user_model import User  # noqa: E402
from wtnapp.services import crypto_service  # noqa: E402
from wtnapp.services.gap_seed_service import adopt_seed  # noqa: E402
from wtnapp.settings import GapDimension, GapStatus, MembershipStatus, OrgStatus, Role, UserStatus  # noqa: E402

EMAIL = "soademo@example.com"
PASSWORD = "Sup3rSecret!2345"
SLUG = "soa-demo"


def main() -> int:
    db = SessionLocal()
    try:
        org = db.query(Organization).filter_by(slug=SLUG).first()
        if org is None:
            org = Organization(name="SoA Demo", slug=SLUG, status=OrgStatus.active)
            db.add(org)
            db.commit()
            db.refresh(org)

        user = db.query(User).filter_by(email=EMAIL).first()
        if user is None:
            user = User(
                email=EMAIL,
                full_name="SoA Demo Admin",
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

        # Gap Analysis adotado + avaliado
        adopt_seed(db, org.id, "2022.1")
        assessment = db.query(GapAssessment).filter_by(tenant_id=org.id).first()
        annex = (
            db.query(GapAssessmentItem)
            .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
            .filter(
                GapAssessmentItem.assessment_id == assessment.id,
                GapCatalogItem.dimension == GapDimension.annex_a,
            )
            .order_by(GapCatalogItem.order)
            .all()
        )
        if len(annex) >= 4:
            annex[0].status = GapStatus.meets
            annex[1].status = GapStatus.partial
            annex[2].status = GapStatus.not_meet
            annex[3].status = GapStatus.not_applicable
            annex[3].exclusion_justification = "Não há desenvolvimento de software interno."
        db.commit()

        print(f"OK: org={org.slug} ({org.id})  admin={EMAIL}  senha={PASSWORD}")
        print(f"    Anexo A avaliados: {sum(1 for a in annex if a.status != GapStatus.not_filled)} / {len(annex)}")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
