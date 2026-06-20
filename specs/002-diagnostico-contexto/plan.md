# Implementation Plan: Diagnóstico e Contexto da Organização (ISO/IEC 27001 — Cláusula 4)

**Branch**: `002-diagnostico-contexto` | **Date**: 2026-06-19 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-diagnostico-contexto/spec.md`

## Summary

Módulo da Cláusula 4 do SGSI sobre a fundação multi-tenant existente. Entrega um
diagnóstico-questionário incremental e três **documentos controlados versionados** — Análise de
Contexto (4.1), Mapa de Partes Interessadas (4.2) e Declaração de Escopo (4.3) — com rastreabilidade
entre si. Abordagem técnica: dados de trabalho **relacionais** (questões, partes, requisitos, itens
de escopo) que materializam o "rascunho corrente" de cada artefato; ao aprovar, congela-se uma
**versão imutável (snapshot JSON)** com os metadados de "Documento Controlado SGSI (7.5)" — mantendo
**exatamente uma versão "em vigor"** por artefato e um rascunho paralelo em revisão (decisão de
clarify). Reutiliza `helpers/tenant_scope.py` (+ RLS) e `helpers/permissions.py` (novas permissões
`view_context` / `manage_context` / `approve_context_document`). Classificação da informação é
rótulo de governança com **política de acesso por classificação configurável por organização**
(default: RBAC-apenas). Sugestões são heurísticas/regras locais (sem IA).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, python-jose,
argon2-cffi, slowapi, Redis · PrimeNG 21, Angular Signals (tudo já presente da fundação)

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); RLS nas tabelas escopadas

**Testing**: pytest + FastAPI TestClient (SQLite in-memory, override central de `get_db`) ·
Vitest + Angular TestBed. **Teste de isolamento de tenant obrigatório.**

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo `wtnapp/` + `wtnadmin/`) — estende a fundação 001

**Tenant Isolation Strategy**: Inalterada da fundação — shared-DB + `tenant_id` com escopo central
não-contornável (`tenant_scope`) + RLS (defesa em profundidade) nas novas tabelas escopadas. Toda
query de domínio passa pelo escopo central; cross-tenant ⇒ 404/403 + audit (fail-closed).

**Performance Goals**: edição/listagem de artefatos e questões/partes p95 < 500 ms; geração de
sugestões heurísticas p95 < 1 s; emissão de versão (snapshot) p95 < 800 ms.

**Constraints**: sem `AsyncSession`; sem middleware novo (reusa CORS/rate-limit/tenant-scope da
fundação); sem dependência de infra externa crítica (sugestões são locais; sem e-mail/IA aqui).

**Scale/Scope**: por organização — 1 diagnóstico + 1 conjunto dos 3 artefatos; ordem de dezenas de
questões e partes interessadas, poucas dezenas de versões ao longo do tempo. ~5 routers backend e
~5 telas Angular.

## Constitution Check

*GATE: Passou antes da Phase 0. Re-checado após a Phase 1 — ver "Post-Design".*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: novas tabelas têm `tenant_id`; queries via `tenant_scope`; RLS
  habilitada; cross-tenant ⇒ 404/403 + audit. (Princípio I)
- [x] **RBAC**: novas permissões `view_context`/`manage_context`/`approve_context_document` via
  `require_permission`; aprovação restrita ao Admin da organização (clarify). (Princípio II)
- [x] **Auditoria**: salvar diagnóstico, criar/editar/transicionar/aprovar/obsoletar e tentativa
  cross-tenant chamam `AuditService.log_from_request()`; sem PII/segredos. (Princípio III)
- [x] **Integridade e versionamento de artefatos**: versões são **append-only** (snapshot imutável
  com autor/data/ação/aprovador); ciclo aprovação/obsolescência rastreável; "1 em vigor + rascunho
  paralelo". (Princípio IV — central nesta feature.)
- [x] **Dados sensíveis**: classificação por artefato; conteúdo confidencial nunca em
  logs/erros/telemetria; cifragem de campos sensíveis em repouso quando aplicável. (Princípio V)

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novos routers em
  `main.py`; config via `settings.py`; sem middleware novo.
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`;
  Signals; Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelo SQLAlchemy **+** migration Alembic; novas tabelas com `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas principais **e teste de isolamento de tenant** planejados
  antes da implementação. (Princípio VI)
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant.

**Resultado do gate**: ✅ PASS — sem violações. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/002-diagnostico-contexto/
├── plan.md · research.md · data-model.md · quickstart.md · contracts/ · checklists/
└── tasks.md   # /speckit.tasks (não criado aqui)
```

### Source Code (adições à fundação)

```text
wtnapp/
├── models/         # diagnostic_model, context_analysis_model, context_issue_model,
│                   #   stakeholder_map_model, stakeholder_model, stakeholder_requirement_model,
│                   #   scope_statement_model, scope_item_model, document_version_model,
│                   #   classification_policy_model  (todos com tenant_id)
├── schemas/        # diagnostic_schema, context_schema, stakeholder_schema, scope_schema,
│                   #   document_version_schema
├── routers/        # diagnostic.py, context_analysis.py, stakeholders.py, scope.py,
│                   #   context_overview.py (visão consolidada + sugestões)  → registrados em main.py
├── services/       # controlled_document_service.py (ciclo de vida/versão/snapshot),
│                   #   suggestion_service.py (heurística)
├── helpers/        # permissions.py (estende a matriz); classification_access.py (política por org)
└── test/           # test_context_*, test_stakeholders_*, test_scope_*, test_document_version_*,
                    #   test_tenant_isolation (estende)

wtnadmin/src/app/pages/
├── diagnostic/        # questionário incremental (rascunho/retomar)
├── context-analysis/  # questões PESTEL/SWOT + impacto
├── stakeholders/      # mapa + matriz Poder×Interesse
├── scope/             # declaração de escopo (3 entradas, inclusões/exclusões)
└── context-overview/  # visão consolidada + sugestões
```

**Structure Decision**: estende o monorepo da fundação (`wtnapp/` + `wtnadmin/`), reusando auth,
tenant_scope, RBAC e auditoria.

## Complexity Tracking

> Sem violações do Constitution Check. Tabela intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 — Research

Concluída em [research.md](research.md): modelo de documento controlado (dados relacionais de
trabalho + snapshot de versão imutável; "1 em vigor + rascunho paralelo"), one-set-per-org,
classificação de informação com política de acesso configurável (RBAC-default), motor de sugestões
heurísticas, e rastreabilidade entre artefatos com referência por versão.

## Phase 1 — Design & Contracts

Concluída: [data-model.md](data-model.md) (entidades, estados, RLS), [contracts/openapi.yaml](contracts/openapi.yaml)
+ [contracts/README.md](contracts/README.md), [quickstart.md](quickstart.md). `CLAUDE.md` atualizado
(marcadores SPECKIT) para apontar este plano.

### Post-Design Constitution Re-Check

✅ PASS. Versões append-only + escopo central + RBAC por `require_permission` + auditoria sem PII
mantidos. Sem novas violações; Complexity Tracking vazio.

## Phase 2 — Próximo passo

`/speckit.tasks` para gerar `tasks.md`. **Não** gerado por este comando.
