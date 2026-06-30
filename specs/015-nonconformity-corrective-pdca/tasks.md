---
description: "Task list — Feature 015: NC/Ações Corretivas + Análise Crítica + PDCA (5b)"
---

# Tasks: Não Conformidades & Ações Corretivas (10.2) + Análise Crítica (9.3) + Melhoria Contínua/PDCA (10.1)

**Input**: Design documents from `/specs/015-nonconformity-corrective-pdca/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md
**Depende da Feature 5a (014)** — promoção de constatações + repositório de evidências.

**Tests**: ⚠️ Obrigatórios (override da constitution) — isolamento de tenant + casos de falha por story.

**Organization**: por user story (US1–US7), cada uma testável de forma independente.

## Path Conventions
- Backend: `wtnapp/` (models, schemas, routers, services, helpers, test)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Adicionar enums e constantes em `wtnapp/settings.py`: `NCOrigin`, `NCSeverity`, `NCStatus`,
  `CorrectiveActionStatus`, `VerificationResult`, `ImprovementOrigin`, `ImprovementStatus`,
  `NC_CODE_PREFIX="NC-"`, `IMPROVEMENT_CODE_PREFIX="IMP-"`, `DocType.management_review`, e **estender**
  `SgsiArtifactType` com `nonconformity` e `corrective_action`.
- [X] T002 [P] Registrar 5 permissões em `wtnapp/helpers/permissions.py` (`view_nonconformity`,
  `manage_nonconformity`, `view_management_review`, `manage_management_review`,
  `approve_management_review`) nos papéis conforme a matriz do data-model.md.
- [X] T003 [P] Espelhar as 5 permissões em `wtnadmin/src/app/core/permissions.ts`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

- [X] T004 Criar `wtnapp/models/nonconformity_model.py` (4 tabelas: `nonconformity`,
  `corrective_action`, `nonconformity_verification`, `nonconformity_event`), todas `tenant_id`; trigger
  append-only em `nonconformity_event`.
- [X] T005 [P] Criar `wtnapp/models/management_review_model.py` (`management_review`, coleção;
  `current_version_id`+`draft_status` no padrão Documento Controlado).
- [X] T006 [P] Criar `wtnapp/models/improvement_model.py` (`improvement`, `improvement_event`); trigger
  append-only em `improvement_event`.
- [X] T007 Registrar os 3 modelos em `wtnapp/models/__init__.py` e os routers stub `nonconformity`,
  `management_review`, `improvement` em `wtnapp/main.py`.
- [X] T008 Estender `wtnapp/services/evidence_service.py` (`_TARGET_MODELS`/`target_exists`) para
  resolver `nonconformity`→`NonConformity` e `corrective_action`→`CorrectiveAction` (o `/evidence` da
  5a passa a aceitar esses alvos sem mudança no router).
- [X] T009 Criar migration `wtnapp/alembic/versions/<rev>_nonconformity_pdca_module.py`
  (`down_revision="b8c9d0e1f016"`), idempotente: 7 tabelas + RLS + triggers append-only. **Não** altera
  tabelas da 5a.
- [X] T010 [P] Teste de migração em `wtnapp/test/test_nc_migration.py` (tabelas/colunas/índices +
  triggers append-only; head único).

**Checkpoint**: schema + permissões + extensão de evidências prontos.

---

## Phase 3: User Story 1 — Registrar e Tratar uma NC (Priority: P1) 🎯 MVP

**Goal**: Registrar NC (manual e **promovida** da 5a) com origem/severidade/vínculo/causa raiz/status.

**Independent Test**: registrar NC manual + promover constatação NC da 5a; ambas com origem/severidade/
causa raiz/status; constatação promovida referencia a NC; promoção idempotente.

### Tests for User Story 1 (MANDATORY) ⚠️
- [X] T011 [P] [US1] Tenant isolation em `wtnapp/test/test_tenant_isolation_nonconformity.py`
  (NC/promoção da Org B inacessíveis).
- [X] T012 [P] [US1] Promoção em `wtnapp/test/test_nc_promotion.py`: cria NC semeando severidade
  (`nc_maior→maior`/`nc_menor→menor`), preenche `nonconformity_ref`, idempotente, e recusa constatação
  não promovível (422).
- [X] T013 [P] [US1] CRUD/causa raiz/status em `wtnapp/test/test_nonconformity.py`.

### Implementation for User Story 1
- [X] T014 [P] [US1] `wtnapp/schemas/nonconformity_schema.py`: `NCRequest/Summary/Detail` (com
  `readiness`), `PromoteRequest`, `NCTransitionRequest`.
- [X] T015 [US1] `wtnapp/services/nonconformity_service.py`: criar/editar NC (código `NC-####`),
  máquina de estados `start`/`send-verify`/`cancel` (**o `close` chega na US2 já com o gate** — US1 não
  expõe `close` sem verificação, evitando contradizer FR-007), **promoção** idempotente (lê
  `InternalAuditFinding`, escreve `nonconformity_ref`), trilha `nonconformity_event`.
