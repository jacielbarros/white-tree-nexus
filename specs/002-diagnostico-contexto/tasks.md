---
description: "Task list for feature 002 â€” DiagnÃ³stico e Contexto da OrganizaÃ§Ã£o (ClÃ¡usula 4)"
---

# Tasks: DiagnÃ³stico e Contexto da OrganizaÃ§Ã£o (ISO/IEC 27001 â€” ClÃ¡usula 4)

**Input**: Design documents from `/specs/002-diagnostico-contexto/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml). **Roda sobre a
fundaÃ§Ã£o 001 jÃ¡ implementada** (auth, `tenant_scope`, RBAC, auditoria, RLS, `controlled-document`
ainda nÃ£o â€” Ã© criado aqui).

**Tests**: âš ï¸ **OVERRIDE da constitution:** testes NÃƒO sÃ£o opcionais â€” toda story inclui **teste de
isolamento de tenant** + casos de falha principais (PrincÃ­pio VI).

**Organization**: por user story (US1â€“US5). Backend `wtnapp/`, frontend `wtnadmin/src/app/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizÃ¡vel (arquivos diferentes, sem dependÃªncias pendentes)
- **[Story]**: US1â€“US5. Setup/Foundational/Polish sem label.

---

## Phase 1: Setup

- [X] T001 Estender `wtnapp/helpers/permissions.py`: adicionar `view_context`, `manage_context` e
  `approve_context_document` Ã  matriz papelâ†’permissÃ£o (super_admin/org_admin: todas;
  consultant/manager/process_owner: view+manage; demais: view), conforme data-model.md.
- [X] T002 [P] Estender `wtnapp/test/conftest.py` com fixtures do mÃ³dulo: seed de organizaÃ§Ã£o +
  usuÃ¡rios com papÃ©is `org_admin`, `consultant`, `client`, e helper para `X-Org-Context`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: nÃºcleo de "documento controlado" e config de classificaÃ§Ã£o que US1â€“US5 dependem.
**âš ï¸ Nenhuma user story comeÃ§a antes desta fase.**

- [X] T003 Model `DocumentVersion` em `wtnapp/models/document_version_model.py` + migration Alembic
  + RLS + **gatilho append-only** (bloqueia UPDATE/DELETE, anÃ¡logo a `audit_logs`).
- [X] T004 `controlled_document_service` em `wtnapp/services/controlled_document_service.py`: ciclo
  de vida (submit-review, approveâ†’**snapshot JSON imutÃ¡vel**, list versions), invariante **â‰¤1
  `in_force`** por artefato (aprovar nova obsoleta a anterior), numeraÃ§Ã£o de versÃ£o e identificador.
- [X] T005 [P] Model `ClassificationAccessPolicy` (+migration+RLS) em
  `wtnapp/models/classification_policy_model.py` e helper `wtnapp/helpers/classification_access.py`
  (default: RBAC-apenas; quando hÃ¡ polÃ­tica, restringe leitura por nÃ­vel).
- [X] T005a Router da polÃ­tica de classificaÃ§Ã£o em `wtnapp/routers/context_overview.py` (ou mÃ³dulo
  prÃ³prio): `GET`/`PUT /context/classification-policy` (`approve_context_document` para definir);
  define o shape de `rules` (nÃ­vel â†’ papÃ©is). Registrar em `main.py`; audit. (FR-011a)
- [X] T006 [P] `wtnapp/main.py`: pontos de registro dos novos routers (context/diagnostic/
  stakeholders/scope/overview) e wiring do helper de classificaÃ§Ã£o na dependency de leitura.

**Checkpoint**: documento controlado + classificaÃ§Ã£o prontos â€” user stories podem comeÃ§ar.

---

## Phase 3: User Story 1 â€” AnÃ¡lise de Contexto (4.1) + DiagnÃ³stico (Priority: P1) ðŸŽ¯ MVP

**Goal**: diagnÃ³stico incremental + registro de questÃµes internas/externas (PESTEL/SWOT + impacto)
na AnÃ¡lise de Contexto.

**Independent Test**: salvar/retomar diagnÃ³stico; registrar questÃµes classificadas; ver a anÃ¡lise;
A nÃ£o acessa dados de contexto de B.

### Tests (MANDATORY) âš ï¸

- [X] T007 [P] [US1] **Teste de isolamento de tenant**: diagnÃ³stico e anÃ¡lise de contexto de A
  inacessÃ­veis a B (404 + audit) em `wtnapp/test/test_tenant_isolation.py` (estende).
