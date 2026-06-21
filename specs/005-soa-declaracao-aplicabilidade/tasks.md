---
description: "Task list para a feature 005 — Statement of Applicability (SoA)"
---

# Tasks: Statement of Applicability (SoA) — Declaração de Aplicabilidade

**Input**: Design documents de `/specs/005-soa-declaracao-aplicabilidade/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml),
[quickstart.md](quickstart.md). **Roda sobre as features 001 (fundação), 002 (Documento Controlado +
classificação), 003 (Motor de Workflow / assinatura) e 004 (Gap Analysis)** — reusa `tenant_scope`+RLS,
RBAC, auditoria, `controlled_document_service`/`document_versions`, `signature_service` e a avaliação
corrente do Gap (`gap_assessment`/`gap_assessment_item`/`gap_catalog_item`).

**Tests**: ⚠️ **OVERRIDE da constitution:** testes NÃO são opcionais — toda story inclui **teste de
isolamento de tenant** + casos de falha principais (Princípio VI).

**Organization**: por user story (US1–US5). Backend `wtnapp/`, frontend `wtnadmin/src/app/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependências pendentes)
- **[Story]**: US1–US5. Setup/Foundational/Polish sem label.

---

## Phase 1: Setup

- [X] T001 Estender `wtnapp/settings.py`: adicionar `DocType.soa`; enums `SoaImplementationStatus`
  (implemented/in_progress/planned/not_started/not_applicable) e `SoaInclusionReason`
  (risk_treatment/legal/contractual/best_practice); e um helper de mapeamento Gap→SoA
  (`meets→implemented`, `partial→in_progress`, `not_meet→not_started`, `not_applicable→not_applicable`,
  `not_filled→None`).
- [X] T002 [P] Estender `wtnapp/helpers/permissions.py`: adicionar `view_soa`, `manage_soa`,
  `approve_soa` à matriz papel→permissão (org_admin: todas; consultant: view+manage;
  manager/internal_auditor/client: view). Assinatura opcional reusa `sign_form` do 003.
- [X] T003 [P] Adicionar `reportlab` a `requirements.txt` (geração de PDF server-side, pure-Python).
- [X] T004 [P] Estender `wtnapp/test/conftest.py` com fixtures do módulo SoA: org com **Gap Analysis
  adotado e avaliado** (alguns controles do Anexo A com status), usuários org_admin/consultant/client
  e helper de header `X-Org-Context`, reusando os das features 002/004.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: models, consolidação, exportação e migration de que US1–US5 dependem.
**⚠️ Nenhuma user story começa antes desta fase.**

- [X] T005 [P] Models `Soa` + `SoaItem` + `SoaItemEvent` em `wtnapp/models/soa_model.py`
  (`tenant_id`+RLS; `Soa` único por org com `current_version_id`; `SoaItem` com
  `gap_assessment_item_id` p/ rastreabilidade; `inclusion_reasons` JSON; `SoaItemEvent` **append-only**).
- [X] T006 `soa_consolidation_service` em `wtnapp/services/soa_consolidation_service.py`: consolida a
  **avaliação corrente** do Gap (itens `annex_a` não descontinuados) → `SoaItem`, **aditivo e
  idempotente** (cria ausentes via mapeamento; preserva edição manual); e `compute_divergence(item)`
  comparando campos consolidados com o valor vivo do `gap_assessment_item`.
- [X] T007 [P] `soa_export_service` em `wtnapp/services/soa_export_service.py`: `render_pdf(version)`
  a partir do `content_snapshot` da `DocumentVersion` (reportlab) — cabeçalho do Documento Controlado
  + tabela dos controles.
- [X] T008 Migration `wtnapp/alembic/versions/<rev>_soa_module.py` (`down_revision="e7f8a9b0c106"`):
  cria `soa`, `soa_item`, `soa_item_event` + **RLS** + **gatilho append-only** em `soa_item_event`,
  **idempotente** (guard `_table_exists`; `DROP POLICY/TRIGGER IF EXISTS`; `CREATE OR REPLACE`).
  `alembic check` sem drift.
- [X] T009 `wtnapp/main.py`: registrar o router `soa`.

**Checkpoint**: models + consolidação + exportação + migration prontos — user stories podem começar.

---

## Phase 3: User Story 1 — Consolidar e visualizar a SoA (Priority: P1) 🎯 MVP

**Goal**: gerar a SoA a partir da avaliação corrente do Gap (93 controles do Anexo A, pré-preenchidos)
e visualizá-la.

**Independent Test**: `POST /soa/consolidate` materializa ~93 itens com aplicabilidade/status mapeados;
`GET /soa` traz itens + resumo; rodar consolidate 2× não duplica; item de outra org nunca aparece.

### Tests (MANDATORY) ⚠️

- [X] T010 [P] [US1] **Teste de isolamento de tenant** em `wtnapp/test/test_tenant_isolation_soa.py`:
  SoA/itens/versões de A inacessíveis a B (404 + audit); consolidar lê só o Gap da própria org.
