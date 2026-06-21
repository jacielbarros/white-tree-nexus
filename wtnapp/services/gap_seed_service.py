"""Gap Seed Service — carrega e adota versões do seed ISO/IEC 27001.

Adoção é **aditiva e idempotente**:
- Novos itens entram como not_filled.
- Personalizações e avaliações existentes são preservadas.
- Itens removidos do seed são marcados como is_discontinued (nunca deletados).
"""

import uuid
from sqlalchemy.orm import Session

from wtnapp.data.iso27001_seed import SEED_DESCRIPTION, SEED_VERSION, build_seed_items
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.gap_seed_model import GapSeedItem, GapSeedVersion
from wtnapp.settings import GapStatus


def load_seed(db: Session) -> GapSeedVersion:
    """Carrega o seed 2022.1 no banco (idempotente — não duplica se já existe)."""
    version = db.query(GapSeedVersion).filter_by(version=SEED_VERSION).first()
    if version is None:
        version = GapSeedVersion(version=SEED_VERSION, description=SEED_DESCRIPTION)
        db.add(version)
        db.flush()

    existing_refs = {
        r for (r,) in db.query(GapSeedItem.ref_code).filter_by(seed_version_id=version.id).all()
    }
    for item_dict in build_seed_items():
        if item_dict["ref_code"] not in existing_refs:
            db.add(GapSeedItem(seed_version_id=version.id, **item_dict))

    db.flush()
    return version


def adopt_seed(db: Session, tenant_id: uuid.UUID, seed_version: str) -> dict:
    """Materializa/atualiza a cópia editável do catálogo da organização a partir do seed.

    Retorna contagem de { added, discontinued, unchanged }.
    """
    version = db.query(GapSeedVersion).filter_by(version=seed_version).first()
    if version is None:
        from fastapi import HTTPException, status
        raise HTTPException(status.HTTP_409_CONFLICT, f"Versão de seed '{seed_version}' não disponível.")

    seed_items = db.query(GapSeedItem).filter_by(seed_version_id=version.id).all()
    seed_by_ref = {s.ref_code: s for s in seed_items}

    catalog_items = db.query(GapCatalogItem).filter_by(tenant_id=tenant_id).all()
    catalog_by_ref = {c.ref_code: c for c in catalog_items}

    added = 0
    discontinued = 0
    unchanged = 0

    for ref, seed_item in seed_by_ref.items():
        if ref in catalog_by_ref:
            existing = catalog_by_ref[ref]
            if existing.is_discontinued:
                existing.is_discontinued = False
            unchanged += 1
        else:
            db.add(GapCatalogItem(
                tenant_id=tenant_id,
                seed_item_id=seed_item.id,
                dimension=seed_item.dimension,
                ref_code=seed_item.ref_code,
                name=seed_item.name,
                theme=seed_item.theme,
                objective=seed_item.objective,
                order=seed_item.order,
                is_custom=False,
                is_discontinued=False,
            ))
            added += 1

    # Itens no catálogo da org que não existem mais no seed → is_discontinued
    for ref, cat_item in catalog_by_ref.items():
        if not cat_item.is_custom and ref not in seed_by_ref:
            if not cat_item.is_discontinued:
                cat_item.is_discontinued = True
                discontinued += 1

    db.flush()

    # Garante que a avaliação existe e tem o seed_version_id atualizado
    assessment = db.query(GapAssessment).filter_by(tenant_id=tenant_id).first()
    if assessment is None:
        assessment = GapAssessment(tenant_id=tenant_id, seed_version_id=version.id)
        db.add(assessment)
        db.flush()
    else:
        assessment.seed_version_id = version.id

    # Cria GapAssessmentItems para novos itens do catálogo que ainda não têm avaliação
    existing_item_refs = {
        ci.ref_code
        for ci in (
            db.query(GapCatalogItem)
            .join(GapAssessmentItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
            .filter(GapCatalogItem.tenant_id == tenant_id)
            .all()
        )
    }
    new_catalog_items = (
        db.query(GapCatalogItem)
        .filter(
            GapCatalogItem.tenant_id == tenant_id,
            GapCatalogItem.is_discontinued == False,
        )
        .all()
    )
    for cat_item in new_catalog_items:
        if cat_item.ref_code not in existing_item_refs:
            db.add(GapAssessmentItem(
                tenant_id=tenant_id,
                assessment_id=assessment.id,
                catalog_item_id=cat_item.id,
                status=GapStatus.not_filled,
            ))

    db.commit()
    return {"added": added, "discontinued": discontinued, "unchanged": unchanged, "assessment_id": str(assessment.id)}
