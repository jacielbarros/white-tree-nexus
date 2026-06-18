# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Codinome provisório:** "White Tree Nexus". Faça find-replace pelo nome real do produto.
> Prefixo de diretórios: `wtn` (`wtnapp/` backend, `wtnadmin/` admin web).

## Project Overview

A **White Tree Nexus** é uma plataforma **SaaS multi-tenant** de Gestão de SGSI e Compliance
**ISO/IEC 27001:2022**, organizada como um **monorepo**:

| Directory | Module | Stack |
|-----------|--------|-------|
| `wtnapp/` | Backend API | Python, FastAPI, SQLAlchemy, PostgreSQL |
| `wtnadmin/` | Admin/Web (frontend) | Angular 21, PrimeNG 21, Signals, TypeScript 5.9 |

O produto acompanha a jornada de implementação do SGSI de múltiplas organizações (tenants),
com isolamento estrito de dados entre elas. Ver os princípios inegociáveis em
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) — **leia antes de
qualquer spec, plano ou implementação.**

## Common Commands

### Backend
```bash
# Activate virtual environment (Windows)
source <venv>/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn wtnapp.main:app --reload

# Run all tests
pytest wtnapp/test/

# Run a single test file
pytest wtnapp/test/test_auth.py

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Admin Frontend
```bash
cd wtnadmin
npm install
npm start                       # dev server on http://localhost:4200
npm run build                   # production build
npm test                        # Vitest unit tests
```

### Required `.env` variables (ponto de partida — ajuste por feature)
```
DATABASE_URL=postgresql://postgres:password@localhost/wtndatabase
JWT_SECRET_KEY=<64-byte hex>
TOKEN_EXPIRY_MINUTES=20
RESET_TOKEN_EXPIRY_MINUTES=30
REDIS_URL=redis://localhost:6379/0
TRUSTED_PROXY_COUNT=0
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_PASSWORD_REQUEST=3/minute
MAX_LOGIN_ATTEMPTS=5
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
CSP_ENABLED=true
HSTS_ENABLED=false        # opt-in — só ligar em produção HTTPS
HSTS_MAX_AGE=31536000
# --- Proteção de dados sensíveis em repouso ---
FIELD_ENCRYPTION_KEY=     # Fernet (urlsafe-b64 32B) p/ cifrar campos sensíveis (risco/PII/evidência)
# --- Storage de evidências (escolher na feature de Evidências) ---
EVIDENCE_STORAGE_DIR=./evidence_store/   # local; trocar por S3/objeto em produção
EVIDENCE_MAX_FILE_BYTES=20971520          # 20 MB
# --- Recursos de IA (Módulo 10, opt-in por organização) ---
AI_FEATURES_ENABLED=false
ANTHROPIC_API_KEY=
AI_MODEL=claude-sonnet-4-6                # default; usar os modelos Claude mais recentes
```

---

## Backend Architecture (`wtnapp/`)

### Layers
1. **`main.py`** — FastAPI app com metadata, CORS, IntegrityError handler, health check com
   verificação de DB, registra todos os routers via `app.include_router(...)`. Todo novo router
   é registrado aqui.
2. **`database/database.py`** — engine SQLAlchemy, `SessionLocal` e **`get_db()` centralizado** —
   importado por todos os routers e helpers. NÃO criar `get_db()` local.
3. **`routers/`** — um arquivo por domínio; queries SQLAlchemy direto. A maior parte da lógica
   de negócio vive aqui.
4. **`models/`** — modelos ORM SQLAlchemy (`<domain>_model.py`). Base declarativa em `models/base.py`.
5. **`schemas/`** — modelos Pydantic de request/response (`<domain>_schema.py`). Padrão
   `<Domain>Base / Create / Update / Response`.
6. **`services/`** — lógica reutilizável/isolada: `audit_service.py`, `crypto_service.py`,
   `notification_service.py`.
7. **`helpers/`** — utilitários: `permissions.py` (RBAC), `tenant_scope.py` (escopo de tenant),
   `settings_helper.py`.
8. **`utils/`** — integrações com efeito colateral: e-mail (SMTP), storage de evidências, IA.
9. **`settings.py`** — lê `.env` via `load_dotenv()`; define enums e parâmetros configuráveis.

Não há **repository layer** e não há **middleware** além de CORS, rate limiting e (se justificado)
resolução de tenant.

### Multi-tenant — invariante central
- Todo modelo de domínio carrega `tenant_id` (FK para `organizations`).
- A resolução do tenant do usuário autenticado e o filtro por tenant vivem em
  `helpers/tenant_scope.py` (ponto único e não-contornável). Nunca filtre tenant ad-hoc no router.
- Acesso cross-tenant ⇒ `404`/`403` sem revelar existência + audit log.
- Toda feature tem **teste de isolamento de tenant** dedicado.

### RBAC (Perfis de Acesso)
Papéis: **Super Admin da plataforma** (único cross-tenant), **Admin da organização**,
**Consultor**, **Cliente**, **Gestor**, **Dono de processo**, **Dono de controle**,
**Auditor interno**, **Colaborador convidado**. Permissões granulares verificadas via
`require_permission()` de `helpers/permissions.py`. Super Admin tem bypass de permissão,
**mas não de auditoria** — suas ações são especialmente logadas.

### Audit Logs
- `AuditService.log_from_request()` registra metadata de toda operação relevante.
- Usa `SessionLocal` própria (persiste mesmo em rollback, falha em silêncio).
- Trilha **append-only**: nunca editar/apagar registros.
- **NUNCA** logar PII, senhas, tokens, chaves ou conteúdo confidencial de evidência.

### Authentication
- JWT (HS512) assinado com `JWT_SECRET_KEY`, emitido por `routers/auth.py`. Rate limited.
- Claims: `sub`, `tenant_id` (ou lista, p/ consultor multi-org), `role`, `iss`, `exp`, `jti`.
- Login lockout após `MAX_LOGIN_ATTEMPTS`. Logout revoga `jti` no Redis (fail-open).

### Módulos do produto (preencher conforme as features chegam)
Ordem de MVP: 1) Diagnóstico e Contexto · 2) Gap Analysis · 3) SoA · 4) Plano de Ação ·
5) Gestão de Evidências. Evolução: 6) Riscos · 7) Auditoria Interna · 8) Revisão pela Direção ·
9) IA · 10) Dashboards avançados. Cada módulo nasce de uma spec própria
([Spec Kit](.specify/)) e ganha sua seção aqui quando implementado.

### Schema management
Alembic migrations (`wtnapp/alembic/`) **e** `create_all()` no startup. Ao mudar tabelas,
atualizar o modelo SQLAlchemy **e** adicionar migration; não remover `create_all()`.

## Backend Key Conventions

**Router pattern:**
```python
from wtnapp.database.database import get_db

