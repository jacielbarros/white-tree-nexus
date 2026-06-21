---
description: "Task list para a feature 004 — Gap Analysis ISO/IEC 27001:2022"
---

# Tasks: Gap Analysis ISO/IEC 27001:2022

**Input**: Design documents de `/specs/004-gap-analysis/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml),
[quickstart.md](quickstart.md). **Roda sobre as features 001 (fundação), 002 (Documento Controlado) e
003 (Motor de Workflow)** — reusa `tenant_scope`+RLS, RBAC, auditoria, `controlled_document_service`,
`form_workflow_service`/`signature_service`/`notification_service` e `form_assignment_event`.

**Tests**: ⚠️ **OVERRIDE da constitution:** testes NÃO são opcionais — toda story inclui **teste de
isolamento de tenant** + casos de falha principais (Princípio VI).

**Organization**: por user story (US1–US5). Backend `wtnapp/`, frontend `wtnadmin/src/app/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependências pendentes)
- **[Story]**: US1–US5. Setup/Foundational/Polish sem label.

---

## Phase 1: Setup

- [X] T001 Estender `wtnapp/settings.py` com os enums: `GapStatus` (not_filled/meets/partial/
  not_meet/not_applicable), `GapPriority` (critical/high/medium/low), `GapDimension` (clause/annex_a),
  `GapTheme` (organizational/people/physical/technological), `GapAssignmentScope` (whole/theme), e
  estender `DocType` com `gap_baseline`.
- [X] T002 [P] Estender `wtnapp/helpers/permissions.py`: adicionar `view_gap`, `manage_gap`,
  `approve_gap_baseline` à matriz papel→permissão (org_admin: todas; consultant: view+manage;
  gestor/auditor/cliente: view). Condução reusa `assign_form`/`fill_form`/`sign_form` do 003.
- [X] T003 [P] Criar `wtnapp/data/iso27001_seed.py` com o seed das Cláusulas 4–10 e os 93 controles do
  Anexo A (A.5=37, A.6=8, A.7=14, A.8=34), `seed_version="2022.1"`, derivado de `material_de_contexto/`.
- [X] T004 [P] Estender `wtnapp/test/conftest.py` com fixtures do módulo (seed carregado em memória,
  org + usuários org_admin/consultant/client e helper de header `X-Org-Context`, reusando os da 002/003).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: catálogo (seed + cópia por org), avaliação e métricas de que US1–US5 dependem.
**⚠️ Nenhuma user story começa antes desta fase.**

- [X] T005 [P] Models `GapSeedVersion` + `GapSeedItem` em `wtnapp/models/gap_seed_model.py`
  (**compartilhados, sem `tenant_id`, somente leitura**; índice único `(seed_version_id, ref_code)`).
- [X] T006 [P] Model `GapCatalogItem` em `wtnapp/models/gap_catalog_model.py` (cópia editável por org;
  `tenant_id`+RLS; `seed_item_id` nullable; `is_custom`/`is_discontinued`; único `(tenant_id, ref_code)`).
- [X] T007 [P] Models `GapAssessment` + `GapAssessmentItem` + `GapAssessmentItemEvent` em
  `wtnapp/models/gap_assessment_model.py` (`tenant_id`+RLS; `GapAssessment` único por org;
  `GapAssessmentItemEvent` **append-only**; regra `not_applicable` ⇒ `exclusion_justification`).
- [X] T008 `gap_seed_service` em `wtnapp/services/gap_seed_service.py`: carregar seed; **adotar versão**
  (materializa/atualiza `GapCatalogItem` de forma **aditiva e idempotente** — novos como not_filled,
  preserva personalizações/avaliações, marca removidos como `is_discontinued`).
- [X] T009 `gap_metrics_service` em `wtnapp/services/gap_metrics_service.py`: aderência ponderada
  (1.0/0.5/0.0, exclui N/A e not_filled; denominador zero ⇒ `None`) por geral/dimensão/cláusula/tema;
  distribuição por status; completude; lista de lacunas.
- [X] T010 Migration `wtnapp/alembic/versions/e7f8a9b0c106_gap_analysis_module.py`: cria todas as tabelas +
  **RLS** nas por-org + **gatilho append-only** em `gap_assessment_item_event` + carga idempotente do
  seed em `gap_seed_*`. `alembic check` sem drift.
- [X] T011 `wtnapp/main.py`: registrar os routers `gap_catalog`, `gap_assessment`, `gap_assignment`.

**Checkpoint**: catálogo + avaliação + métricas prontos — user stories podem começar.

---

## Phase 3: User Story 1 — Avaliar a aderência (matriz) (Priority: P1) 🎯 MVP

**Goal**: adotar o catálogo e avaliar cada item das duas dimensões (status + campos), com N/A exigindo
justificativa e histórico append-only.

**Independent Test**: adotar seed → matriz com itens not_filled → atualizar item persiste; N/A sem
justificativa ⇒ 422; item de outra org nunca aparece.

