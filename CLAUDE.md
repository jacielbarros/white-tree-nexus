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
RATE_LIMIT_FORM_TOKEN=20/minute   # endpoints públicos do motor de workflow (token)
RATE_LIMIT_FORM_OTP=5/minute      # OTP de assinatura eletrônica (mais restrito)
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

#### Fundação Multi-Tenant (Feature 001 — implementada)
Base de todos os módulos. Spec/plano em `specs/001-fundacao-multi-tenant/`.
- **Backend** (`wtnapp/`): organizações (ciclo de vida), bootstrap do Super Admin, auth JWT HS512
  (login/bloqueio/logout), redefinição de senha, convites + aceite, RBAC, isolamento de tenant e
  auditoria append-only. Routers: `bootstrap`, `auth`, `organizations`, `invitations`,
  `memberships`, `me`. Escopo de tenant central em `helpers/tenant_scope.py` (+ RLS no PostgreSQL);
  RBAC em `helpers/permissions.py` (`require_permission` / `require_super_admin`); auditoria em
  `services/audit_service.py`. Contexto de organização via header `X-Org-Context`. O aceite de
  convite reaproveita usuário existente (ex.: Super Admin/Consultor multi-org): quem já tem conta
  **confirma o vínculo sem redefinir a senha**; `GET /invitations/lookup` (público) informa à tela
  se é usuário novo (pede senha) ou existente (só confirma). E-mail de convite leva link
  `/accept?token=` e texto adequado a cada caso.
- **Frontend** (`wtnadmin/`): core (AuthStore com Signals, interceptor, guards, `ApiService`) e
  telas login, senha (esqueci/redefinir), aceite de convite, shell c/ seletor de organização,
  organizações e usuários/convites.
- **Testes**: `pytest wtnapp/test` (inclui isolamento de tenant) e `npm test` em `wtnadmin/`.
- **Migrations**: `wtnapp/alembic/` (schema inicial + RLS/gatilho append-only). Ainda **não**
  validado contra PostgreSQL real (RLS é PG-only; testes rodam em SQLite).

#### Módulo 1 — Diagnóstico e Contexto (Feature 002 — implementada)
Cláusula 4 do SGSI. Spec/plano em `specs/002-diagnostico-contexto/`. Segue o padrão
[Documento Controlado SGSI](docs/iso27001-documento-controlado.md).
- **Backend** (`wtnapp/`): Diagnóstico inicial (`routers/diagnostic.py`), Análise de Contexto 4.1
  (PESTEL/SWOT + impacto — `routers/context_analysis.py`), Mapa de Partes Interessadas 4.2
  (Poder×Interesse/Mendelow — `routers/stakeholders.py`), Declaração de Escopo 4.3 com referências
  de versão a Contexto/Partes (`routers/scope.py`), visão consolidada + sugestões heurísticas
  (`routers/context_overview.py` + `services/suggestion_service.py`). Ciclo de vida do documento
  controlado (rascunho→revisão→aprovação, identificador/versão/classificação/retenção) em
  `services/controlled_document_service.py`. Versões imutáveis em `document_versions` (gatilho
  append-only); "1 em vigor + rascunho paralelo" — a versão vigente é o ponteiro
  `current_version_id` do artefato e a obsolescência de uma referência é **derivada por recência**
  (`is_superseded`), nunca por mutação de status (preserva o append-only). Aprovação exige
  `approve_context_document` (Admin da organização). Acesso por classificação configurável por org
  (`helpers/classification_access.py` + `models/classification_policy_model.py`, default RBAC).
  Um conjunto por organização (índice único em `tenant_id`).
- **Frontend** (`wtnadmin/`): telas `diagnostic/`, `context-analysis/`, `stakeholders/`, `scope/`,
  `context-overview/` (lazy, `permissionGuard('view_context')`), com histórico de versões e ações
  enviar-para-revisão/aprovar; links no shell.
- **Testes**: `pytest wtnapp/test` (diagnóstico, contexto, partes, escopo, versionamento/append-only,
  classificação, sugestões + isolamento de tenant) e `npm test` em `wtnadmin/`.
- **Migrations**: `wtnapp/alembic/versions/c3d4e5f6a702_context_module.py` (tabelas + RLS + gatilho
  append-only de `document_versions`); `alembic check` sem drift. **Pendente**: validação E2E
  manual no browser (T038) e contra PostgreSQL real.

#### Motor de Workflow de Preenchimento (Feature 003 — implementada)
Capacidade transversal. Spec/plano em `specs/003-workflow-preenchimento/`.
- **Backend** (`wtnapp/`): `FormTemplate` (CRUD de template por org, kind/status, schema JSON) em
  `routers/form_templates.py`; `FormAssignment` (ciclo de vida: pending→in_progress→submitted→signed
  →completed + return + cancel) em `routers/form_assignments.py`; respondente externo via token
  (apenas hash em `respondent_token_hash`) em `routers/form_respond.py`; assinatura eletrônica avançada
  (Lei 14.063/2020) com SHA-256 canônico, DocumentVersion imutável e OTP por e-mail (fail-closed)
  em `services/signature_service.py`; máquina de estados e snapshot do template em
  `services/form_workflow_service.py`; integração com Diagnóstico em `services/diagnostic_intake.py`;
  política de assinatura por org (única ou dupla) em `routers/form_signature_policy.py`.
  Notificações de atribuição/lembrete/OTP em `services/notification_service.py` (best-effort).
  Trilha append-only em `models/form_assignment_event_model.py` (SQLite+PG triggers).
  Permissões: `assign_form`, `fill_form`, `sign_form`, `view_form`.