- [X] T016 [US1] `wtnapp/routers/nonconformity.py`: `GET/POST /nonconformities`, `GET/PUT
  /nonconformities/{id}`, `POST /nonconformities/promote`, `POST /nonconformities/{id}/transition` —
  com RBAC/scoped_query/audit + 404 genérico; registrar em `main.py`.
- [X] T017 [P] [US1] `wtnadmin/src/app/pages/nonconformities/` (lista+criar) e base de
  `pages/nonconformity-detail/` (dados/causa raiz/status/promover); rotas com
  `permissionGuard('view_nonconformity')`, grupo de nav.
- [X] T018 [P] [US1] `pages/nonconformities/nonconformities.spec.ts` (criar/promover/listar).

**Checkpoint**: US1 funcional — MVP (registro + promoção).

---

## Phase 4: User Story 2 — Ação Corretiva + Verificação de Eficácia (Priority: P1)

**Goal**: Ações corretivas (resp.+prazo) + verificação de eficácia + **gate de encerramento**.

**Independent Test**: criar ações, registrar verificação eficaz, encerrar; encerramento bloqueado sem
verificação eficaz; prazo vencido sinalizado.

### Tests for User Story 2 (MANDATORY) ⚠️
- [X] T019 [P] [US2] Gate de encerramento + verificação em `wtnapp/test/test_nc_verification_gate.py`
  (encerrar sem verificação eficaz ⇒ 409; com eficaz ⇒ ok).
- [X] T020 [P] [US2] Ações + prazo vencido em `wtnapp/test/test_corrective_action.py`.

### Implementation for User Story 2
- [X] T021 [US2] `nonconformity_service`: CRUD de ação corretiva (valida `responsible_member_id` membro
  ativo), `pending_actions`/`overdue`, verificação de eficácia, e **transição `close` com gate**
  (status=in_verification + verificação mais recente `effective` + **zero ações em estado não terminal**
  — sem campo `obrigatória`).
- [X] T022 [US2] `wtnapp/schemas/nonconformity_schema.py` + `wtnapp/routers/nonconformity.py`:
  `GET/POST /{id}/actions`, `PUT/DELETE /actions/{id}`, `GET/POST /{id}/verifications`; `readiness`
  no detalhe (`can_close`/`overdue_actions`/`has_effective_verification`).
- [X] T023 [P] [US2] `pages/nonconformity-detail/`: seção de ações (resp.+prazo+status, prazo vencido) e
  verificação de eficácia + ação de encerrar (gated).
- [X] T024 [P] [US2] `pages/nonconformity-detail/nonconformity-detail.spec.ts` (ações/verificação/gate).

**Checkpoint**: 10.2 completa (NC + ação verificável).

---

## Phase 5: User Story 3 — Lista, Filtros e Indicadores (Priority: P2)

**Goal**: Lista filtrável (status/severidade/responsável/prazo vencido) + indicadores.

**Independent Test**: aplicar filtros e confirmar resultado escopado ao tenant; "prazo vencido" só
retorna itens vencidos não concluídos.

### Tests for User Story 3 (MANDATORY) ⚠️
- [X] T025 [P] [US3] Filtros + isolation em `wtnapp/test/test_nonconformity.py` (extensão).

### Implementation for User Story 3
- [X] T026 [US3] `nonconformity_service`/`routers/nonconformity.py`: `GET /nonconformities` com filtros
  (status/severity/responsible/overdue) e indicadores simples.
- [X] T027 [P] [US3] `pages/nonconformities/`: barra de filtros + chips de indicadores; `.spec.ts`.

**Checkpoint**: operação das NCs com busca/filtros.

---

## Phase 6: User Story 4 — Evidências em NCs/Ações (Priority: P2)

