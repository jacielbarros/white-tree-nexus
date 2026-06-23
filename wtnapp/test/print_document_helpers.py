from __future__ import annotations

from datetime import datetime, timezone

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.context_analysis_model import ContextAnalysis
from wtnapp.models.diagnostic_model import Diagnostic
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.gap_catalog_model import GapCatalogItem
from wtnapp.models.scope_model import ScopeItem, ScopeStatement
from wtnapp.models.soa_model import Soa, SoaItem
from wtnapp.models.stakeholder_model import Stakeholder, StakeholderMap, StakeholderRequirement
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import EngagementStrategy, GapDimension, GapStatus, IssueFramework, IssueOrigin, Level, RequirementType, Role, ScopeItemKind


def configure_document_storage(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_DIR", str(tmp_path / "document_store"))
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))
    monkeypatch.setattr(settings, "DOCUMENT_RENDER_TIMEOUT_SECONDS", 30)
    monkeypatch.setattr(settings, "DOCUMENT_PREVIEW_TTL_MINUTES", 60)


def headers_for(org_headers, user, org):
    return org_headers(user.email, org.id)


def seed_context(db, factory, slug="print-context"):
    org = factory.org(slug, f"Print {slug}")
    admin = factory.user(f"admin@{slug}.com", full_name=f"Admin {slug}")
    client = factory.user(f"client@{slug}.com", full_name=f"Client {slug}")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(client, org, Role.client)
    diagnostic = Diagnostic(
        tenant_id=org.id,
        sections={"identificacao": {"nome": org.name}, "ambiente": {"setor": "Tecnologia"}},
    )
    analysis = ContextAnalysis(
        tenant_id=org.id,
        intended_outcomes="Proteger informacoes criticas e apoiar certificacao ISO 27001.",
        methodology="PESTEL e SWOT.",
    )
    db.add_all([diagnostic, analysis])
    db.flush()
    stakeholder_map = StakeholderMap(tenant_id=org.id)
    scope = ScopeStatement(tenant_id=org.id, interfaces_dependencies="Servicos em nuvem e fornecedores criticos.")
    db.add_all([stakeholder_map, scope])
    db.flush()
    stakeholder = Stakeholder(
        tenant_id=org.id,
        map_id=stakeholder_map.id,
        name="Alta direcao",
        type="internal",
        power=Level.alto,
        interest=Level.alto,
        strategy=EngagementStrategy.manage_closely,
    )
    db.add(stakeholder)
    db.flush()
    db.add(
        StakeholderRequirement(
            tenant_id=org.id,
            stakeholder_id=stakeholder.id,
            type=RequirementType.expectation,
            description="Relatorios confiaveis de conformidade.",
            how_addressed="Revisao periodica do SGSI.",
        )
    )
    db.add(
        ScopeItem(
            tenant_id=org.id,
            scope_id=scope.id,
            kind=ScopeItemKind.inclusion,
            description="Processos corporativos e infraestrutura de TI.",
            justification="Ambiente que processa informacoes criticas.",
        )
    )
    from wtnapp.models.context_analysis_model import ContextIssue

    db.add(
        ContextIssue(
            tenant_id=org.id,
            analysis_id=analysis.id,
            origin=IssueOrigin.external,
            framework=IssueFramework.pestel,
            category="Legal",
            description="Requisitos LGPD e contratos com clientes.",
            impact=Level.alto,
        )
    )
    db.commit()
    return {"org": org, "admin": admin, "client": client, "analysis": analysis}


def seed_gap(db, factory, gap_seed, slug="print-gap"):
    org = factory.org(slug, f"Print {slug}")
    admin = factory.user(f"admin@{slug}.com", full_name=f"Admin {slug}")
    client = factory.user(f"client@{slug}.com", full_name=f"Client {slug}")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(client, org, Role.client)
    adopt_seed(db, org.id, "2022.1")
    assessment = db.query(GapAssessment).filter_by(tenant_id=org.id).first()
    items = (
        db.query(GapAssessmentItem)
        .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
        .filter(GapAssessmentItem.assessment_id == assessment.id, GapCatalogItem.dimension == GapDimension.annex_a)
        .order_by(GapCatalogItem.order)
        .limit(3)
        .all()
    )
    if items:
        items[0].status = GapStatus.meets
        items[1].status = GapStatus.partial
        items[2].status = GapStatus.not_meet
    db.commit()
    return {"org": org, "admin": admin, "client": client, "assessment": assessment, "items": items}


def seed_soa(db, factory, gap_seed, slug="print-soa"):
    gap = seed_gap(db, factory, gap_seed, slug)
    soa = Soa(tenant_id=gap["org"].id, gap_assessment_id=gap["assessment"].id)
    db.add(soa)
    db.flush()
    for item in gap["items"]:
        cat = db.get(GapCatalogItem, item.catalog_item_id)
        db.add(
            SoaItem(
                tenant_id=gap["org"].id,
                soa_id=soa.id,
                catalog_item_id=cat.id,
                gap_assessment_item_id=item.id,
                ref_code=cat.ref_code,
                theme=cat.theme,
                name=cat.name,
                applicable=True,
                inclusion_reasons=["best_practice"],
                implementation_status=None,
                expected_evidence="Politica, registro ou evidencia documental aplicavel.",
            )
        )
    db.commit()
    return {**gap, "soa": soa}