- [X] T011 [P] [US1] Testes em `wtnapp/test/test_soa_consolidation.py`: consolidar materializa os
  controles do Anexo A; **mapeamento de status** correto; N/A do Gap ⇒ `applicable=false` +
  justificativa; **idempotência** (2ª consolidação não duplica nem sobrescreve edição manual).
- [X] T012 [P] [US1] Testes em `wtnapp/test/test_soa.py`: `GET /soa` retorna itens + `summary`
  (total/applicable/not_applicable); 404 antes de consolidar.

### Implementation

- [X] T013 [US1] Schemas em `wtnapp/schemas/soa_schema.py` (`SoaItem`, `SoaItemUpdate`, `SoaResponse`,
  `SoaVersion`, `DivergenceField`; `ConfigDict(from_attributes=True)`).
- [X] T014 [US1] Router `wtnapp/routers/soa.py`: `GET /soa` (`view_soa`) e `POST /soa/consolidate`
  (`manage_soa`) usando `soa_consolidation_service` + `scoped_query` + audit; registrado em `main.py`.
- [X] T015 [P] [US1] Frontend `wtnadmin/src/app/pages/soa/` (matriz dos 93 controles por tema +
  botão "Consolidar do Gap" + resumo) — Signals, OnPush. Registrar rota `soa` em `app.routes.ts`
  (`permissionGuard('view_soa')`), link no shell e espelhar `view_soa`/`manage_soa`/`approve_soa` em
  `wtnadmin/src/app/core/permissions.ts`.

**Checkpoint**: US1 funcional e isolamento verificado — MVP do módulo.

---

## Phase 4: User Story 2 — Editar a SoA controle a controle (Priority: P2)

**Goal**: editar cada controle (aplicabilidade, razões de inclusão tipadas, exclusão, status,
responsável, prazo, riscos, evidências, observações), com validações.

**Independent Test**: aplicável sem razão de inclusão ⇒ 422; N/A sem justificativa ⇒ 422; edição
válida persiste e gera evento.

### Tests (MANDATORY) ⚠️

- [X] T016 [P] [US2] Testes em `wtnapp/test/test_soa.py` (estende): `PUT /soa/items/{id}` —
  **aplicável sem `inclusion_reasons` ⇒ 422**; **N/A sem `exclusion_justification` ⇒ 422**; edição
  válida persiste, registra `SoaItemEvent` e gera audit.

### Implementation

- [X] T017 [US2] Endpoint `PUT /soa/items/{id}` em `wtnapp/routers/soa.py` (`manage_soa`) com as
  validações de inclusão/exclusão + gravação de `SoaItemEvent` + audit.
- [X] T018 [P] [US2] Frontend: dialog de edição do controle em `wtnadmin/src/app/pages/soa/`
  (razões de inclusão multiselect tipado; justificativa de exclusão condicional; demais campos),
  com validação espelhada (aplicável⇒razão; N/A⇒justificativa) — Reactive Forms.

**Checkpoint**: US1–US2 = SoA completa e editável.

---

## Phase 5: User Story 3 — SoA como Documento Controlado versionado (Priority: P3)

**Goal**: emitir versões imutáveis (rascunho→revisão→aprovado/em vigor) reusando o Documento
Controlado; aprovação do Admin com validação de completude e assinatura opcional.

**Independent Test**: enviar→aprovar cria `DocumentVersion` (`DocType.soa`) imutável; aprovar sem
revisão ⇒ 409; como Consultor ⇒ 403; aprovar SoA incompleta ⇒ 422; versão antiga imutável (gatilho).

### Tests (MANDATORY) ⚠️

- [X] T019 [P] [US3] Testes em `wtnapp/test/test_soa_version.py`: `submit-review`→`approve` cria
  `DocumentVersion` imutável; **aprovar sem revisão ⇒ 409**; **como Consultor ⇒ 403**; **SoA
  incompleta ⇒ 422** (lista de `ref_code`); UPDATE/DELETE da versão bloqueado (append-only);
  assinatura opcional (`sign=true`) marca a versão como assinada.

### Implementation

- [X] T020 [US3] Endpoints `POST /soa/submit-review`, `POST /soa/approve` e `GET /soa/versions` em
  `wtnapp/routers/soa.py`, reusando `controlled_document_service` (`submit_review`/`approve_document`
  com `snapshot_factory` da SoA), `approve_soa`, validação de completude (aplicáveis com razão; N/A
  com justificativa) ⇒ 422; assinatura avançada opcional via `signature_service` (Motor 003); audit.
- [X] T021 [P] [US3] Frontend `wtnadmin/src/app/pages/soa-versions/` (enviar p/ revisão, aprovar com
  classificação/próxima análise + **toggle de assinatura opcional**, listar versões). Registrar rota
  `soa-versions` em `app.routes.ts` (`permissionGuard('view_soa')`) e link no shell.

**Checkpoint**: US1–US3 = SoA emitível e rastreável.

---

## Phase 6: User Story 4 — Exportar a SoA de uma versão (Priority: P4)

**Goal**: exportar PDF correspondendo exatamente à versão selecionada (artefato de auditoria).

**Independent Test**: exportar a versão aprovada gera PDF com o conteúdo daquela versão (não o
rascunho atual); exportação auditada.