- [X] T008 [P] [US1] Testes do diagnÃ³stico (salvar rascunho parcial e retomar sem perda) em
  `wtnapp/test/test_diagnostic.py`.
- [X] T009 [P] [US1] Testes da AnÃ¡lise de Contexto (questÃµes CRUD; PESTEL/SWOT; impacto
  Alto/MÃ©dio/Baixo) em `wtnapp/test/test_context_analysis.py`.
- [X] T009a [P] [US1] Teste da **polÃ­tica de acesso por classificaÃ§Ã£o** (FR-011a): **sem** polÃ­tica
  â‡’ acesso sÃ³ por RBAC; **com** polÃ­tica configurada, papel sem o nÃ­vel exigido Ã© negado/filtrado na
  leitura do artefato â€” em `wtnapp/test/test_classification_access.py`.

### Implementation

- [X] T010 [P] [US1] Model `Diagnostic` (+migration+RLS) em `wtnapp/models/diagnostic_model.py`
  (Ãºnico por `tenant_id`; seÃ§Ãµes JSONB).
- [X] T011 [P] [US1] Models `ContextAnalysis` + `ContextIssue` (+migration+RLS) em
  `wtnapp/models/context_analysis_model.py` e `context_issue_model.py`.
- [X] T012 [P] [US1] Schemas em `wtnapp/schemas/diagnostic_schema.py` e
  `wtnapp/schemas/context_schema.py`.
- [X] T013 [US1] Router `wtnapp/routers/diagnostic.py` (`GET`/`PUT /context/diagnostic`,
  `manage_context` p/ editar) + registrar em `main.py`; audit.
- [X] T014 [US1] Router `wtnapp/routers/context_analysis.py` (`GET`/`PUT /context/analysis`,
  `POST`/`PATCH`/`DELETE /context/analysis/issues`) escopado por tenant + `require_permission` +
  audit; registrar em `main.py`.
- [X] T015 [P] [US1] Frontend `wtnadmin/src/app/pages/diagnostic/` e `pages/context-analysis/`
  (Reactive Forms, Signals, OnPush; rascunho/retomar; questÃµes PESTEL/SWOT + impacto).

**Checkpoint**: US1 funcional e isolamento verificado â€” MVP do mÃ³dulo.

---

## Phase 4: User Story 2 â€” Mapa de Partes Interessadas (4.2) (Priority: P2)

**Goal**: cadastrar partes + requisitos tipados; derivar estratÃ©gia de PoderÃ—Interesse (Mendelow).

**Independent Test**: cadastrar parte com requisito; verificar derivaÃ§Ã£o da estratÃ©gia nas
combinaÃ§Ãµes; isolamento.

### Tests (MANDATORY) âš ï¸

- [X] T016 [P] [US2] Teste de derivaÃ§Ã£o PoderÃ—Interesse â†’ estratÃ©gia (manage_closely/keep_satisfied/
  keep_informed/monitor) em todas as combinaÃ§Ãµes, em `wtnapp/test/test_stakeholders.py`.
- [X] T017 [P] [US2] Testes de partes + requisitos (CRUD, tipos legal/regulatÃ³rio/contratual/
  expectativa) + isolamento (estende `test_tenant_isolation.py`).

### Implementation

- [X] T018 [P] [US2] Models `StakeholderMap` + `Stakeholder` + `StakeholderRequirement`
  (+migration+RLS) em `wtnapp/models/`.
- [X] T019 [P] [US2] Schema em `wtnapp/schemas/stakeholder_schema.py`.
- [X] T020 [US2] Router `wtnapp/routers/stakeholders.py` (CRUD parte + requisitos) com **derivaÃ§Ã£o
  de estratÃ©gia** + `require_permission` + audit; registrar em `main.py`.
- [X] T021 [P] [US2] Frontend `wtnadmin/src/app/pages/stakeholders/` (matriz PoderÃ—Interesse,
  estratÃ©gia derivada exibida).

**Checkpoint**: US1 + US2 independentes.

---

## Phase 5: User Story 3 â€” DeclaraÃ§Ã£o de Escopo (4.3) (Priority: P3)

**Goal**: escopo derivado das 3 entradas (4.3 a/b/c) com inclusÃµes/exclusÃµes justificadas e
referÃªncia Ã s versÃµes de Contexto e Partes.

**Independent Test**: elaborar escopo com itens; referenciar versÃµes; revisar artefato referenciado
sinaliza referÃªncia desatualizada; isolamento.

### Tests (MANDATORY) âš ï¸

