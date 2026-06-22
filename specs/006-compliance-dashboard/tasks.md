---
description: "Task list — Feature 006: Dashboard de Conformidade"
---

# Tasks: Dashboard de Conformidade

**Input**: Design documents from `/specs/006-compliance-dashboard/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml),
[quickstart.md](quickstart.md)

**Tests**: ⚠️ Obrigatórios (constitution Princípio VI) — inclui **teste de isolamento de tenant** +
casos de falha. Escritos antes da implementação dentro de cada story.

**Organization**: por user story (US1 = MVP, US2 = P2). **Sem novo modelo de domínio, sem migration**
(feature read-only que agrega serviços existentes).

## Path Conventions

- Backend: `wtnapp/` (routers, services, schemas, helpers, test)
- Frontend: `wtnadmin/src/app/` (pages/dashboard, core)

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Confirmar branch `006-compliance-dashboard` e que **não há dependências novas** nem
  migration (feature read-only). Revisar a Structure Decision em [plan.md](plan.md).
- [X] T002 [P] Revisar as fontes a reusar e confirmar assinaturas: `gap_metrics_service.compute_dashboard`/`list_gaps`
  (`wtnapp/services/gap_metrics_service.py`), `GET /soa` + `SoaItem` (`wtnapp/routers/soa.py`),
  helpers de overview (`wtnapp/routers/context_overview.py`), `controlled_document_service.review_overdue`
  + baselines (`wtnapp/services/controlled_document_service.py`), `FormAssignment`
  (`wtnapp/models/form_assignment_model.py`).
- [X] T003 [P] Revisar fixtures de teste reutilizáveis (`client`, `org_headers`, seeds por org) em
  `wtnapp/test/conftest.py` e `wtnapp/test/test_soa.py` para os testes do dashboard.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: scaffolding compartilhado por TODAS as stories (permissão, DTOs, router/serviço base).

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

- [X] T004 Adicionar permissão `"view_dashboard"` à matriz `PERMISSIONS` para **todos os papéis
  exceto `guest_collaborator`** em `wtnapp/helpers/permissions.py` (ver D6/research).
- [X] T005 [P] Espelhar a permissão `view_dashboard` em `wtnadmin/src/app/core/permissions.ts`.
- [X] T006 [P] Criar DTOs e enums de resposta em `wtnapp/schemas/dashboard_schema.py`:
  `DashboardResponse`, `DashboardKpis`, `ModuleCard`, `NextAction`, `AdherencePoint`,
  `DashboardCardStatus`, `DashboardModuleId` (Pydantic v2; campos conforme [data-model.md](data-model.md)).
- [X] T007 Criar esqueleto do service `wtnapp/services/dashboard_service.py` com
  `build_dashboard(db, ctx) -> DashboardResponse` (retorno mínimo: org + KPIs zerados + `cards=[]`).
- [X] T008 Criar router `wtnapp/routers/dashboard.py` (`prefix="/dashboard"`, `GET ""` com
  `Depends(require_permission("view_dashboard"))` chamando `build_dashboard`) e **registrar em
  `wtnapp/main.py`** (`app.include_router(dashboard.router)`). **Sem** `AuditService` no sucesso (D7).

**Checkpoint**: `GET /dashboard` acessível, RBAC aplicado, retorna payload mínimo.

---

## Phase 3: User Story 1 — Visão consolidada do estado de conformidade (P1) 🎯 MVP

**Goal**: cada módulo (Contexto, Gap, SoA) aparece como card com status, progresso, responsável,
prazo, alerta de revisão vencida e atalho de próxima ação; KPIs no topo; placeholders para módulos
futuros. Frontend consome o endpoint único.

**Independent Test**: org com Contexto aprovado + Gap parcial + SoA rascunho ⇒ 3 cards corretos +
KPIs corretos, sem navegar para outros módulos; usuário de outra org recebe 404.

### Tests for User Story 1 (MANDATORY) ⚠️

> Escrever PRIMEIRO e garantir que FALHAM antes de implementar.

- [X] T009 [P] [US1] **Teste de isolamento de tenant** em
  `wtnapp/test/test_tenant_isolation_dashboard.py`: usuário da Org A com `X-Org-Context` da Org B ⇒
  **404 genérico**, nenhum dado de B no corpo, audit `CROSS_TENANT_DENIED` registrado; Consultor
  multi-org no contexto de A vê só dados de A.
- [X] T010 [P] [US1] Teste de happy path + **correção de agregação** em `wtnapp/test/test_dashboard.py`:
  3 cards com status/`progress_pct`; KPIs batendo com `compute_dashboard` chamado diretamente (SC-002).
  Assertar explicitamente: `critical_gaps` = nº de itens `priority == critical` (não `not_meet`) (C1);
  `controls_total` = nº de itens do assessment, e **93** quando não há assessment (C2).
- [X] T011 [P] [US1] Testes de casos de falha/edge em `wtnapp/test/test_dashboard.py`: módulo sem
  dados ⇒ `not_started` (sem progresso/responsável inventados); versão de Contexto vencida ⇒
  `needs_review` + `overdue`; sem `view_dashboard` ⇒ 403; sem `view_gap` ⇒ card de Gap omitido;
  erro ao montar um card ⇒ `status="error"` e demais cards ok (fail-open por card, D8).

### Implementation for User Story 1

- [X] T012 [US1] Implementar montagem do card **Contexto (Cl. 4)** em
  `wtnapp/services/dashboard_service.py` (status normalizado via `DocStatus`+`current_version_id`+
  `review_overdue`; progresso = artefatos aprovados / 3; responsável/prazo de atribuição se houver;
  `next_action` heurística — D4/D5).
- [X] T013 [US1] Implementar card **Gap Analysis** em `wtnapp/services/dashboard_service.py`
  (reusar `compute_dashboard`/`list_gaps`; `progress_pct`=completude; `review_overdue` da baseline
  corrente). KPIs: `overall_adherence`; `controls_evaluated`; **`controls_total`** = nº de itens do
  assessment, **senão 93** (C2); **`critical_gaps`** = nº de gaps com **`priority == critical`**
  (via `list_gaps`), **não** a contagem de `not_meet` (C1).
- [X] T014 [US1] Implementar card **SoA** em `wtnapp/services/dashboard_service.py`
  (% de itens com `implementation_status`; status do documento; `next_action`). `responsible`/
  `deadline` = item de **menor `deadline` futuro** (datetime → `date`) (C3); mesma regra para o
  prazo do card de Contexto/Gap.
- [X] T015 [US1] Finalizar `build_dashboard` em `wtnapp/services/dashboard_service.py`: KPIs
  agregados, **gating de card por permissão** (`has_permission(role, view_context/view_gap/view_soa)`),
  placeholders `action_plan`/`evidence`, e **fail-open por card** (try/except por módulo).
- [X] T016 [P] [US1] Frontend: refatorar `wtnadmin/src/app/pages/dashboard/dashboard.ts` para
  **uma** chamada `api.get<DashboardResponse>('/dashboard')` (tipar pelos DTOs; remover o `forkJoin`
  de 3 endpoints); renderizar KPIs + cards (status/progress/responsible/deadline/overdue) e navegar
  por `next_action.route` (+ `fragment` quando presente).
- [X] T017 [P] [US1] Frontend: atualizar `wtnadmin/src/app/pages/dashboard/dashboard.spec.ts` para
  mockar o endpoint único `/dashboard` e validar render de KPIs + nº de cards + estado "não iniciado".

**Checkpoint**: US1 funcional e testável; isolamento verificado; home consome o endpoint único.

---

## Phase 4: User Story 2 — Conformidade ao longo do tempo (P2)

**Goal**: indicador de evolução da aderência derivado das baselines aprovadas do Gap.

**Independent Test**: org com ≥ 2 baselines aprovadas ⇒ série cronológica; org sem baseline ⇒
indicador ausente (sem dado inventado).

### Tests for User Story 2 (MANDATORY) ⚠️

- [X] T018 [P] [US2] Teste de `adherence_trend` em `wtnapp/test/test_dashboard.py`: ≥ 2 baselines
  (`DocType.gap_baseline`) ⇒ lista com `{date, adherence, version}` em ordem; < 2 ⇒ `null`; nunca
  interpola.

### Implementation for User Story 2

- [X] T019 [US2] Implementar `adherence_trend` em `wtnapp/services/dashboard_service.py` lendo
  `DocumentVersion` (`document_type=gap_baseline`) → `content_snapshot["dashboard"]["overall_adherence"]`
  + `emitted_at`/`version_number`; retorna `null` se < 2 baselines (D9).
- [X] T020 [P] [US2] Frontend: renderizar o indicador de evolução em
  `wtnadmin/src/app/pages/dashboard/dashboard.ts` (série/sparkline), oculto quando `adherence_trend`
  é `null`.

**Checkpoint**: US1 e US2 funcionam independentemente.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T021 [P] Atualizar status da Feature 006 em `CLAUDE.md` (planejada → implementada, com contagem
  de testes) e nota em `docs/feature-dashboard-rastreabilidade.md`.
- [X] T022 **Audit review**: confirmar que o caminho de sucesso **não** gera audit log e que
  tentativas não autorizadas são logadas pelas dependencies centrais (`CROSS_TENANT_DENIED`/
  `PERMISSION_DENIED`) — sem PII/segredos.
- [X] T023 **Tenant isolation sweep**: revisar `wtnapp/services/dashboard_service.py` para garantir
  que toda query usa `ctx.tenant_id`/`scoped_query` (nenhum filtro ad-hoc).
- [X] T024 Rodar validação do [quickstart.md](quickstart.md): `pytest wtnapp/test/test_dashboard.py
  wtnapp/test/test_tenant_isolation_dashboard.py` + `cd wtnadmin && npm test` (todos verdes).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA** US1 e US2 (permissão + DTOs + router/serviço base).
- **US1 (Phase 3)**: depende da Foundational. É o MVP.
- **US2 (Phase 4)**: depende da Foundational; campo `adherence_trend` é **aditivo** ao contrato, então
  pode ser feito após US1 sem quebrá-la (independente).
- **Polish (Phase 5)**: depende das stories entregues.

### Within Each User Story

- Testes (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação.
- T012→T013→T014→T015 são **sequenciais** (mesmo arquivo `dashboard_service.py`).
- T016/T017 (frontend) dependem só do contrato (Foundational) ⇒ podem ir em **paralelo** ao backend.

### Parallel Opportunities

- **Foundational**: T005 (frontend perms) e T006 (schema) em paralelo; T004 separado.
- **US1 tests**: T009, T010, T011 em paralelo (mas T010/T011 no mesmo arquivo `test_dashboard.py` —
  coordenar se editados juntos).
- **US1**: frontend (T016/T017) em paralelo com os card builders backend (T012–T015).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1: Setup
2. Phase 2: Foundational (permissão + DTOs + router/serviço base)
3. Phase 3: US1 (testes → card builders → frontend)
4. **STOP e VALIDE**: `pytest` dos 2 arquivos + `npm test`; verificação E2E no browser (home).
5. Demo (MVP).

### Incremental Delivery

1. Setup + Foundational → endpoint mínimo no ar.
2. US1 → testa → demo (MVP) → US2 (série de aderência) → testa → demo.
3. Polish: docs + sweeps de auditoria/isolamento.

---

## Notes

- **Sem migration** — nenhuma mudança de schema (read-only). Não rodar Alembic.
- **Auditoria**: sucesso não loga; não autorizadas já logadas pelas dependencies centrais.
- Teste de isolamento de tenant (T009) é **obrigatório** (não é polish).
- A home atual (composição no frontend) tinha 2 bugs que o endpoint corrige: path `/gap-assessment/`
  (real `/gap/assessment/`) e rótulos `under_review`/`approved` (backend `in_review`/`in_force`).
- Commit após cada task ou grupo lógico.
