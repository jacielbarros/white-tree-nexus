# Implementation Plan: [FEATURE]

**Branch**: `[###-feature-name]` | **Date**: [DATE] | **Spec**: [link]

**Input**: Feature specification from `/specs/[###-feature-name]/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command.

## Summary

[Extract from feature spec: primary requirement + technical approach from research]

## Technical Context

<!--
  ACTION REQUIRED: Replace with the technical details for this feature.
  Os defaults da White Tree Nexus já estão preenchidos — ajuste só o que mudar.
-->

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, python-jose,
slowapi, Redis · PrimeNG 21, Angular Signals

**Storage**: PostgreSQL (Alembic + `create_all()` no startup)

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: [shared-DB + `tenant_id` com enforcement na app (default MVP) /
schema-per-tenant / db-per-tenant — DECIDIR e justificar aqui. O *princípio* é da constitution;
a *implementação* é desta decisão.]

**Performance Goals**: [domain-specific ou NEEDS CLARIFICATION]

**Constraints**: [domain-specific ou NEEDS CLARIFICATION]

**Scale/Scope**: [nº de organizações/usuários esperado, nº de telas, etc.]

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar após a Phase 1 (design).*

> Marque cada item. Qualquer `[ ]` não-atendido é uma violação que vai para **Complexity
> Tracking** com justificativa, OU bloqueia o plano. Derivado de `.specify/memory/constitution.md`.

**Segurança (Core Principles I–V):**

- [ ] **Isolamento de tenant**: toda query de domínio passa pelo escopo central
  (`helpers/tenant_scope.py`); nenhum filtro de tenant ad-hoc. Acesso cross-tenant ⇒ 404/403
  + audit. (Princípio I — fail-closed, nunca degradar.)
- [ ] **RBAC**: cada endpoint usa `require_permission(...)`; papéis e permissões batem com a
  spec (SEC-002). (Princípio II)
- [ ] **Auditoria**: operações sensíveis chamam `AuditService.log_from_request()`; trilha
  append-only; sem PII/segredos nos campos. (Princípio III)
- [ ] **Integridade de evidências/artefatos**: alterações versionadas, append-only, com
  autor/data/ação (se aplicável — SEC-005). (Princípio IV)
- [ ] **Dados sensíveis**: PII/confidencial cifrado em repouso quando aplicável; nunca em
  logs/erros/telemetria. (Princípio V)

**Arquitetura (Regras que não dobram):**

- [ ] Backend: sem repository layer; SQLAlchemy **síncrono** (sem `AsyncSession`); `get_db()`
  central; novos routers registrados em `main.py`; config via `settings.py`+`load_dotenv()`;
  sem middleware novo sem requisito explícito.
- [ ] Frontend: standalone (sem NgModules); `input()`/`output()`; `inject()`; control flow
  nativo; `OnPush`; Signals; Reactive Forms (`NonNullableFormBuilder`).
- [ ] Schema: modelo SQLAlchemy **+** migration Alembic para toda mudança de tabela; modelos de
  domínio têm `tenant_id`.

**Qualidade (Definition of Done):**

- [ ] **Test-first**: testes de happy path, falhas principais **e teste de isolamento de
  tenant** planejados antes da implementação. (Princípio VI — NÃO opcional neste projeto.)
- [ ] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit.tasks — NÃO criado pelo /speckit.plan)
```

### Source Code (repository root)

```text
wtnapp/                      # Backend FastAPI
├── models/                   # ORM (<domain>_model.py) — todos com tenant_id
├── schemas/                  # Pydantic (<domain>_schema.py)
├── routers/                  # Endpoints (<domain>.py)
├── services/                 # audit_service, crypto_service, notification_service
├── helpers/                  # permissions.py, tenant_scope.py, settings_helper.py
├── core/security/
├── utils/
├── database/database.py      # get_db() centralizado
├── main.py                   # registra routers
├── alembic/
└── test/                     # pytest (inclui teste de isolamento de tenant)

wtnadmin/                    # Frontend Angular 21
└── src/app/
    ├── core/                 # serviços singleton
    ├── pages/                # rotas lazy-loaded
    └── shared/               # componentes/diretivas/pipes reutilizáveis
```

**Structure Decision**: Web application monorepo (backend `wtnapp/` + frontend `wtnadmin/`).
[Ajustar/expandir com os diretórios concretos desta feature.]

## Complexity Tracking

> **Preencher SOMENTE se o Constitution Check tiver violações que precisam ser justificadas.**
> Violações de **isolamento de tenant** exigem aprovação explícita documentada — não são um
> simples trade-off.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| [ex.: middleware novo] | [necessidade atual] | [por que CORS/rate-limit não bastam] |
