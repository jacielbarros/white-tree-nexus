# Implementation Plan: Fundação Multi-Tenant (Organizações, Auth, RBAC, Isolamento, Auditoria)

**Branch**: `001-fundacao-multi-tenant` | **Date**: 2026-06-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-fundacao-multi-tenant/spec.md`

## Summary

Estabelecer a fundação multi-tenant da plataforma: organizações (tenants) com ciclo de vida,
autenticação JWT com sessão revogável e bloqueio de conta, RBAC granular por papel, isolamento
de dados estrito entre organizações e trilha de auditoria imutável. A abordagem técnica usa
PostgreSQL **shared-DB + `tenant_id`** com enforcement num **ponto único e não-contornável**
(`helpers/tenant_scope.py`), reforçado por **Row-Level Security (RLS)** como defesa em
profundidade. Autenticação é JWT HS512 com `jti` revogável no Redis (fail-open) e invalidação de
tokens anteriores na troca de senha via `password_changed_at`. Convites e redefinições de senha
usam tokens aleatórios armazenados apenas como hash, de uso único e com expiração. Todo o acesso
cross-tenant retorna 404/403 sem revelar existência e é auditado; o teste automatizado de
isolamento de tenant é o gate inegociável de pronto.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, python-jose
(JWT HS512), argon2-cffi (hash de senha), slowapi (rate limiting), Redis (revogação de `jti`) ·
PrimeNG 21, Angular Signals

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); Redis para denylist de `jti`

**Testing**: pytest + FastAPI TestClient (SQLite in-memory, override central de `get_db`) ·
Vitest + Angular TestBed. **Teste de isolamento de tenant obrigatório.**

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend) — greenfield
(diretórios de código ainda não existem; esta feature cria a base)

**Tenant Isolation Strategy**: **Shared-DB + coluna `tenant_id`** em todo modelo de domínio, com
enforcement central e não-contornável via dependency `tenant_scope` (resolve o tenant do JWT +
contexto de organização e filtra toda query). **Defesa em profundidade:** PostgreSQL Row-Level
Security nas tabelas escopadas, com `app.tenant_id` setado por requisição (`SET LOCAL`) na mesma
sessão do ORM. Rejeitada schema-per-tenant/db-per-tenant para o MVP (custo operacional de
migrations e provisionamento desproporcional ao volume inicial). Justificativa completa em
[research.md](research.md). Isolamento é **sempre fail-closed**.

**Performance Goals**: login e validação de token p95 < 300 ms; endpoints de listagem
(organizações/usuários/convites) p95 < 500 ms; aceite de convite e redefinição p95 < 800 ms
(inclui hashing Argon2id). Hashing de senha calibrado para ~100–250 ms por verificação.

**Constraints**: API stateless (JWT); Redis e SMTP tratados como dependências externas com
degradação graciosa (fail-open / fail-soft) — exceto isolamento de tenant e suspensão de
organização, que são **fail-closed**. Sem `AsyncSession`. Sem middleware novo além de CORS,
rate limiting e a dependency de resolução de tenant.

**Scale/Scope**: alvo inicial ~10³ organizações / ~10⁵ usuários; esta feature entrega ~6 routers
backend (bootstrap, auth, organizations, invitations, memberships/users, e leitura mínima de
contexto do usuário) e ~6 telas Angular (login, esqueci/redefinir senha, aceitar convite, gestão
de organizações, gestão de usuários/convites, troca de contexto de organização).

## Constitution Check

*GATE: Passou antes da Phase 0. Re-checado após a Phase 1 (design) — ver "Post-Design" abaixo.*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: toda query de domínio passa pelo escopo central
  (`helpers/tenant_scope.py`); nenhum filtro ad-hoc. Cross-tenant ⇒ 404/403 + audit. Reforço RLS
  no banco. Fail-closed. (Princípio I)
- [x] **RBAC**: cada endpoint usa `require_permission(...)`; matriz papel→permissão bate com
  SEC-002 (ver [data-model.md](data-model.md) §Papéis & Permissões). (Princípio II)
- [x] **Auditoria**: operações sensíveis chamam `AuditService.log_from_request()`; trilha
  append-only (sem UPDATE/DELETE); campos sem PII de conteúdo/segredos. (Princípio III)
- [x] **Integridade de evidências/artefatos**: N/A nesta feature — não cria artefato versionável
  de compliance (SEC-005). A única trilha imutável é o audit log. (Princípio IV)
- [x] **Dados sensíveis**: senhas via Argon2id (nunca recuperáveis); tokens de convite/reset
  apenas como hash; PII (e-mail/nome) nunca em logs/erros/auditoria; mensagens de erro genéricas.
  (Princípio V)

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy **síncrono**; `get_db()` central; novos routers
  registrados em `main.py`; config via `settings.py`+`load_dotenv()`; único middleware/dependency
  novo é a resolução de tenant (justificada na spec — FR-027/FR-029).
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`;
  Signals; Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelo SQLAlchemy **+** migration Alembic para toda tabela; modelos de domínio têm
  `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas principais **e teste de isolamento de tenant** planejados
  antes da implementação (ver [quickstart.md](quickstart.md) §Testes). (Princípio VI)
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant.

**Resultado do gate**: ✅ PASS — nenhuma violação. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/001-fundacao-multi-tenant/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (openapi.yaml + README.md)
└── tasks.md             # Phase 2 output (/speckit.tasks — NÃO criado aqui)
```