router = APIRouter(prefix="/my-domain", tags=["my-domain"])
db_dependency = Annotated[Session, Depends(get_db)]
```

**RBAC pattern:**
```python
from wtnapp.helpers.permissions import require_permission
manage_dep = Annotated[dict, Depends(require_permission("manage_something"))]
```

**Tenant scope pattern:**
```python
from wtnapp.helpers.tenant_scope import scoped_query
# scoped_query(db, Model, user) já filtra por tenant_id do usuário
```

**Audit pattern:**
```python
AuditService.log_from_request(
    db=db, request=request, operation="CREATE",
    entity_type="risk", entity_id=str(obj.id),
    details={"key": "value"}, user_id=user.get("user_id"),
)
```

**DB write pattern:** `db.add(obj)` → `db.commit()` → `db.refresh(obj)` (só ao retornar o objeto).

**Pydantic v2:** `.model_dump()`; ORM schemas com `class Config: from_attributes = True`.

**Async:** handlers podem ser `async def` mas usam SQLAlchemy síncrono — intencional. Não
introduzir `AsyncSession`.

**Language:** comentários e strings de usuário misturam Português e Inglês. Preserve o idioma
do arquivo que está editando.

---

## Admin Frontend Architecture (`wtnadmin/`)

### Stack
- **Angular 21** com standalone components (sem NgModules)
- **PrimeNG 21** (`@primeuix/themes`, preset Material)
- **Signals** (`signal()`, `computed()`) para estado
- **Vitest** (nativo via `@angular/build:unit-test`)
- **esbuild** (via `@angular/build:application`)

### Key conventions
- `input()` / `output()` functions, NUNCA `@Input()` / `@Output()`
- `inject()`, NUNCA injeção via construtor
- Control flow nativo: `@if`, `@for`, `@switch`
- `ChangeDetectionStrategy.OnPush`
- NÃO declarar `standalone: true` (é o default)
- NÃO usar sufixo `Component` no nome da classe
- Reactive Forms com `NonNullableFormBuilder`

### Structure
```
wtnadmin/src/app/
  app.ts              # Root component
  app.config.ts       # Bootstrap providers (router, PrimeNG theme)
  app.routes.ts       # Route definitions
  core/               # Singleton services, app-wide utilities
  pages/              # Feature modules (lazy-loaded routes)
  shared/             # Reusable components, directives, pipes
```

### Path aliases (tsconfig.json)
- `@app/*` → `./src/app/*`
- `@environment/*` → `./src/environments/*`

---

## What to Avoid (Global)

- Não executar query de domínio sem escopo de tenant.
- Não inventar repository layer no backend.
- Não adicionar middleware sem requisito explícito.
- Não usar `pydantic-settings`; configuração em `settings.py` com `load_dotenv()`.
- Não introduzir `AsyncSession`.
- Não esquecer de registrar novos routers em `main.py`.
- Não usar NgModules nem `@Input()`/`@Output()` decorators no Angular.
- Não editar/apagar audit logs ou histórico de evidências (append-only).

## Testing

### Backend
- Framework: pytest + FastAPI `TestClient`
- SQLite in-memory com override único e centralizado de `get_db`
- `conftest.py` isola infra real (`REDIS_URL=""`, audit em sink SQLite)
- **Teste de isolamento de tenant é obrigatório** por feature
- Helpers async: `@pytest.mark.asyncio`

### Admin Frontend
- Framework: Vitest (nativo) + Angular TestBed
- `ng test --no-watch` (ou `npm test`)
- `describe`/`it`/`expect` (globals Vitest, sem Jasmine)
- DOM: `happy-dom`

---

## Fluxo de trabalho com Spec Kit

1. `/speckit.constitution` — ratifica/ajusta os princípios (já adaptados em `.specify/memory/`).
2. `/speckit.specify` — descreve **o QUÊ** de cada feature (agnóstico de stack).
3. `/speckit.plan` — decide **o COMO** (stack, modelo de dados, estratégia de tenant), guiado
   pela constitution.
4. `/speckit.tasks` → `/speckit.implement`.

A **primeira feature deve ser a fundação multi-tenant** (organizações + auth + RBAC +
isolamento + auditoria). Ver `specs/SPECIFY-PROMPT-fundacao.md`.