- [X] T022 [P] [US3] Testes do escopo (itens inclusÃ£o/exclusÃ£o justificados; 3 entradas; referÃªncias
  de versÃ£o; **sinalizaÃ§Ã£o de referÃªncia obsoleta**) + isolamento, em `wtnapp/test/test_scope.py`.

### Implementation

- [X] T023 [P] [US3] Models `ScopeStatement` + `ScopeItem` (+migration+RLS) em `wtnapp/models/`
  (refs `context_version_ref`/`stakeholder_version_ref`).
- [X] T024 [P] [US3] Schema em `wtnapp/schemas/scope_schema.py`.
- [X] T025 [US3] Router `wtnapp/routers/scope.py` (`GET`/`PUT /context/scope`, `POST` itens,
  referÃªncias de versÃ£o) + `require_permission` + audit + sinalizaÃ§Ã£o de referÃªncia obsoleta;
  registrar em `main.py`.
- [X] T026 [P] [US3] Frontend `wtnadmin/src/app/pages/scope/`.

**Checkpoint**: US1â€“US3 independentes.

---

## Phase 6: User Story 4 â€” Documento controlado e versionamento (7.5) (Priority: P4)

**Goal**: ciclo de vida (rascunhoâ†’revisÃ£oâ†’em vigorâ†’obsoleto) + versÃµes append-only + "1 em vigor +
rascunho paralelo" para os 3 artefatos.

**Independent Test**: aprovar exige papel (403 sem); transiÃ§Ãµes; UPDATE/DELETE em versÃµes bloqueado;
â‰¤1 em vigor; prÃ³xima anÃ¡lise crÃ­tica vencida destacada.

### Tests (MANDATORY) âš ï¸

- [X] T027 [P] [US4] Testes de ciclo de vida/versionamento: `submit-review`/`approve`; **aprovar sem
  `approve_context_document` â‡’ 403 + audit**; **append-only** (UPDATE/DELETE em `document_versions`
  rejeitado); invariante **â‰¤1 `in_force`**; lista de versÃµes â€” em `wtnapp/test/test_document_version.py`.
- [X] T028 [P] [US4] Teste: artefato com prÃ³xima anÃ¡lise crÃ­tica vencida Ã© destacado.

### Implementation

- [X] T029 [US4] Adicionar aos routers `context_analysis.py`, `stakeholders.py` e `scope.py` os
  endpoints `â€¦/submit-review`, `â€¦/approve` (usando `controlled_document_service`, exigindo
  `approve_context_document`) e `â€¦/versions`; audit de cada transiÃ§Ã£o.
- [X] T030 [US4] Destaque de "prÃ³xima anÃ¡lise crÃ­tica vencida" nas listagens/overview.
- [X] T031 [P] [US4] Frontend: histÃ³rico de versÃµes + aÃ§Ãµes enviar-para-revisÃ£o/aprovar nas telas
  dos artefatos (`context-analysis/`, `stakeholders/`, `scope/`).

**Checkpoint**: US1â€“US4 independentes; artefatos viram documentos controlados.

---

## Phase 7: User Story 5 â€” VisÃ£o consolidada e sugestÃµes (Priority: P5)

**Goal**: visÃ£o consolidada da ClÃ¡usula 4 + sugestÃµes heurÃ­sticas (nunca auto-aplicadas).

**Independent Test**: overview reflete a versÃ£o mais recente; sugestÃµes aparecem; sÃ³ `accept`
persiste.

### Tests (MANDATORY) âš ï¸

- [X] T032 [P] [US5] Testes: overview reflete a versÃ£o mais recente; sugestÃµes heurÃ­sticas (dados
  pessoais â‡’ ANPD/titulares+LGPD); **nenhuma sugestÃ£o persistida sem `accept`** â€” em
  `wtnapp/test/test_overview_suggestions.py`.

### Implementation

- [X] T033 [P] [US5] `suggestion_service` em `wtnapp/services/suggestion_service.py` (regras
  determinÃ­sticas a partir do diagnÃ³stico). **Cobre FR-003**: a reutilizaÃ§Ã£o dos dados do
  diagnÃ³stico nas anÃ¡lises ocorre via sugestÃµes aceitÃ¡veis (sem prÃ©-preenchimento silencioso).
- [X] T034 [US5] Router `wtnapp/routers/context_overview.py` (`GET /context/overview`,
  `GET /context/suggestions`, `POST /context/suggestions/accept`) + audit; registrar em `main.py`.
- [X] T035 [P] [US5] Frontend `wtnadmin/src/app/pages/context-overview/` (visÃ£o consolidada +
  sugestÃµes aceitÃ¡veis).

