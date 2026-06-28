"""Catálogo de ameaças e vulnerabilidades — semente + cópia editável por org (Feature 012).

Adoção aditiva e idempotente (padrão do Gap): itens novos entram, personalizações e itens próprios
são preservados; re-executar não duplica.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from wtnapp.data.iso27005_seed import THREAT_SEED, VULNERABILITY_SEED
from wtnapp.models.risk_catalog_model import (
    OrgThreat,
    OrgVulnerability,
    ThreatSeedItem,
    VulnerabilitySeedItem,
)


def load_seed(db: Session) -> None:
    """Carrega as sementes de ameaças/vulnerabilidades (idempotente por `code`)."""
    existing_threats = {t.code for t in db.query(ThreatSeedItem).all()}
    for order, item in enumerate(THREAT_SEED):
        if item["code"] not in existing_threats:
            db.add(ThreatSeedItem(order=order, **item))
    existing_vulns = {v.code for v in db.query(VulnerabilitySeedItem).all()}
    for order, item in enumerate(VULNERABILITY_SEED):
        if item["code"] not in existing_vulns:
            db.add(VulnerabilitySeedItem(order=order, **item))
    db.flush()


def adopt_threats(db: Session, tenant_id: uuid.UUID) -> dict:
    """Materializa/atualiza a cópia da org do catálogo de ameaças (aditivo/idempotente)."""
    load_seed(db)
    seed = db.query(ThreatSeedItem).order_by(ThreatSeedItem.order).all()
    existing = {t.code: t for t in db.query(OrgThreat).filter_by(tenant_id=tenant_id).all()}
    added = unchanged = 0
    for s in seed:
        if s.code in existing:
            unchanged += 1
            continue
        db.add(OrgThreat(
            tenant_id=tenant_id, seed_item_id=s.id, code=s.code, name=s.name,
            description=s.description, category=s.category, origin=s.origin, is_custom=False,
        ))
        added += 1
    db.commit()
    return {"added": added, "unchanged": unchanged, "reactivated": 0}


def adopt_vulnerabilities(db: Session, tenant_id: uuid.UUID) -> dict:
    """Materializa/atualiza a cópia da org do catálogo de vulnerabilidades."""
    load_seed(db)
    seed = db.query(VulnerabilitySeedItem).order_by(VulnerabilitySeedItem.order).all()
    existing = {v.code: v for v in db.query(OrgVulnerability).filter_by(tenant_id=tenant_id).all()}
    added = unchanged = 0
    for s in seed:
        if s.code in existing:
            unchanged += 1
            continue
        db.add(OrgVulnerability(
            tenant_id=tenant_id, seed_item_id=s.id, code=s.code, name=s.name,
            description=s.description, category=s.category, is_custom=False,
        ))
        added += 1
    db.commit()
    return {"added": added, "unchanged": unchanged, "reactivated": 0}


def _next_custom_code(db: Session, model, tenant_id: uuid.UUID, prefix: str) -> str:
    """Próximo código sequencial por org para itens custom (ex.: AME-C001)."""
    count = db.query(model).filter(
        model.tenant_id == tenant_id, model.is_custom == True  # noqa: E712
    ).count()
    return f"{prefix}-C{count + 1:03d}"


def create_threat(db: Session, tenant_id: uuid.UUID, actor_id, data: dict) -> OrgThreat:
    from wtnapp.settings import RISK_THREAT_CODE_PREFIX
    threat = OrgThreat(
        tenant_id=tenant_id,
        code=_next_custom_code(db, OrgThreat, tenant_id, RISK_THREAT_CODE_PREFIX),
        name=data["name"], description=data.get("description"), category=data["category"],
        origin=data.get("origin"), is_custom=True, created_by=actor_id,
    )
    db.add(threat)
    db.commit()
    db.refresh(threat)
    return threat


def create_vulnerability(db: Session, tenant_id: uuid.UUID, actor_id, data: dict) -> OrgVulnerability:
    from wtnapp.settings import RISK_VULN_CODE_PREFIX
    gap_id = data.get("gap_catalog_item_id")
    if gap_id is not None:
        _assert_same_tenant_gap(db, tenant_id, gap_id)
    vuln = OrgVulnerability(
        tenant_id=tenant_id,
        code=_next_custom_code(db, OrgVulnerability, tenant_id, RISK_VULN_CODE_PREFIX),
        name=data["name"], description=data.get("description"), category=data["category"],
        gap_catalog_item_id=gap_id, is_custom=True, created_by=actor_id,
    )
    db.add(vuln)
    db.commit()
    db.refresh(vuln)
    return vuln


def _assert_same_tenant_gap(db: Session, tenant_id: uuid.UUID, gap_id) -> None:
    from wtnapp.models.gap_catalog_model import GapCatalogItem
    gap = db.query(GapCatalogItem).filter_by(id=gap_id, tenant_id=tenant_id).first()
    if gap is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")


def archive_item(db: Session, item, reason: str) -> None:
    if not (reason or "").strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Justificativa obrigatória para arquivar.")
    item.is_archived = True
    item.archive_reason = reason
    db.commit()


def _assert_same_tenant_asset(db: Session, tenant_id: uuid.UUID, asset_item_id) -> None:
    from wtnapp.models.asset_item_model import AssetItem
    asset = db.query(AssetItem).filter_by(id=asset_item_id, tenant_id=tenant_id).first()
    if asset is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Recurso não encontrado.")


def link_threat_asset(db: Session, tenant_id: uuid.UUID, threat: OrgThreat, asset_item_id, actor_id):
    from wtnapp.models.risk_catalog_model import AssetThreatLink
    _assert_same_tenant_asset(db, tenant_id, asset_item_id)
    existing = db.query(AssetThreatLink).filter_by(
        tenant_id=tenant_id, asset_item_id=asset_item_id, threat_id=threat.id
    ).first()
    if existing:
        return existing
    link = AssetThreatLink(
        tenant_id=tenant_id, asset_item_id=asset_item_id, threat_id=threat.id, created_by=actor_id
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link


def link_vulnerability_asset(db: Session, tenant_id: uuid.UUID, vuln: OrgVulnerability, asset_item_id, actor_id):
    from wtnapp.models.risk_catalog_model import AssetVulnerabilityLink
    _assert_same_tenant_asset(db, tenant_id, asset_item_id)
    existing = db.query(AssetVulnerabilityLink).filter_by(
        tenant_id=tenant_id, asset_item_id=asset_item_id, vulnerability_id=vuln.id
    ).first()
    if existing:
        return existing
    link = AssetVulnerabilityLink(
        tenant_id=tenant_id, asset_item_id=asset_item_id, vulnerability_id=vuln.id, created_by=actor_id
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return link
