"""Infra de testes: SQLite em arquivo temporário, override central de `get_db`, jti em memória.

`conftest.py` define variáveis de ambiente ANTES de importar `wtnapp` (settings lê no import):
- DATABASE_URL → SQLite em arquivo temp (conexões separadas p/ a sessão própria do audit)
- REDIS_URL=memory:// → denylist de jti determinística (sem Redis real)
- RATE_LIMIT_ENABLED=false → não dispara 429 nos testes funcionais
"""

import os
import tempfile
import uuid

_TMP_DB = os.path.join(tempfile.gettempdir(), f"wtn_test_{uuid.uuid4().hex}.db")
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TMP_DB}"
os.environ["REDIS_URL"] = "memory://"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-only-for-tests"
os.environ["BOOTSTRAP_TOKEN"] = "test-bootstrap-token"
os.environ["MAX_LOGIN_ATTEMPTS"] = "5"
os.environ["LOCKOUT_DURATION_MINUTES"] = "15"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from wtnapp.database import database  # noqa: E402
from wtnapp.main import app  # noqa: E402
from wtnapp.models import Base  # noqa: E402
from wtnapp.models.membership_model import Membership  # noqa: E402
from wtnapp.models.organization_model import Organization  # noqa: E402
from wtnapp.models.user_model import User  # noqa: E402
from wtnapp.services import crypto_service, token_service  # noqa: E402
from wtnapp.settings import MembershipStatus, OrgStatus, Role, UserStatus  # noqa: E402

DEFAULT_PASSWORD = "Sup3rSecret!2345"


@pytest.fixture(autouse=True)
def _reset_state():
    """Schema limpo + denylist limpa por teste."""
    Base.metadata.drop_all(bind=database.engine)
    Base.metadata.create_all(bind=database.engine)
    token_service.reset_memory_denylist()
    yield
    Base.metadata.drop_all(bind=database.engine)


@pytest.fixture
def db():
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    return TestClient(app)


