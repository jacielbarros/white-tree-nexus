---
description: "Task list for feature 001 — Fundação Multi-Tenant"
---

# Tasks: Fundação Multi-Tenant (Organizações, Auth, RBAC, Isolamento, Auditoria)

**Input**: Design documents from `/specs/001-fundacao-multi-tenant/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml)

**Tests**: ⚠️ **OVERRIDE da constitution (White Tree Nexus):** testes NÃO são opcionais.
Toda story de domínio inclui **teste de isolamento de tenant** + casos de falha principais
(Princípio VI + Definition of Done).

**Organization**: Tasks agrupadas por user story (US1–US5) para implementação/teste
independentes. Greenfield: `wtnapp/` (backend) e `wtnadmin/` (frontend) são criados aqui.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependências pendentes)
- **[Story]**: US1–US5 (rastreabilidade). Setup/Foundational/Polish não têm label.

## Path Conventions

- Backend: `wtnapp/` (models, schemas, routers, services, helpers, utils, test, alembic)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)

---

## Implementation Status — Incrementos de backend

**Concluído e verificado** (`pytest wtnapp/test` → **40 passed**, incl. teste de isolamento de
tenant — **todo o backend da fundação, US1–US5**):
- **Incremento 1** — Phase 1 (Setup) + Phase 2 (Foundational) + Phase 3 (US1 backend): modelos +
  `create_all()`, auth (login/bloqueio/logout), `/me` e `/me/context`, `tenant_scope` (+ guarda
  RLS via `SET LOCAL`, ativa só no PostgreSQL), RBAC e auditoria.
- **Incremento 2** — Phase 4 (US2 backend): bootstrap do 1º Super Admin (`/bootstrap/super-admin`),
  ciclo de vida de organizações (criar/listar escopado/detalhar/suspender/reativar) com
  `require_super_admin`, listagem escopada (FR-005) e auditoria.
- **Incremento 3** — Phase 5 (US3 backend): model `Invitation` + convites
  (criar/listar/aceitar-público/revogar/reenviar, token só por hash, FR-020), memberships
  (listar usuários, mudar papel, ativar/desativar, desbloquear) com salvaguardas FR-022,
  `notification_service`/`utils.email` (fail-soft). Inclui o fluxo do admin inicial (FR-002a).
- **Incremento 4** — Phase 6 (US4) + Phase 7 (US5): redefinição de senha
  (`/auth/password/forgot|reset`, genérico, uso único, invalida sessões via `password_changed_at`,
  limpa bloqueio) e model `PasswordResetToken`; **auditoria append-only** via gatilho de banco
  (SQLite + PostgreSQL) + varredura de cobertura.

- **Incremento 5** — Migrations Alembic: scaffold (`alembic.ini`, `env.py` → `Base.metadata`),
  migration inicial autogerada (`18d01e15da30`, 6 tabelas + índices, incl. índice parcial) e
  migration **`b2c3d4e5f601`** (RLS no PostgreSQL + gatilho append-only SQLite/PG). Verificado:
  `alembic upgrade head`/`downgrade base` + `alembic check` (sem drift) em SQLite.

**Pendente (próximos incrementos):**
- **Frontend Angular**: T002, T018, T025, T026, T033, T042, T043, T047.
- **Tooling frontend** (T003: Vitest/eslint/prettier) — backend (pytest + ruff) feito.
- **Polish restante**: T052–T055, T057 (varreduras finais, CSP/HSTS, docs, validação do
  quickstart, testes de frontend).
- **Validação de RLS contra PostgreSQL real** (a migration é PG-only; os testes rodam em SQLite).

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Scaffold do backend em `wtnapp/`: estrutura de diretórios (models, schemas, routers,
  services, helpers, utils, database, alembic, test), `requirements.txt` (FastAPI, SQLAlchemy
  síncrono, Pydantic v2, Alembic, python-jose, argon2-cffi, slowapi, redis, psycopg),
  `wtnapp/settings.py` (`load_dotenv()` + enums + parâmetros) e `wtnapp/database/database.py`
  (engine, `SessionLocal`, `get_db()` centralizado); `alembic init wtnapp/alembic`
- [ ] T002 [P] Scaffold do frontend em `wtnadmin/`: Angular 21 standalone, `src/app/app.ts`,
  `src/app/app.config.ts` (router + PrimeNG preset Material), `src/app/app.routes.ts`,
  ambientes e path aliases `@app/*` e `@environment/*` no `tsconfig.json`
- [ ] T003 [P] Tooling: configurar pytest (+ `wtnapp/test/`), Vitest, lint/format (ruff +
  prettier/eslint) e scripts em `package.json`/`pyproject.toml`
- [X] T004 [P] Criar `.env.example` com todas as variáveis (incl. `LOCKOUT_DURATION_MINUTES=15`,
  `INVITE_EXPIRY_HOURS=72`, `PASSWORD_MIN_LENGTH=12`, `BOOTSTRAP_TOKEN=`) — ver research.md

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infra central que TODAS as user stories dependem. **⚠️ Nenhuma user story começa
antes desta fase terminar.**

- [X] T005 Base declarativa em `wtnapp/models/base.py` + wiring do Alembic (`env.py` →
  `Base.metadata`) + `create_all()` no startup (mantido junto com migrations)
- [X] T006 [P] Model `Organization` (name, slug único, status, created_by) + migration em
  `wtnapp/models/organization_model.py`
- [X] T007 [P] Model `User` (email único, password_hash nullable, status, failed_login_count,
  locked_until, password_changed_at, is_platform_super_admin) + migration em
  `wtnapp/models/user_model.py`
- [X] T008 [P] Model `Membership` (tenant_id FK, user_id FK, role, status, unique
  `(tenant_id, user_id)`) + migration em `wtnapp/models/membership_model.py`
- [X] T009 [P] Model `AuditLog` (actor, actor_role, tenant_id nullable, operation, entity_type,
  entity_id, outcome, ip, user_agent, details JSONB, created_at) + migration em
  `wtnapp/models/audit_log_model.py`
- [X] T010 Migration de **RLS**: `ENABLE`/`FORCE ROW LEVEL SECURITY` + policy
  `tenant_id = current_setting('app.tenant_id')::uuid` em `memberships` e `invitations` (apenas
  PostgreSQL) — em `wtnapp/alembic/versions/b2c3d4e5f601_rls_and_audit_append_only.py`
- [X] T011 [P] `crypto_service` em `wtnapp/services/crypto_service.py`: Argon2id hash/verify,
  geração de segredo (`secrets.token_urlsafe`) e hash SHA-256 de tokens
- [X] T012 [P] `token_service` em `wtnapp/services/token_service.py`: JWT HS512 (claims `sub`,
  `tenant_ids`, `role`, `iss`, `iat`, `exp`, `jti`), rejeição por `iat < password_changed_at`,
  denylist de `jti` no Redis (fail-open + warning)
- [X] T013 `tenant_scope` em `wtnapp/helpers/tenant_scope.py`: resolve tenant do JWT +
  `X-Org-Context`, valida pertença/Super Admin, **fail-closed** em org suspensa, `scoped_query()`
  e `SET LOCAL app.tenant_id` na sessão ORM (depende de T007/T008/T012)
- [X] T014 [P] `permissions` em `wtnapp/helpers/permissions.py`: enum `Role`, matriz
  papel→permissão (data-model.md) e factory `require_permission(...)` (negação ⇒ 403 + audit)
- [X] T015 [P] `AuditService.log_from_request()` em `wtnapp/services/audit_service.py`: sessão
  própria (`SessionLocal`), append-only, sem PII/segredos, `outcome` success/denied
- [X] T016 `wtnapp/main.py`: FastAPI app + CORS + rate limiting (slowapi) + handler de
  `IntegrityError` + handlers genéricos de erro (sem vazar stack/tabela/existência) + health check
  com DB + `create_all()` no startup + ponto de registro de routers
- [X] T017 Harness de testes em `wtnapp/test/conftest.py`: SQLite in-memory, override central de
  `get_db`, `REDIS_URL=""`, audit em sink SQLite, e fixtures para semear organização/usuário/
  vínculo e emitir tokens
- [ ] T018 [P] Core do frontend em `wtnadmin/src/app/core/`: estado de auth com Signals,
  HTTP interceptor (`Authorization: Bearer` + `X-Org-Context`), `authGuard`/`roleGuard` e store de
  contexto de organização

**Checkpoint**: Fundação pronta — user stories podem começar.

---

## Phase 3: User Story 1 — Acesso seguro e isolamento de dados (Priority: P1) 🎯 MVP

**Goal**: Login com sessão expirável, logout que encerra a sessão, bloqueio após N falhas, e
isolamento estrito: usuário só vê/opera dados da(s) sua(s) organização(ões).

**Independent Test**: Com org+usuário seedados, verificar login/expiração/logout, bloqueio após
`MAX_LOGIN_ATTEMPTS`, e — com 2 orgs — que A não acessa recurso de B (404/403 + audit).

### Tests for User Story 1 (MANDATORY) ⚠️

- [X] T019 [P] [US1] **Teste de isolamento de tenant**: token do tenant A acessando recurso/
  contexto do tenant B ⇒ 404/403 + audit, em `wtnapp/test/test_tenant_isolation.py`
- [X] T020 [P] [US1] Testes de auth (happy path, expiração de sessão, logout revoga `jti`) em
  `wtnapp/test/test_auth.py`
- [X] T021 [P] [US1] Testes de falha de auth (credencial inválida ⇒ 401 genérico; bloqueio após
  `MAX_LOGIN_ATTEMPTS`; org suspensa ⇒ negado) em `wtnapp/test/test_auth_failures.py`
- [X] T021a [P] [US1] Teste de **auto-expiração do bloqueio** (FR-009a/SC-003): com `locked_until`
  no passado, o login volta a ser aceito e o contador zera — em `wtnapp/test/test_auth_failures.py`

### Implementation for User Story 1

- [X] T022 [P] [US1] Schemas de auth em `wtnapp/schemas/auth_schema.py` (login request/response,
  `Me`)
- [X] T023 [US1] Router de auth em `wtnapp/routers/auth.py`: `POST /auth/login` (verifica
  Argon2id, lógica de bloqueio com `failed_login_count`/`locked_until`, checa status da org, emite
  JWT, audita LOGIN/LOGIN_FAILED/ACCOUNT_LOCKED) e `POST /auth/logout` (revoga `jti`, audita) com
  rate limiting; registrar em `main.py`
- [X] T024 [US1] Router `GET /me` em `wtnapp/routers/me.py` (retorna vínculos+papéis, valida
  contexto via `tenant_scope`); registrar em `main.py`
- [ ] T025 [P] [US1] Página de login em `wtnadmin/src/app/pages/login/` (Reactive Forms +
  `NonNullableFormBuilder`, Signals, OnPush)
- [ ] T026 [P] [US1] Seletor de contexto de organização + aplicação do `authGuard` no shell em
  `wtnadmin/src/app/` (usa o store de contexto do core)

**Checkpoint**: US1 funcional e isolamento de tenant verificado — **MVP entregável**.

---

## Phase 4: User Story 2 — Provisionamento e ciclo de vida de organizações (Priority: P2)

**Goal**: Bootstrap único do 1º Super Admin; Super Admin cria organizações e controla
ativar/suspender/reativar (suspensão bloqueia usuários, fail-closed).

**Independent Test**: Bootstrap uma vez (2ª ⇒ 409); criar org (slug dup ⇒ 409); suspender (users
não operam) e reativar; ações do Super Admin auditadas.

### Tests for User Story 2 (MANDATORY) ⚠️

- [X] T027 [P] [US2] Testes de bootstrap (sucesso único; 2ª chamada ⇒ 409; `BOOTSTRAP_TOKEN`
  inválido ⇒ 401) em `wtnapp/test/test_bootstrap.py`
- [X] T028 [P] [US2] Testes de ciclo de vida de org (criar, slug duplicado ⇒ 409, suspender
  bloqueia usuários fail-closed, reativar; Super Admin auditado) em
  `wtnapp/test/test_organizations.py`
- [X] T029 [P] [US2] Teste de listagem escopada (FR-005): não-Super-Admin lista apenas sua org —
  em `wtnapp/test/test_organizations.py` (`test_organization_listing_is_scoped`)

### Implementation for User Story 2

- [X] T030 [P] [US2] Schemas de organização em `wtnapp/schemas/organization_schema.py`
- [X] T031 [US2] Router de bootstrap em `wtnapp/routers/bootstrap.py`:
  `POST /bootstrap/super-admin` guardado (nenhum Super Admin existente **+** `BOOTSTRAP_TOKEN`),
  audita BOOTSTRAP; registrar em `main.py`
- [X] T032 [US2] Router de organizações em `wtnapp/routers/organizations.py` (create, list
  escopada, get, `PATCH /status` suspend/reactivate) com `require_permission("manage_organizations")`
  e audit ORG_CREATE/ORG_STATUS_CHANGE; registrar em `main.py`
- [ ] T033 [P] [US2] Página de gestão de organizações em `wtnadmin/src/app/pages/organizations/`

**Checkpoint**: US1 + US2 funcionam independentemente.

---

## Phase 5: User Story 3 — Convite de usuários e RBAC (Priority: P3)

**Goal**: Convidar usuário com papel (expira/revogável), aceite que define senha e ativa vínculo,
mudança de papel, e enforcement de permissão por papel; Consultor multi-org, demais single-org.

**Independent Test**: Convidar→aceitar→autenticar; convite expirado/revogado ⇒ 400; ação sem
permissão ⇒ 403+audit; mudança de papel auditada (salvaguarda de último admin ⇒ 409); Consultor
opera em A e B mas não em C.

### Tests for User Story 3 (MANDATORY) ⚠️

- [X] T034 [P] [US3] Testes de convite (criar; pendente duplicado ⇒ 409; vínculo já existe ⇒ 409;
  aceitar ativa+define senha; expirado/revogado ⇒ 400) em `wtnapp/test/test_invitations.py`
- [X] T035 [P] [US3] Testes de RBAC/memberships (sem `invite_users` ⇒ 403+audit; mudança de papel
  auditada; salvaguarda de último admin ⇒ 409) em `wtnapp/test/test_rbac_memberships.py`
- [X] T035a [P] [US3] Teste de **desbloqueio manual** (FR-009a/SC-003): `POST /users/{id}/unlock`
  por papel autorizado limpa o bloqueio e é auditado; sem `manage_memberships` ⇒ 403 — em
  `wtnapp/test/test_rbac_memberships.py`
- [X] T036 [P] [US3] Teste de Consultor multi-org + invariante FR-020 (não-Consultor = 1 vínculo)
  — estender `wtnapp/test/test_tenant_isolation.py`
- [X] T036a [P] [US3] Teste do **admin inicial** (FR-002a / US2-cenário 7): Super Admin convida
  `org_admin` para org recém-criada → aceite ativa o vínculo → o admin consegue convidar os
  demais; sem criação direta de conta — em `wtnapp/test/test_invitations.py`

### Implementation for User Story 3

- [X] T037 [P] [US3] Model `Invitation` + migration + policy RLS em
  `wtnapp/models/invitation_model.py` (unique parcial `(tenant_id, email)` enquanto `pending`)
- [X] T038 [P] [US3] Schemas em `wtnapp/schemas/invitation_schema.py` e
  `wtnapp/schemas/membership_schema.py`
- [X] T039 [P] [US3] `notification_service` + `utils/email` (SMTP best-effort) em
  `wtnapp/services/notification_service.py` e `wtnapp/utils/email.py`
- [X] T040 [US3] Router de convites em `wtnapp/routers/invitations.py` (create, list, `accept`
  público, revoke, resend) com token via `crypto_service` (só hash), e-mail best-effort,
  enforcement FR-020 e audit; registrar em `main.py`
- [X] T041 [US3] Router de memberships em `wtnapp/routers/memberships.py` (list users, `PATCH
  /role`, `PATCH /status`, `POST /users/{id}/unlock`) com salvaguardas (último admin/Super Admin),
  `require_permission("manage_memberships")` e audit; registrar em `main.py`
- [ ] T042 [P] [US3] Página pública de aceite de convite em `wtnadmin/src/app/pages/invite-accept/`
- [ ] T043 [P] [US3] Página de gestão de usuários e convites em `wtnadmin/src/app/pages/users/`

**Checkpoint**: US1–US3 funcionam independentemente.

---

## Phase 6: User Story 4 — Definição e redefinição de senha (Priority: P4)

**Goal**: Esqueci a senha → token de uso único com validade → nova senha; resposta genérica
(sem enumeração) e invalidação de sessões anteriores.

**Independent Test**: Solicitar reset (e-mail existente/inexistente ⇒ resposta genérica); usar
token uma vez dentro da validade; autenticar com nova senha; token expirado/usado ⇒ 400; sessões
anteriores invalidadas.

### Tests for User Story 4 (MANDATORY) ⚠️

- [X] T044 [P] [US4] Testes de redefinição (forgot genérico; reset uso único + expiração;
  invalida sessões anteriores via `password_changed_at`; reset bem-sucedido **limpa o bloqueio de
  conta** (FR-009a/SC-003); expirado/usado ⇒ 400) em `wtnapp/test/test_password_reset.py`

### Implementation for User Story 4

- [X] T045 [P] [US4] Model `PasswordResetToken` + migration em
  `wtnapp/models/password_reset_model.py`
- [X] T046 [US4] Endpoints em `wtnapp/routers/auth.py`: `POST /auth/password/forgot` (rate
  limited, genérico, cria token, e-mail best-effort) e `POST /auth/password/reset` (consome token,
  grava hash Argon2id, atualiza `password_changed_at`, audita) — **depende de T023** (mesmo arquivo)
- [ ] T047 [P] [US4] Páginas de esqueci/redefinir senha em `wtnadmin/src/app/pages/password/`

**Checkpoint**: US1–US4 funcionam independentemente.

---

## Phase 7: User Story 5 — Trilha de auditoria imutável (Priority: P5)

**Goal**: Toda ação sensível gera exatamente 1 registro append-only, sem PII/segredos; registros
não podem ser editados/apagados.

**Independent Test**: Amostra de ações sensíveis ⇒ 1 registro cada com campos exigidos e sem
segredo/PII; UPDATE/DELETE em `audit_logs` é rejeitado.

### Tests for User Story 5 (MANDATORY) ⚠️

- [X] T048 [P] [US5] Teste de completude de auditoria (cada ação sensível ⇒ 1 registro com
  ator/operation/entity/outcome; sem PII/segredos) em `wtnapp/test/test_audit.py`
- [X] T049 [P] [US5] Teste de imutabilidade (UPDATE/DELETE em `audit_logs` rejeitado) em
  `wtnapp/test/test_audit.py`

### Implementation for User Story 5

- [X] T050 [US5] Trigger que bloqueia UPDATE/DELETE em `audit_logs` (SQLite + PostgreSQL) via
  DDL event em `wtnapp/models/audit_log_model.py` (criado junto com a tabela; versão Alembic
  pendente junto com as demais migrations)
- [X] T051 [US5] Varredura de cobertura de auditoria: toda operação sensível em
  `wtnapp/routers/*` chama `AuditService.log_from_request()` com `operation`/`outcome` corretos e
  sem PII (incl. CROSS_TENANT_DENIED) — verificado por T048

**Checkpoint**: Todas as 5 stories completas.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T052 [P] **Tenant isolation sweep**: confirmar que nenhuma query de domínio escapou do
  `tenant_scope` e que RLS está habilitada em todas as tabelas escopadas (`memberships`,
  `invitations`)
- [ ] T053 [P] Configurar headers de segurança (CSP/HSTS opt-in) via `settings.py` em
  `wtnapp/main.py`
- [ ] T054 [P] Atualizar docs: seção do módulo em `CLAUDE.md` e `docs/` (fundação implementada)
- [ ] T055 Validar `quickstart.md` end-to-end (bootstrap → org → convite → login → isolamento)
- [X] T056 [P] Verificar paridade migrations ↔ `create_all()`: `alembic upgrade head` + `alembic
  check` em DB limpa (SQLite) ⇒ "No new upgrade operations detected"; upgrade/downgrade OK
- [ ] T057 [P] Testes unitários de frontend (auth, guards, interceptor) em
  `wtnadmin/src/app/core/*.spec.ts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **bloqueia todas as user stories**.
- **User Stories (Phase 3–7)**: dependem da Foundational. Após ela, US1–US5 são independentes e
  podem ser tocadas por devs diferentes; recomenda-se ordem de prioridade P1→P5.
- **Polish (Phase 8)**: depende das stories desejadas.

### Cross-story file notes (não quebram independência, mas serializam edição do arquivo)

- `wtnapp/routers/auth.py`: criado em **T023** (US1); estendido em **T046** (US4).
- `wtnapp/test/test_tenant_isolation.py`: criado em **T019** (US1); estendido em **T029/T036**.
- `wtnapp/main.py`: registro de routers a cada story (T023/T024, T031/T032, T040/T041, T046).

### Within Each User Story

- Tests (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação.
- Models → schemas → services → routers → frontend.

---

## Parallel Opportunities

- **Setup**: T002, T003, T004 em paralelo (T001 primeiro fornece a estrutura backend).
- **Foundational**: T006–T009 (models) em paralelo; T011, T012, T014, T015, T018 em paralelo após
  os models; T013 depende de T007/T008/T012; T016/T017 ao final.
- **US1 tests**: T019, T020, T021 em paralelo. **US1 frontend**: T025, T026 em paralelo ao backend.
- **Entre stories**: após a Foundational, US1–US5 podem avançar em paralelo (respeitando as notas
  de arquivos cross-story acima).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → 2. Phase 2 (Foundational, CRITICAL) → 3. Phase 3 (US1, incl. teste de
   isolamento) → **STOP e VALIDE** US1 isoladamente → demo (MVP).

### Incremental Delivery

Setup + Foundational → US1 (MVP) → US2 → US3 → US4 → US5 → Polish. Cada story agrega valor sem
quebrar as anteriores; o teste de isolamento de tenant é re-executado a cada story que adiciona
recurso escopado.

---

## Notes

- **Teste de isolamento de tenant é obrigatório** (não é "polish") — Princípio VI da constitution.
- Garanta que os testes falham antes de implementar.
- Toda operação sensível chama `AuditService`; nenhum log/erro expõe PII/segredos.
- Nenhum filtro de tenant ad-hoc — sempre via `tenant_scope` (+ RLS como defesa em profundidade).
- Commit após cada task ou grupo lógico.

**Total: 60 tasks** — Setup 4 · Foundational 14 · US1 9 · US2 7 · US3 12 · US4 4 · US5 4 · Polish 6
(inclui T021a, T035a e T036a — mais o reforço de T044 — adicionados na remediação do
`/speckit-analyze` para cobrir FR-009a/SC-003 e FR-002a.)