### Source Code (repository root) — a ser criado por esta feature

```text
wtnapp/                          # Backend FastAPI
├── main.py                       # app + CORS + rate limit + IntegrityError handler + health;
│                                 #   registra: bootstrap, auth, organizations, invitations,
│                                 #   memberships, me
├── settings.py                   # load_dotenv(); enums (Role, OrgStatus, ...); parâmetros
├── database/database.py          # engine, SessionLocal, get_db() centralizado
├── models/                       # base.py, organization_model.py, user_model.py,
│                                 #   membership_model.py, invitation_model.py,
│                                 #   password_reset_model.py, audit_log_model.py
├── schemas/                      # organization_schema.py, auth_schema.py, user_schema.py,
│                                 #   membership_schema.py, invitation_schema.py
├── routers/                      # bootstrap.py, auth.py, organizations.py, invitations.py,
│                                 #   memberships.py, me.py
├── services/                     # audit_service.py, crypto_service.py, notification_service.py,
│                                 #   token_service.py (JWT + jti revoke)
├── helpers/                      # permissions.py (require_permission + matriz),
│                                 #   tenant_scope.py (resolução + scoped_query + SET LOCAL RLS),
│                                 #   settings_helper.py
├── utils/                        # email.py (SMTP)
├── alembic/                      # migrations (inclui políticas RLS)
└── test/                         # conftest.py + test_* (inclui test_tenant_isolation.py)

wtnadmin/                        # Frontend Angular 21
└── src/app/
    ├── core/                     # auth (signals), interceptors (token + org context),
    │                             #   org-context store, guards (auth/role)
    ├── pages/                    # login, password (forgot/reset), invite-accept,
    │                             #   organizations, users, (org switcher)
    └── shared/                   # componentes/diretivas/pipes reutilizáveis
```

**Structure Decision**: Web application monorepo (backend `wtnapp/` + frontend `wtnadmin/`),
conforme constitution. Esta feature cria a base de ambos os módulos.

## Complexity Tracking

> Nenhuma violação do Constitution Check. Tabela intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 — Research

Concluída. Decisões consolidadas em [research.md](research.md): estratégia de isolamento
(shared-DB + tenant_id + RLS), modelo de sessão JWT/`jti`/`password_changed_at`, hashing Argon2id,
política de bloqueio (auto-expiração + desbloqueio manual + reset), tokens de convite/reset
(hash + uso único), bootstrap protegido por `BOOTSTRAP_TOKEN`, regra 404-vs-403, e seleção de
contexto de organização para Consultor/Super Admin.

## Phase 1 — Design & Contracts

Concluída:

- **[data-model.md](data-model.md)** — entidades (Organization, User, Membership, Invitation,
  PasswordResetToken, AuditLog), campos, constraints, transições de estado, matriz
  papel→permissão e políticas RLS.
- **[contracts/openapi.yaml](contracts/openapi.yaml)** — endpoints REST com respostas de erro
  padronizadas e convenções de segurança; **[contracts/README.md](contracts/README.md)** com as
  convenções transversais.
- **[quickstart.md](quickstart.md)** — setup, `.env`, fluxo bootstrap→organização→convite→login,
  e estratégia de testes (com isolamento de tenant).
- **Agent context** — `CLAUDE.md` atualizado com o ponteiro do plano ativo entre marcadores
  `<!-- SPECKIT START/END -->`.

### Post-Design Constitution Re-Check

Re-avaliado após o design: ✅ PASS. O design mantém escopo central de tenant + RLS, RBAC por
`require_permission`, auditoria append-only sem PII, Argon2id e tokens hash. Nenhuma nova
violação introduzida; Complexity Tracking permanece vazio.

## Phase 2 — Próximo passo

`/speckit.tasks` para gerar `tasks.md` (decomposição dependency-ordered). **Não** gerado por este
comando.