**Goal**: Anexar evidências a NCs e ações pelo repositório transversal da 5a (alvos novos).

**Independent Test**: anexar evidência a uma NC e a uma ação; aparecem vinculadas, com metadados/
integridade da 5a; isolamento de tenant no alvo.

### Tests for User Story 4 (MANDATORY) ⚠️
- [X] T028 [P] [US4] Evidência em NC/ação em `wtnapp/test/test_nc_evidence.py` (upload via `/evidence`
  com `target_type=nonconformity`/`corrective_action`; alvo cross-tenant ⇒ 404).

### Implementation for User Story 4
- [X] T029 [US4] (Backend já coberto por T008 — extensão do resolver.) Confirmar que `/evidence`
  resolve os novos alvos; nenhum endpoint novo.
- [X] T030 [P] [US4] `pages/nonconformity-detail/`: embutir `shared/evidence-panel` para a NC
  (`target_type=nonconformity`) e para cada ação corretiva (`target_type=corrective_action`).

**Checkpoint**: comprovação documental das NCs/ações via 5a.

---

## Phase 7: User Story 5 — Análise Crítica como Documento Controlado (Priority: P3)

**Goal**: Análise crítica (coleção, uma por reunião) com entradas/saídas, aprovação/PDF/assinatura.

**Independent Test**: criar análise crítica, submeter, aprovar (com/sem assinatura), exportar PDF;
aprovação bloqueada se incompleta; versão imutável; coleção lista várias atas.

### Tests for User Story 5 (MANDATORY) ⚠️
- [X] T031 [P] [US5] Ciclo/gate/versão/PDF em `wtnapp/test/test_management_review.py`; **incluir
  asserção (FR-019)**: criar duas atas com datas distintas lista ambas (coleção).
- [X] T032 [P] [US5] Isolation em `wtnapp/test/test_tenant_isolation_management_review.py`.

### Implementation for User Story 5
- [X] T033 [P] [US5] `wtnapp/schemas/management_review_schema.py`: `ReviewRequest/Summary/Detail`,
  `ReviewApproveRequest`, `ReviewVersionSummary`.
- [X] T034 [US5] `wtnapp/services/management_review_service.py`: CRUD (coleção), `snapshot_factory`
  (entradas/saídas), reuso `controlled_document_service` (submit-review/approve) + `signature_service`,
  **gate** de completude; `wtnapp/services/management_review_export_service.py` (PDF reportlab).
- [X] T035 [US5] `wtnapp/routers/management_review.py`: CRUD + `submit-review`/`approve`/`versions`/
  `versions/{id}/export`; registrar em `main.py`.
- [X] T036 [P] [US5] `pages/management-reviews/` (lista/criar) + `pages/management-review-detail/`
  (entradas/saídas + submeter/aprovar/assinar/exportar/versões); rotas + nav.
- [X] T037 [P] [US5] `management-reviews.spec.ts` + `management-review-detail.spec.ts`.

**Checkpoint**: 9.3 completa.

---

## Phase 8: User Story 6 — Melhorias + Visão de Ciclo PDCA (Priority: P4)

**Goal**: Melhorias (origem/status + realimentação read-only) e visão de ciclo PDCA fechando o loop.

**Independent Test**: registrar melhorias por origem; abrir visão PDCA (loop read-only); isolamento.

### Tests for User Story 6 (MANDATORY) ⚠️
- [X] T038 [P] [US6] Melhorias + visão PDCA + isolation em `wtnapp/test/test_improvement_pdca.py`.

### Implementation for User Story 6
- [X] T039 [P] [US6] `wtnapp/schemas/improvement_schema.py`: `ImprovementRequest/Summary`, `PdcaEntry`.
- [X] T040 [US6] `wtnapp/services/improvement_service.py` (CRUD + status; código `IMP-####`) e
  `wtnapp/services/pdca_service.py` (visão de ciclo read-only reusando `traceability_service`, sem
  write-back; **RBAC composto**: `view_nonconformity` + constatações só com `view_internal_audit` e
  atas só com `view_management_review`, senão omitidas).
- [X] T041 [US6] `wtnapp/routers/improvement.py`: `GET/POST /improvements`, `PUT /improvements/{id}`,
  `GET /improvements/pdca`; registrar em `main.py`.
- [X] T042 [P] [US6] `pages/improvements/` (lista/criar + visão de ciclo PDCA); rota + nav; `.spec.ts`.