### Tests (MANDATORY) ⚠️

- [X] T022 [P] [US4] Testes em `wtnapp/test/test_soa_export.py`: `GET /soa/versions/{id}/export`
  retorna `application/pdf`; o conteúdo reflete o **snapshot da versão** (editar o rascunho depois
  não muda o PDF da versão); ação gera audit; versão de outra org ⇒ 404.

### Implementation

- [X] T023 [US4] Endpoint `GET /soa/versions/{id}/export` em `wtnapp/routers/soa.py` (`view_soa`)
  usando `soa_export_service.render_pdf` a partir do `content_snapshot` da versão + audit; resposta
  `application/pdf` (stream).
- [X] T024 [P] [US4] Frontend: ação "Exportar PDF" por versão em `wtnadmin/src/app/pages/soa-versions/`
  (download do blob).

**Checkpoint**: US1–US4 = núcleo completo (consolidar + editar + emitir + exportar).

---

## Phase 7: User Story 5 — Divergência e reconciliação (Priority: P5)

**Goal**: sinalizar onde a SoA diverge do valor vivo do Gap e reconciliar por ação explícita.

**Independent Test**: editar na SoA um campo vindo do Gap marca o controle como divergente;
`GET /soa/divergences` lista-o; reconciliar aplica o valor vivo do Gap; reconsolidar não apaga edição.

### Tests (MANDATORY) ⚠️

- [X] T025 [P] [US5] Testes em `wtnapp/test/test_soa_divergence.py`: divergência derivada do valor
  vivo do Gap (status via mapeamento); `GET /soa` inclui bloco `divergence`; `GET /soa/divergences`
  filtra; `POST /soa/items/{id}/reconcile` aplica o valor vivo e gera `SoaItemEvent`; isolamento.

### Implementation

- [X] T026 [US5] Endpoints `GET /soa/divergences` e `POST /soa/items/{id}/reconcile` em
  `wtnapp/routers/soa.py` (`view_soa`/`manage_soa`); **enriquecer `GET /soa`** com o bloco
  `divergence[]` por item e `summary.divergent` (via `compute_divergence`); audit na reconciliação.
- [X] T027 [P] [US5] Frontend: badges de divergência + ação "Reconciliar com o Gap" por controle em
  `wtnadmin/src/app/pages/soa/` (mostra valor da SoA vs. valor vivo do Gap).

**Checkpoint**: motor completo (US1–US5).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T028 [P] **Tenant isolation sweep**: confirmar que toda query por-org passa por `tenant_scope`
  e que RLS está habilitada em `soa`, `soa_item`, `soa_item_event`.
- [X] T029 [P] **Audit review**: consolidar, editar item, reconciliar, enviar/aprovar, emitir versão
  e **exportar** geram log sem PII/conteúdo sensível.
- [X] T030 [P] `alembic check` (sem drift) + upgrade/downgrade da migration; **idempotência**
  (rodar `upgrade head` com tabelas já criadas pelo `create_all()` não falha).
- [X] T031 [P] Testes unitários de frontend (matriz/edição/versões/exportação/divergência) em
  `wtnadmin/src/app/pages/soa*/**/*.spec.ts`.
- [X] T032 [P] Atualizar docs: seção do Módulo 3 (SoA) em `CLAUDE.md` (implementado) + nota em
  `docs/README.md`.
- [X] T033 Validar `quickstart.md` end-to-end (cenários A–F: consolidar, editar/validar, divergência/
  reconciliar, revisar/aprovar, exportar, isolamento). **Validado no browser** (backend :8000 +
  frontend :4200 contra Postgres real): A consolida 93 controles; B 422 sem razão / 200 válido;
  C divergência + reconcile; D gate de incompletude (422) → aprovação assinada (201); E PDF
  `%PDF-` 13KB; F isolamento (testes automatizados).

---

## Dependências entre fases

- **Setup (P1)** → **Foundational (P2)** → user stories.
- **US1 (P1)** é o MVP; **US2–US5** dependem do motor (P2). US2/US3/US4/US5 dependem de US1 (SoA
  consolidada). US4 (export) depende de US3 (versão emitida). US5 (divergência) enriquece o `GET /soa`
  do US1.
- **Polish (P8)** por último.

## Exemplos de paralelização

- Setup: T002, T003, T004 em paralelo.
- Foundational: T005, T007 em paralelo; T006 depende de T005; T008 depende de T005; T009 após o router.
- US1: T010, T011, T012 (testes) em paralelo; T015 (frontend) em paralelo com T013/T014.
- US3/US4: testes (T019/T022) e frontends (T021/T024) paralelizáveis dentro de cada story.

## Estratégia de implementação

1. **MVP = US1** (consolidar do Gap + visualizar a SoA) sobre o Foundational (P2) — já entrega a SoA
   dos 93 controles.
2. Incrementos: US2 (editar) → US3 (versão/aprovação) → US4 (exportar PDF) → US5 (divergência).
3. Test-first em cada story (isolamento de tenant obrigatório); migration + RLS + gatilho append-only
   acompanham os modelos; consolidação idempotente.