### Tests (MANDATORY) ⚠️

- [X] T012 [P] [US1] **Teste de isolamento de tenant** em `wtnapp/test/test_tenant_isolation_gap.py`:
  catálogo/avaliação/item de A inacessíveis a B (404 + audit); seed compartilhado é só-leitura.
- [X] T013 [P] [US1] Testes em `wtnapp/test/test_gap_assessment.py`: adotar seed materializa catálogo;
  `GET /gap/assessment` traz itens not_filled; `PUT .../items/{id}` persiste e gera evento; **N/A sem
  justificativa ⇒ 422**.

### Implementation

- [X] T014 [US1] Schemas em `wtnapp/schemas/gap_catalog_schema.py` e `wtnapp/schemas/gap_assessment_schema.py`
  (response com `id: UUID`; `ConfigDict(from_attributes=True)`).
- [X] T015 [US1] Router `wtnapp/routers/gap_catalog.py` (`GET /gap/catalog`, `POST /gap/catalog/adopt`)
  com `scoped_query` + `require_permission` + audit; registrar em `main.py`.
- [X] T016 [US1] Router `wtnapp/routers/gap_assessment.py` (`GET /gap/assessment`, `PUT
  /gap/assessment/items/{id}`) com `tenant_scope` + `require_permission(manage_gap)` + validação de N/A
  + gravação de `GapAssessmentItemEvent` + audit.
- [X] T017 [P] [US1] Frontend `wtnadmin/src/app/pages/gap-analysis/` (matriz: itens agrupados por
  dimensão/tema/cláusula, editar status + campos, salvar) — Signals, OnPush, Reactive/FormsModule.

**Checkpoint**: US1 funcional e isolamento verificado — MVP do módulo.

---

## Phase 4: User Story 2 — Indicadores e lacunas (Priority: P2)

**Goal**: dashboard de aderência (geral/dimensão/cláusula/tema) + lista priorizada de lacunas.

**Independent Test**: com itens avaliados, % de aderência consistente entre recortes (só aplicáveis);
lacunas trazem só aplicáveis não conformes, ordenáveis por prioridade.

### Tests (MANDATORY) ⚠️

- [X] T018 [P] [US2] Testes em `wtnapp/test/test_gap_metrics.py`: pesos 1.0/0.5/0.0; N/A e not_filled
  fora do denominador; denominador zero ⇒ null; consistência geral×dimensão×cláusula×tema; lacunas
  (filtro + ordenação por prioridade).

### Implementation

- [X] T019 [US2] Endpoints `GET /gap/assessment/dashboard` e `GET /gap/assessment/gaps` no
  `gap_assessment.py` (usando `gap_metrics_service`) + `view_gap` + audit de leitura sensível se aplicável.
- [X] T020 [P] [US2] Frontend `wtnadmin/src/app/pages/gap-dashboard/` (indicadores + distribuição +
  lista de lacunas com ordenação por prioridade).

**Checkpoint**: US1–US2 = retrato de conformidade acionável.

---

## Phase 5: User Story 3 — Catálogo editável por organização (Priority: P3)

**Goal**: personalizar/adicionar itens próprios e adotar nova versão do seed de forma aditiva.

**Independent Test**: item próprio aparece só na Org A; renomear não afeta Org B/seed; adotar versão
nova preserva avaliações e marca removidos como descontinuados.

### Tests (MANDATORY) ⚠️

- [X] T021 [P] [US3] Testes em `wtnapp/test/test_gap_catalog.py`: adicionar item próprio (isolado por
  org); `PATCH` renomeia; **adoção aditiva** preserva avaliações/personalizações e marca
  `is_discontinued`; isolamento de tenant.

### Implementation

- [X] T022 [US3] Endpoints `POST /gap/catalog/items` e `PATCH /gap/catalog/items/{id}` no `gap_catalog.py`
  (`manage_gap`) + lógica de adoção versionada aditiva no `gap_seed_service` + audit.
- [X] T023 [P] [US3] Frontend `wtnadmin/src/app/pages/gap-catalog/` (personalizar catálogo + adotar
  versão do seed).

**Checkpoint**: US1–US3 independentes.

---

## Phase 6: User Story 4 — Baseline versionada e rastreabilidade (Priority: P4)

**Goal**: congelar baseline imutável (aprovação do Admin) reusando Documento Controlado; comparar
baselines; expor chave de rastreabilidade p/ SoA.

**Independent Test**: enviar→aprovar cria versão imutável; aprovar sem revisão ⇒ 409; como Consultor
⇒ 403; comparar duas baselines mostra variação; baseline antiga imutável (gatilho).

### Tests (MANDATORY) ⚠️

- [X] T024 [P] [US4] Testes em `wtnapp/test/test_gap_baseline.py`: `submit-review`→`approve` cria
  `DocumentVersion` (`DocType.gap_baseline`) imutável; aprovar sem revisão ⇒ 409; como Consultor ⇒ 403;
  `compare` retorna variação; UPDATE/DELETE da versão bloqueado (append-only).