- **Testes backend**: `pytest wtnapp/test/test_form_assignment_lifecycle.py` (ciclo de vida + devolução/cancelamento),
  `test_form_respond_token.py` (token externo + OTP), `test_form_signature.py` (assinatura + integridade),
  `test_tenant_isolation_forms.py` (isolamento), `test_diagnostic_intake.py` (US5). 37 testes, todos passando.
- **Testes frontend**: `form-templates.spec.ts`, `form-assignments.spec.ts`, `form-respond.spec.ts`. 30 testes, todos passando.
- **Migrations**: `wtnapp/alembic/versions/d6e7f8a9b005_workflow_module.py` (6 tabelas + RLS +
  triggers append-only em `form_assignment_events` e `form_signatures`).
- **Frontend** (`wtnadmin/`): `pages/form-templates/` (CRUD de template + auto-chave + arquivar/
  desarquivar; campos com metadados ricos: `section`, `order`, `mask`, `help_text`, `options` —
  persistidos no `schema` JSON, sem migration),
  `pages/form-assignments/` (lista + criar/atribuir com **dropdown de membros** + wizard/linha do tempo
  + assinar + devolver/cancelar/lembrar + **toggle de política de assinatura dupla**),
  `pages/form-fill/` (assumir/preencher/salvar/enviar), `pages/form-respond/` (rota pública tokenizada
  `/respond/:token` + OTP + assinatura avançada sem auth). Links no shell. A tela `pages/diagnostic/`
  foi **repaginada**: deixou de ter form-builder inline — agora lista os **templates de diagnóstico**
  (com ação Atribuir) e exibe o **diagnóstico vigente** (de `form_intake`). Permissões
  (`assign_form`, `fill_form`, `sign_form`, `view_form`) espelhadas em `core/permissions.ts`.
- **Testes manuais**: roteiro E2E em `docs/guia-de-testes-workflow.md` (membro, externo/token+OTP,
  devolução, política dupla, consumo do diagnóstico, isolamento). Fluxo externo exige *catcher* SMTP local.

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
isolamento + auditoria). Ver `docs/00-fundacao-multi-tenant.md` (índice dos prompts de
specify em `docs/README.md`).

<!-- SPECKIT START -->
## Plano ativo (Spec Kit)

**Feature 003 — Motor de Workflow de Preenchimento (atribuível e assinável)** (`003-workflow-preenchimento`) — implementada (37 testes backend + 30 testes frontend, todos passando)
- Plano: `specs/003-workflow-preenchimento/plan.md`
- Spec: `specs/003-workflow-preenchimento/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: capacidade **transversal** — template parametrizável → atribuição (membro ou link
  tokenizado) → preenchimento (assumir/salvar/enviar) → **assinatura avançada** (Lei 14.063/2020) →
  versão imutável, com trilha append-only/wizard. Diagnóstico é o 1º consumidor; Gap Analysis (004) usa.
- Decisões-chave (clarify): snapshot do template na atribuição; política de assinatura configurável por
  org (única padrão / contra-assinatura opcional); identidade do externo via vínculo + **OTP por
  e-mail** (fail-closed); campos obrigatórios validados no envio. Reusa convite/token, Documento
  Controlado/versões, auditoria, e-mail, RBAC e RLS.

**Feature 002 — Diagnóstico e Contexto da Organização** (`002-diagnostico-contexto`) — implementada (ver seção do módulo acima); pendente E2E manual + PostgreSQL real
- Plano: `specs/002-diagnostico-contexto/plan.md`
- Spec: `specs/002-diagnostico-contexto/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml`
- Escopo: Cláusula 4 do SGSI — Análise de Contexto (4.1, PESTEL/SWOT + impacto), Mapa de Partes
  Interessadas (4.2, Poder×Interesse/Mendelow) e Declaração de Escopo (4.3), como **documentos
  controlados versionados** (1 em vigor + rascunho paralelo).
- Decisões-chave: dados de trabalho relacionais + snapshot de versão imutável (append-only);
  1 conjunto por organização; aprovação só pelo Admin da organização (`approve_context_document`);
  classificação como rótulo + política de acesso por classificação configurável (RBAC-default);
  sugestões heurísticas (sem IA); reusa `tenant_scope`/RBAC/auditoria da fundação.

**Feature 001 — Fundação Multi-Tenant** (`001-fundacao-multi-tenant`) — implementada (ver seção do módulo acima)
- shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`) + RLS; JWT HS512 + `jti`
  em Redis (fail-open) + `password_changed_at`; Argon2id; contexto de org via `X-Org-Context`;
  cross-tenant ⇒ 404 genérico.
<!-- SPECKIT END -->