**Checkpoint**: 10.1 + fechamento do loop PDCA.

---

## Phase 9: User Story 7 — Dashboard do Módulo + Readiness (Priority: P5)

**Goal**: Dashboard (NCs por status/severidade, ações vencidas, melhorias por status) + readiness na
esteira.

**Independent Test**: contagens corretas escopadas ao tenant; card de fechamento do PDCA no Dashboard
de Conformidade.

### Tests for User Story 7 (MANDATORY) ⚠️
- [X] T043 [P] [US7] Contagens + isolation em `wtnapp/test/test_nc_metrics.py`.
- [X] T044 [P] [US7] Card de readiness em `wtnapp/test/test_dashboard.py` (extensão — substitui o
  placeholder `action_plan`).

### Implementation for User Story 7
- [X] T045 [US7] `wtnapp/services/nc_metrics_service.py` + `GET /nonconformities/dashboard` no router.
- [X] T046 [US7] Estender `wtnapp/services/dashboard_service.py` + `schemas/dashboard_schema.py`:
  **reusar o id `DashboardModuleId.action_plan`** (já reservado pela 5a) como card real **Act/PDCA**
  (substitui o placeholder), gating por `view_nonconformity`, fail-open.
- [X] T047 [P] [US7] `pages/nonconformity-dashboard/` (cards) + card na home; `.spec.ts`.

**Checkpoint**: visão executiva + PDCA fechado na esteira.

---

## Phase 10: Polish & Cross-Cutting Concerns

- [X] T048 [P] **Audit review**: confirmar audit log em CRUD/transições de NC, promoção, ações,
  verificação, encerramento, Ata (submeter/aprovar/assinar/exportar) e melhorias, sem PII/segredos.
- [X] T049 [P] **Tenant isolation sweep**: revisar que toda query nova usa `scoped_query`/filtro de
  tenant; promoção/PDCA/dashboard fail-closed; a única escrita na 5a é `nonconformity_ref`.
- [X] T050 [P] Atualizar a seção do módulo no `CLAUDE.md` (Feature 015 implementada).
- [X] T051 Rodar suíte backend completa (`pytest wtnapp/test`) e frontend (`npm test` em `wtnadmin/`).
- [ ] T052 Validar `quickstart.md` no browser + `alembic upgrade head` no Postgres real.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (P1)** → **Foundational (P2)** bloqueia todas as stories.
- **US1 (P3)** é o MVP; **US2 (P4)** estende NC com ação/verificação/gate; **US3 (P5)** e **US4 (P6)**
  dependem de US1 (lista/evidências).
- **US5 (P7)** (análise crítica) é independente de US1–US4 (domínio próprio) — pode ir em paralelo após
  a Foundational.
- **US6 (P8)** depende de US1/US5 para ter conteúdo no PDCA; **US7 (P9)** depende das demais p/ dados.
- **Polish (P10)** por último.

### Within Each User Story
- Testes (incl. isolamento) escritos e falhando antes da implementação.
- Models → services → endpoints → UI.

### Parallel Opportunities
- Setup: T002/T003 [P]. Foundational: T005/T006/T010 [P].
- Dentro de cada story, tasks [P] (schemas/UI/tests em arquivos distintos) rodam em paralelo.
- Após a Foundational, o domínio de **NC** (US1–US4) e o de **análise crítica** (US5) podem ser tocados
  por devs diferentes; convergem em US6 (PDCA) e US7 (dashboard).

---

## Implementation Strategy

### MVP First
1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1: registrar + promover NC).
2. **STOP e VALIDE**: promoção idempotente + NC com causa raiz/status.

### Incremental Delivery
- US1 (NC+promoção) → US2 (ação+verificação+gate) = 10.2 completa.
- US3 (lista) + US4 (evidências) = operação da fase 1.
- US5 (análise crítica 9.3) → US6 (melhorias+PDCA 10.1) → US7 (dashboard) = fechamento do PDCA.

---

## Notes
- [P] = arquivos diferentes, sem dependências.
- Teste de isolamento de tenant é obrigatório por feature de domínio.
- **Única escrita num módulo consumido**: `internal_audit_finding.nonconformity_ref` na promoção.
- Evidências reusam o repositório da 5a (sem novo esquema); análise crítica reusa Documento Controlado.
- Sem novas dependências.