### Implementation

- [X] T025 [US4] Endpoints `POST /gap/assessment/submit-review`, `POST /gap/assessment/approve`,
  `GET /gap/assessment/baselines`, `GET /gap/assessment/baselines/compare` no `gap_assessment.py`,
  reusando `controlled_document_service.approve_document` com `snapshot_factory` (matriz + aderência);
  `approve_gap_baseline`; expõe `soa_ref` de rastreabilidade; audit.
- [X] T026 [P] [US4] Frontend `wtnadmin/src/app/pages/gap-baselines/` (congelar/aprovar/listar/comparar).

**Checkpoint**: US1–US4 = núcleo completo (avaliar + medir + personalizar + baseline).

---

## Phase 7: User Story 5 — Condução atribuível e assinável (Priority: P5)

**Goal**: atribuir a condução (inteira ou por tema) a membro/externo e assinar para congelar baseline,
reusando o Motor 003.

**Independent Test**: atribuir a membro e a e-mail externo; assumir/preencher/enviar; assinar congela
baseline com selo verificável; OTP do externo; isolamento.

### Tests (MANDATORY) ⚠️

- [X] T027 [P] [US5] Testes em `wtnapp/test/test_gap_assignment.py`: criar atribuição (whole/theme;
  membro/externo), claim/submit, assinar congela baseline, token externo + OTP, isolamento de tenant.

### Implementation

- [X] T028 [US5] Model `GapAssignment` em `wtnapp/models/gap_assignment_model.py` (+migration+RLS;
  CHECK exatamente-um respondente) reusando `form_assignment_event` (trilha) e `FormSignature`.
- [X] T029 [US5] `gap_assignment` service + router `wtnapp/routers/gap_assignment.py`
  (`POST/GET /gap/assignments`, `claim`/`submit`/`return`/`cancel`/`sign` + rota pública por token)
  reusando `form_workflow`/`signature_service`/`notification_service`; assinatura congela baseline;
  registrar em `main.py`.
- [X] T030 [P] [US5] Frontend: UI de atribuição/acompanhamento da condução (reusa padrões do 003 —
  wizard/linha do tempo, assinar, devolver/cancelar) integrada à `pages/gap-analysis/`.

**Checkpoint**: motor completo (US1–US5).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T031 [P] **Tenant isolation sweep**: confirmar que toda query por-org passa por `tenant_scope` e
  que RLS está habilitada em todas as novas tabelas por-org (seed compartilhado é só-leitura).
- [X] T032 [P] **Audit review**: criar/editar item, marcar N/A, adotar seed, atribuir/assinar,
  congelar/aprovar baseline geram log sem PII/conteúdo sensível.
- [X] T033 [P] `alembic check` (sem drift) + upgrade/downgrade da migration; carga do seed idempotente
  (rodar duas vezes não duplica).
- [ ] T034 Validar `quickstart.md` end-to-end (cenários A–F: avaliar, dashboard, catálogo, baseline,
  condução, isolamento).
- [X] T035 [P] Atualizar docs: seção do módulo em `CLAUDE.md` (implementado) + nota em `docs/README.md`.
- [X] T036 [P] Testes unitários de frontend (matriz/dashboard/catálogo/baseline) em
  `wtnadmin/src/app/pages/gap-*/**/*.spec.ts`.
- [X] T037 [P] Teste de completude do seed: 7 cláusulas (4–10) + 93 controles do Anexo A
  (A.5=37, A.6=8, A.7=14, A.8=34) em `wtnapp/test/test_gap_catalog.py` (estende).

---

## Dependências entre fases

- **Setup (P1)** → **Foundational (P2)** → user stories.
- **US1 (P1)** é o MVP; **US2–US5** dependem do motor (P2). US2 depende de US1 (itens avaliados); US4
  (baseline) depende de US1; US5 (condução) depende de US1 e reusa o 003.
- **Polish (P8)** por último.

## Exemplos de paralelização

- Foundational: T005, T006, T007 em paralelo (arquivos diferentes); T008/T009 dependem dos models.
- US1: T012 e T013 (testes) em paralelo; T017 (frontend) em paralelo com T015/T016 após contratos.
- US2/US3/US4: testes (T018/T021/T024) e frontends (T020/T023/T026) paralelizáveis dentro de cada story.

## Estratégia de implementação

1. **MVP = US1** (adotar catálogo + avaliar a matriz) sobre o Foundational (P2) — já entrega o retrato
   de conformidade.
2. Incrementos: US2 (dashboard/lacunas) → US3 (catálogo editável) → US4 (baseline) → US5 (condução).
3. Test-first em cada story (isolamento de tenant obrigatório); migrations + RLS + gatilhos append-only
   acompanham cada modelo novo; seed idempotente.
