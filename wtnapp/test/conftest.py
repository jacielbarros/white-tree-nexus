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