**Checkpoint**: mÃ³dulo completo (US1â€“US5).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T036 [P] **Tenant isolation sweep**: confirmar que toda query do mÃ³dulo passa pelo
  `tenant_scope` e que RLS estÃ¡ habilitada em todas as novas tabelas.
- [X] T037 [P] **Audit review**: toda operaÃ§Ã£o sensÃ­vel (diagnÃ³stico, CRUD, transiÃ§Ãµes, accept)
  gera log sem PII/segredos.
- [X] T038 Validar `quickstart.md` end-to-end (diagnÃ³stico â†’ anÃ¡lise â†’ partes â†’ escopo â†’ versÃµes â†’
  overview/sugestÃµes). **Validado em 2026-06-22** contra backend local `:8000` + DB real,
  exercitando diagnÃ³stico incremental, anÃ¡lise PESTEL/SWOT, partes interessadas, escopo com
  referÃªncias de versÃ£o, versionamento controlado, overview e aceite explÃ­cito de sugestÃ£o.
- [X] T039 [P] `alembic check` (sem drift) + upgrade/downgrade das novas migrations (SQLite e, em
  CI, PostgreSQL â€” incl. gatilho append-only de `document_versions` e policy de classificaÃ§Ã£o).
- [X] T040 [P] Atualizar docs: seÃ§Ã£o do MÃ³dulo 1 em `CLAUDE.md` (implementado) e referÃªncia ao
  padrÃ£o "Documento Controlado SGSI".
- [X] T041 [P] Testes unitÃ¡rios de frontend (derivaÃ§Ã£o PoderÃ—Interesse no cliente, guards de
  contexto) em `wtnadmin/src/app/pages/**/*.spec.ts`.

---

## Dependencies & Execution Order

- **Setup (P1)** â†’ **Foundational (P2, bloqueia tudo)** â†’ **US1â€“US5 (P3â€“P7)** â†’ **Polish (P8)**.
- **US4 depende de US1â€“US3** (adiciona endpoints de ciclo de vida aos routers dos 3 artefatos) e do
  `controlled_document_service` (Foundational). US3 referencia versÃµes de US1/US2 (testÃ¡vel com
  versÃµes seedadas).
- **Cross-story (mesmo arquivo)**: `context_analysis.py`/`stakeholders.py`/`scope.py` sÃ£o criados em
  US1/US2/US3 e estendidos em US4 (T029); `main.py` recebe registros a cada story;
  `test_tenant_isolation.py` Ã© estendido por US1â€“US3.
- **FR-003 (reutilizaÃ§Ã£o do diagnÃ³stico)** Ã© realizada em **US5** (sugestÃµes aceitÃ¡veis, T032/T033):
  US1 permanece testÃ¡vel de forma independente (diagnÃ³stico e anÃ¡lise por entrada manual); a
  reutilizaÃ§Ã£o sem redigitaÃ§Ã£o Ã© um incremento de US5.

## Parallel Opportunities

- **Foundational**: T003/T004 (nÃºcleo de versÃ£o) antes; T005/T006 em paralelo.
- **Cada story**: testes `[P]` em paralelo; models `[P]` em paralelo; frontend `[P]` em paralelo ao
  backend. ApÃ³s a Foundational, US1â€“US3 podem avanÃ§ar em paralelo (devs diferentes), respeitando as
  notas de arquivos cross-story.

## Implementation Strategy

**MVP**: Phase 1 + 2 + **US1** (diagnÃ³stico + AnÃ¡lise de Contexto, com isolamento). Validar e
demonstrar. Depois US2 â†’ US3 â†’ US4 (torna os artefatos documentos controlados) â†’ US5. Polish ao fim.

## Notes

- **Teste de isolamento de tenant Ã© obrigatÃ³rio** por story (nÃ£o Ã© polish).
- VersÃµes de documento sÃ£o **append-only** (gatilho no banco) â€” nunca editar/apagar.
- SugestÃµes **nunca** sÃ£o aplicadas sem aÃ§Ã£o explÃ­cita do usuÃ¡rio.
- Nenhum filtro de tenant ad-hoc â€” sempre via `tenant_scope` (+ RLS).
- Commit apÃ³s cada task ou grupo lÃ³gico.

**Total: 43 tasks** â€” Setup 2 Â· Foundational 5 Â· US1 10 Â· US2 6 Â· US3 5 Â· US4 5 Â· US5 4 Â· Polish 6
(inclui T005a â€” router da polÃ­tica de classificaÃ§Ã£o â€” e T009a â€” teste de enforcement â€”, adicionados
na remediaÃ§Ã£o do `/speckit-analyze` para FR-011a; FR-003 esclarecido na spec.)