class Factory:
    """Helpers de seed para os testes (baseline mínimo de cada user story)."""

    def __init__(self, session):
        self.db = session

    def org(self, slug="acme", name=None, status=OrgStatus.active) -> Organization:
        org = Organization(name=name or slug.upper(), slug=slug, status=status)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def user(
        self,
        email="user@acme.com",
        password=DEFAULT_PASSWORD,
        full_name="User",
        status=UserStatus.active,
        super_admin=False,
    ) -> User:
        user = User(
            email=email.lower(),
            full_name=full_name,
            password_hash=crypto_service.hash_password(password) if password else None,
            status=status,
            is_platform_super_admin=super_admin,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def membership(self, user, org, role=Role.org_admin, status=MembershipStatus.active) -> Membership:
        m = Membership(tenant_id=org.id, user_id=user.id, role=role, status=status)
        self.db.add(m)
        self.db.commit()
        self.db.refresh(m)
        return m


@pytest.fixture
def factory(db):
    return Factory(db)


@pytest.fixture
def outbox(monkeypatch):
    """Captura tokens que seriam enviados por e-mail (convite/reset) sem SMTP real."""
    from wtnapp.services import notification_service

    captured: list[dict] = []

    def _invite(*, to_email, token, org_name, role, existing_user=False):
        captured.append(
            {"type": "invite", "to": to_email, "token": token, "existing_user": existing_user}
        )
        return True

    def _reset(*, to_email, token):
        captured.append({"type": "reset", "to": to_email, "token": token})
        return True

    monkeypatch.setattr(notification_service, "send_invite_email", _invite)
    monkeypatch.setattr(notification_service, "send_password_reset_email", _reset)
    return captured


@pytest.fixture
def login(client):
    """Retorna headers Authorization a partir de credenciais válidas."""

    def _login(email, password=DEFAULT_PASSWORD):
        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.text
        return {"Authorization": f"Bearer {resp.json()['access_token']}"}

    return _login


@pytest.fixture
def context_seed(factory):
    """Organizacao + usuarios centrais do modulo de contexto."""
    org = factory.org("ctx-acme", "CTX Acme")
    admin = factory.user("admin@ctx-acme.com", full_name="Admin")
    consultant = factory.user("consultant@ctx-acme.com", full_name="Consultant")
    client = factory.user("client@ctx-acme.com", full_name="Client")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(consultant, org, Role.consultant)
    factory.membership(client, org, Role.client)
    return {"org": org, "admin": admin, "consultant": consultant, "client": client}


@pytest.fixture
def org_headers(login):
    def _headers(email, org_id):
        headers = login(email)
        headers["X-Org-Context"] = str(org_id)
        return headers

    return _headers


@pytest.fixture
def form_seed(factory):
    """Organizacao + usuarios para o motor de workflow de preenchimento (Feature 003)."""
    org = factory.org("form-acme", "Form Acme")
    admin = factory.user("admin@form-acme.com", full_name="Admin Form")
    consultant = factory.user("consultant@form-acme.com", full_name="Consultant Form")
    client_user = factory.user("client@form-acme.com", full_name="Client Form")
    factory.membership(admin, org, Role.org_admin)
    factory.membership(consultant, org, Role.consultant)
    factory.membership(client_user, org, Role.client)
    return {"org": org, "admin": admin, "consultant": consultant, "client": client_user}


@pytest.fixture
def gap_seed(db):
    """Carrega o seed 2022.1 no banco de testes e retorna a versão."""
    from wtnapp.services.gap_seed_service import load_seed

    version = load_seed(db)
    db.commit()
    return version


@pytest.fixture
def gap_seed_factory(db, factory):
    """Org + admin/consultant/client com permissões de gap analysis."""

    def _make(slug="gap-acme"):
        org = factory.org(slug, f"GAP {slug.upper()}")
        admin = factory.user(f"admin@{slug}.com", full_name=f"Admin {slug}")
        consultant = factory.user(f"consultant@{slug}.com", full_name=f"Consultant {slug}")
        client_user = factory.user(f"client@{slug}.com", full_name=f"Client {slug}")
        factory.membership(admin, org, Role.org_admin)
        factory.membership(consultant, org, Role.consultant)
        factory.membership(client_user, org, Role.client)
        return {"org": org, "admin": admin, "consultant": consultant, "client": client_user}

    return _make


@pytest.fixture
def soa_seed(db, factory, gap_seed):
    """Org + usuários + Gap Analysis adotado e avaliado (controles do Anexo A) — base da SoA."""
    from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
    from wtnapp.models.gap_catalog_model import GapCatalogItem
    from wtnapp.services.gap_seed_service import adopt_seed
    from wtnapp.settings import GapDimension, GapStatus

    def _make(slug="soa-acme"):
        org = factory.org(slug, f"SOA {slug.upper()}")
        admin = factory.user(f"admin@{slug}.com", full_name=f"Admin {slug}")
        consultant = factory.user(f"consultant@{slug}.com", full_name=f"Consultant {slug}")
        client_user = factory.user(f"client@{slug}.com", full_name=f"Client {slug}")
        factory.membership(admin, org, Role.org_admin)
        factory.membership(consultant, org, Role.consultant)
        factory.membership(client_user, org, Role.client)

        adopt_seed(db, org.id, "2022.1")
        assessment = db.query(GapAssessment).filter_by(tenant_id=org.id).first()
        annex_items = (
            db.query(GapAssessmentItem)
            .join(GapCatalogItem, GapAssessmentItem.catalog_item_id == GapCatalogItem.id)
            .filter(
                GapAssessmentItem.assessment_id == assessment.id,
                GapCatalogItem.dimension == GapDimension.annex_a,
            )
            .order_by(GapCatalogItem.order)
            .all()
        )
        if len(annex_items) >= 3:
            annex_items[0].status = GapStatus.meets
            annex_items[1].status = GapStatus.partial
            annex_items[2].status = GapStatus.not_applicable
            annex_items[2].exclusion_justification = "Não há desenvolvimento de software interno."
        db.commit()
        return {
            "org": org, "admin": admin, "consultant": consultant, "client": client_user,
            "assessment": assessment, "annex_items": annex_items,
        }

    return _make


@pytest.fixture
def complete_soa(db):
    """Preenche todos os controles da SoA (razão de inclusão / justificativa) p/ habilitar aprovação."""
    from wtnapp.models.soa_model import SoaItem

    def _complete(tenant_id):
        db.rollback()
        for it in db.query(SoaItem).filter_by(tenant_id=tenant_id).all():
            if it.applicable and not it.inclusion_reasons:
                it.inclusion_reasons = ["best_practice"]
            if not it.applicable and not (it.exclusion_justification or "").strip():
                it.exclusion_justification = "Não aplicável ao escopo."
        db.commit()

    return _complete


@pytest.fixture
def risk_seed(db, factory):
    """Org + usuários + catálogo de riscos adotado + 1 ativo com CIA (base do módulo de Riscos)."""
    from wtnapp.models.asset_item_model import AssetItem
    from wtnapp.services import risk_catalog_service
    from wtnapp.settings import AssetScopeStatus, AssetType, CiaLevel

    def _make(slug="risk-acme"):
        org = factory.org(slug, f"RISK {slug.upper()}")
        admin = factory.user(f"admin@{slug}.com", full_name=f"Admin {slug}")
        consultant = factory.user(f"consultant@{slug}.com", full_name=f"Consultant {slug}")
        client_user = factory.user(f"client@{slug}.com", full_name=f"Client {slug}")
        factory.membership(admin, org, Role.org_admin)
        factory.membership(consultant, org, Role.consultant)
        factory.membership(client_user, org, Role.client)

        risk_catalog_service.adopt_threats(db, org.id)
        risk_catalog_service.adopt_vulnerabilities(db, org.id)

        asset = AssetItem(
            tenant_id=org.id, code="ATV-0001", item_type=AssetType.information_asset,
            name="Base de clientes", scope_status=AssetScopeStatus.in_scope,
            confidentiality=CiaLevel.alta, integrity=CiaLevel.media, availability=CiaLevel.media,
            created_by=admin.id,
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return {
            "org": org, "admin": admin, "consultant": consultant, "client": client_user,
            "asset": asset,
        }

    return _make


@pytest.fixture
def link_risk_to_control(db):
    """Feature 013: cria Risk + RiskTreatmentControl ligando um risco a um controle do catálogo.

    Produz a entrada correspondente no soa-feed (insumo read-only consumido pela SoA).
    """
    from wtnapp.models.risk_catalog_model import OrgThreat, OrgVulnerability
    from wtnapp.models.risk_model import Risk, RiskTreatmentControl
    from wtnapp.services import risk_catalog_service
    from wtnapp.settings import RiskStatus

    def _link(org, gap_catalog_item_id, code="RSK-0001"):
        if not db.query(OrgThreat).filter_by(tenant_id=org.id).first():
            risk_catalog_service.adopt_threats(db, org.id)
        if not db.query(OrgVulnerability).filter_by(tenant_id=org.id).first():
            risk_catalog_service.adopt_vulnerabilities(db, org.id)
        threat = db.query(OrgThreat).filter_by(tenant_id=org.id).first()
        vuln = db.query(OrgVulnerability).filter_by(tenant_id=org.id).first()
        risk = Risk(
            tenant_id=org.id, code=code, title=f"Risco {code}", description="cenário de teste",
            threat_id=threat.id, vulnerability_id=vuln.id, status=RiskStatus.identified,
        )
        db.add(risk)
        db.flush()
        db.add(RiskTreatmentControl(
            tenant_id=org.id, risk_id=risk.id, gap_catalog_item_id=gap_catalog_item_id,
        ))
        db.commit()
        return risk

    return _link


@pytest.fixture
def approve_risk_plan(db):
    """Feature 013: marca o Plano de Tratamento de Riscos como aprovado vigente (gate normativo)."""
    from wtnapp.models.risk_model import RiskPlan

    def _approve(org):
        plan = db.query(RiskPlan).filter_by(tenant_id=org.id).first()
        if plan is None:
            plan = RiskPlan(tenant_id=org.id)
            db.add(plan)
            db.flush()
        plan.current_version_id = uuid.uuid4()
        db.commit()
        return plan

    return _approve


@pytest.fixture
def form_outbox(monkeypatch):
    """Captura emails do motor de formularios sem SMTP real."""
    from wtnapp.services import notification_service

    captured: list[dict] = []

    def _assignment(*, to_email, assignment_title, token=None, app_link=None, **kw):
        captured.append({"type": "assignment", "to": to_email, "token": token, "link": app_link})
        return True

    def _reminder(*, to_email, assignment_title, **kw):
        captured.append({"type": "reminder", "to": to_email})
        return True

    def _otp(*, to_email, otp_code, **kw):
        captured.append({"type": "otp", "to": to_email, "otp": otp_code})
        return True

    monkeypatch.setattr(notification_service, "send_form_assignment_email", _assignment)
    monkeypatch.setattr(notification_service, "send_form_reminder_email", _reminder)
    monkeypatch.setattr(notification_service, "send_signature_otp_email", _otp)
    return captured
