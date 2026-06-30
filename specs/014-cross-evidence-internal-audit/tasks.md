---
description: "Task list — Feature 014: Evidências Transversais + Auditoria Interna (5a)"
---

# Tasks: Repositório Transversal de Evidências + Auditoria Interna (9.2)

**Input**: Design documents from `/specs/014-cross-evidence-internal-audit/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: ⚠️ Obrigatórios (override da constitution) — isolamento de tenant + casos de falha por story.

**Organization**: por user story (US1–US8), cada uma testável de forma independente.

## Path Conventions
- Backend: `wtnapp/` (models, schemas, routers, services, helpers, test)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Adicionar enums e constantes em `wtnapp/settings.py`: `SgsiArtifactType`, `EvidenceStatus`,
  `EvidenceEventType`, `InternalAuditStatus`, `AuditChecklistResult`, `AuditFindingType`,
  `AuditFindingStatus`, `PROMOTABLE_FINDING_TYPES`, `AUDIT_CODE_PREFIX="AUD-"`, e
  `DocType.internal_audit_report`.
- [X] T002 [P] Registrar 5 permissões em `wtnapp/helpers/permissions.py` (`view_evidence`,
  `manage_evidence`, `view_internal_audit`, `manage_internal_audit`, `approve_audit_report`) nos papéis
  conforme a matriz do data-model.md.
- [X] T003 [P] Espelhar as 5 permissões em `wtnadmin/src/app/core/permissions.ts`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

- [X] T004 Criar `wtnapp/models/evidence_model.py` com 4 tabelas (`evidence`, `evidence_version`,
  `evidence_link`, `evidence_event`), todas com `tenant_id`; triggers append-only (SQLite+PG) em
  `evidence_version` e `evidence_event` (padrão do `gap_evidence_model.py`).
- [X] T005 [P] Criar `wtnapp/models/internal_audit_model.py` com 5 tabelas
  (`internal_audit_program`, `internal_audit`, `internal_audit_checklist_item`,
  `internal_audit_finding`, `internal_audit_event`), todas com `tenant_id`; trigger append-only em
  `internal_audit_event`.
- [X] T006 Criar migration Alembic `wtnapp/alembic/versions/<rev>_cross_evidence_internal_audit.py`
  com `down_revision = ("a9b0c1d2e308", "d3e4f5a6b217")` (merge dos 2 heads); idempotente
  (`_table_exists`/checagem de coluna), RLS nas 9 tabelas + triggers append-only.
- [X] T007 Na mesma migration, **migrar dados do 008**: copiar `gap_evidence`→`evidence`,
  `gap_evidence_version`→`evidence_version`, `gap_evidence_event`→`evidence_event`, criar
  `evidence_link(target_type=gap_item, target_id=assessment_item_id)`; depois `drop` de
  `gap_evidence*`; `downgrade` reverte (recria e copia de volta). Idempotente.
- [X] T008 [P] Teste de regressão da migração em `wtnapp/test/test_evidence_migration_008.py`:
  histórico/hash/autoria preservados, vínculo `gap_item` criado, contagens batem, sem vazamento
  cross-tenant.
- [X] T009 Registrar routers vazios `evidence`, `internal_audit`, `traceability` em `wtnapp/main.py`
  (`app.include_router(...)`) e criar os arquivos de router stub correspondentes.
- [X] T010 [P] Confirmar cobertura de `helpers/tenant_scope.py` para as 9 entidades novas (todas via
  `scoped_query`) e o reuso de `helpers/classification_access.py` para acesso ao conteúdo.

**Checkpoint**: schema + permissões + migração 008 prontos — user stories podem começar.

---

## Phase 3: User Story 1 — Anexar Evidência a Qualquer Artefato (Priority: P1) 🎯 MVP

**Goal**: Anexar evidência (upload v1 + vínculo + download) a controle SoA / risco / ativo / item Gap,
com integridade, classificação e custódia.

**Independent Test**: anexar evidência válida a cada tipo de artefato; aparece no artefato correto, com
metadados; recusa arquivo inválido; conteúdo confidencial barrado por classificação.

### Tests for User Story 1 (MANDATORY) ⚠️
- [X] T011 [P] [US1] Tenant isolation test em `wtnapp/test/test_tenant_isolation_evidence.py`:
  usuário da Org A não lê/baixa/vincula evidência da Org B (404 + audit).
- [X] T012 [P] [US1] Happy path de upload+vínculo para cada `target_type` em
  `wtnapp/test/test_evidence_repository.py`; **incluir asserção (FR-010)** de que o `status`/avaliação
  do artefato-alvo permanece inalterado após anexar evidência.
- [X] T013 [P] [US1] Casos de falha em `wtnapp/test/test_evidence_repository.py`: arquivo vazio/grande/
  formato inválido, `FIELD_ENCRYPTION_KEY` ausente (fail-closed), download confidencial sem permissão.

### Implementation for User Story 1
- [X] T014 [P] [US1] `wtnapp/schemas/evidence_schema.py`: `EvidenceSummary` (sem `storage_key`,
  com `links[]`/`can_download`), `EvidenceDetail`, `EvidenceUploadRequest`, `EvidenceReplaceRequest`,
  `EvidenceLinkRequest`, `EvidenceLink`.
- [X] T015 [US1] `wtnapp/services/evidence_service.py`: `upload` (cria `evidence`+`version 1`+link
  inicial+eventos `uploaded`/`linked`), `current_version`, `download` (acesso por classificação),
  helpers de custódia; reusa `utils/evidence_storage.py`.
- [X] T016 [US1] `wtnapp/routers/evidence.py`: `POST /evidence`, `GET /evidence/{id}`,
  `GET /evidence/{id}/download` com `require_permission`, `scoped_query`, audit e 404 genérico.
- [X] T017 [US1] Adaptar `wtnapp/routers/gap_evidence.py` para delegar ao `evidence_service`
  (filtro `target_type=gap_item`), **mantendo os mesmos paths/contratos** do 008.
- [X] T018 [P] [US1] `wtnadmin/src/app/shared/evidence-panel/`: componente reutilizável (lista +
  upload + download) com Signals/OnPush/Reactive Forms; helpers de upload/blob em `core/api.ts`.
- [X] T019 [US1] Embutir `evidence-panel` nas telas `pages/soa`, `pages/risk-detail`,
  `pages/asset-detail` e migrar o painel atual de `pages/gap-analysis` para o componente compartilhado.
- [X] T020 [P] [US1] `wtnadmin/src/app/shared/evidence-panel/evidence-panel.spec.ts` (lista/upload/
  estado vazio/regressão do Gap).

**Checkpoint**: US1 funcional — MVP da Fase 1, isolamento verificado, 008 sem regressão.

---

## Phase 4: User Story 2 — Repositório Central Pesquisável (Priority: P2)

**Goal**: Listar/filtrar todas as evidências do tenant e gerir vínculos (1..N).

**Independent Test**: filtros por texto/tipo/classificação/autor/data/estado retornam só o tenant
ativo; vincular evidência a 2º artefato; inativas só com `manage_evidence`.

### Tests for User Story 2 (MANDATORY) ⚠️
- [X] T021 [P] [US2] Isolation + filtros em `wtnapp/test/test_evidence_repository.py` (extensão):
  busca paginada nunca retorna outro tenant.
- [X] T022 [P] [US2] Link/unlink + visibilidade de inativas em `wtnapp/test/test_evidence_links.py`;
  **incluir edge case**: alvo arquivado/inexistente resolve o estado atual sem quebrar o vínculo nem a
  listagem.

### Implementation for User Story 2
- [X] T023 [US2] `evidence_service`: `search` (texto/`target_type`/classificação/autor/data/estado,
  paginado) e `link`/`unlink` (cria `evidence_link`/marca `active=false` + eventos `linked`/`unlinked`).
- [X] T024 [US2] `wtnapp/routers/evidence.py`: `GET /evidence` (filtros), `POST /evidence/{id}/links`,
  `DELETE /evidence/{id}/links/{link_id}`.
- [X] T025 [P] [US2] `wtnadmin/src/app/pages/evidence-repository/`: lista pesquisável/filtrável +
  detalhe com vínculos + ação vincular/desvincular; rota com `permissionGuard('view_evidence')`,
  link no shell.
- [X] T026 [P] [US2] `pages/evidence-repository/evidence-repository.spec.ts` (filtros, vínculos,
  inativas gated).

**Checkpoint**: repositório central pesquisável e reuso de evidência funcionando.

---

## Phase 5: User Story 3 — Cadeia de Custódia e Versionamento (Priority: P2)

**Goal**: Substituir/versionar, inativar e consultar histórico preservando autor/data/ação e hash.

**Independent Test**: substituir → versão anterior no histórico + corrente identificada; inativar →
some das listas, fica no histórico; trilha sem conteúdo/`storage_key`.

### Tests for User Story 3 (MANDATORY) ⚠️
- [X] T027 [P] [US3] Custódia/imutabilidade em `wtnapp/test/test_evidence_custody.py`: replace cria
  versão N imutável (trigger bloqueia UPDATE/DELETE), inativação preserva histórico, eventos corretos.
- [ ] T028 [P] [US3] Histórico gated por `manage_evidence` (versões anteriores/inativas) em
  `wtnapp/test/test_evidence_custody.py`.

### Implementation for User Story 3
- [X] T029 [US3] `evidence_service`: `replace` (versão N+1, classificação obrigatória, atualiza
  corrente, evento `replaced`) e `inactivate` (status + `inactivated_*` + evento `inactivated`).
- [X] T030 [US3] `wtnapp/routers/evidence.py`: `POST /evidence/{id}/versions`,
  `DELETE /evidence/{id}` (inativar), `GET /evidence/{id}/history` (`manage_evidence`).
- [ ] T031 [P] [US3] `evidence-panel`: ações substituir/inativar + visão de histórico (versões+eventos)
  para `manage_evidence`.

**Checkpoint**: cadeia de custódia completa; Fase 1 (evidências) inteira entregue.

---

## Phase 6: User Story 4 — Planejar e Conduzir Auditoria Interna (Priority: P3)

**Goal**: Programa → auditoria (escopo/critérios/auditor/período/estado) → checklist (manual +
importação SoA/Gap).

**Independent Test**: criar programa+auditoria (`AUD-####`, `planned`), adicionar/importar itens,
transitar estados; transição inválida ⇒ 409; tudo tenant-scoped.

### Tests for User Story 4 (MANDATORY) ⚠️
- [X] T032 [P] [US4] Isolation em `wtnapp/test/test_tenant_isolation_internal_audit.py`
  (programa/auditoria/checklist da Org B inacessíveis).
- [X] T033 [P] [US4] Ciclo de vida + transições inválidas + import de checklist em
  `wtnapp/test/test_internal_audit_lifecycle.py`; **incluir edge case**: item de checklist cujo alvo
  (controle/cláusula/risco) deixou de existir é tratado graciosamente (referência preservada, sem
  quebrar a auditoria).

### Implementation for User Story 4
- [X] T034 [P] [US4] `wtnapp/schemas/internal_audit_schema.py`: `ProgramRequest/Summary`,
  `AuditRequest/Summary/Detail` (com `readiness`), `ChecklistItemRequest/Summary`,
  `ChecklistImportRequest`.
- [X] T035 [US4] `wtnapp/services/internal_audit_service.py`: programas, auditorias (geração de `code`
  por tenant, imutável; **validar que `auditor_member_id` é membro ativo do tenant** — N1), máquina de
  estados (`start`/`complete`/`cancel`), checklist manual + `import_from_scope` (SoA/Gap), trilha
  `internal_audit_event`. **Sem campo `mandatory`** — gate de completude usa `result=pendente`.
- [X] T036 [US4] `wtnapp/routers/internal_audit.py`: endpoints de programs, audits (CRUD + `transition`)
  e checklist (`GET/POST` + `/import`), com RBAC/scoped_query/audit.
- [X] T037 [P] [US4] `wtnadmin/src/app/pages/internal-audit/` (lista programas+auditorias + criar) e
  base de `pages/internal-audit-detail/` (seção checklist); rotas com
  `permissionGuard('view_internal_audit')`, grupo no shell.
- [X] T038 [P] [US4] `pages/internal-audit/internal-audit.spec.ts` (criar/listar/transição).

**Checkpoint**: planejamento/condução de auditoria funcional.

---

## Phase 7: User Story 5 — Registrar Constatações (Priority: P3)

**Goal**: Constatações (5 tipos) com vínculo a controle/cláusula/risco e evidência anexada; NC
promovíveis com `nonconformity_ref` reservado.

**Independent Test**: registrar uma de cada tipo; NC maior/menor `promotable=true` (ref vazia); anexar
evidência (`target_type=audit_finding`); remoção lógica preserva trilha.

### Tests for User Story 5 (MANDATORY) ⚠️
- [X] T039 [P] [US5] Constatações por tipo + `promotable` + vínculo de evidência em
  `wtnapp/test/test_internal_audit_findings.py`.
- [X] T040 [P] [US5] Isolation + remoção lógica/trilha em
  `wtnapp/test/test_internal_audit_findings.py`.

### Implementation for User Story 5
- [X] T041 [US5] `internal_audit_service`: CRUD de finding (deriva `promotable`, bloqueia set de
  `nonconformity_ref`), vínculo opcional a checklist item, remoção lógica + evento.
- [X] T042 [US5] `wtnapp/routers/internal_audit.py`: `GET/POST /audits/{id}/findings`,
  `PUT/DELETE /findings/{id}`; `FindingSummary` expõe `promotable`/`nonconformity_ref`/`evidence_links`.
- [X] T043 [P] [US5] `pages/internal-audit-detail/`: seção de constatações (tipo+vínculo) + anexar
  evidência via `evidence-panel` (`target_type=audit_finding`).
- [X] T044 [P] [US5] `pages/internal-audit-detail/internal-audit-detail.spec.ts` (findings + evidência).

**Checkpoint**: constatações com base preparada para a 5b.

---

## Phase 8: User Story 6 — Relatório de Auditoria como Documento Controlado (Priority: P4)

**Goal**: Gerar/submeter/aprovar (assinatura opcional) e exportar PDF do relatório; gate duro de
completude.

**Independent Test**: gerar relatório, gate bloqueia aprovação se incompleto, aprovar (com/sem
assinatura) congela versão imutável, exportar PDF.

### Tests for User Story 6 (MANDATORY) ⚠️
- [X] T045 [P] [US6] Geração/gate/aprovação/imutabilidade em
  `wtnapp/test/test_internal_audit_report.py`.
- [X] T046 [P] [US6] Export PDF + assinatura opcional + isolation em
  `wtnapp/test/test_internal_audit_report.py`.

### Implementation for User Story 6
- [X] T047 [US6] `wtnapp/services/internal_audit_report_service.py`: `snapshot_factory` (escopo/
  critérios/itens/constatações) + reuso de `controlled_document_service` (submit-review/approve) +
  `signature_service` (opcional) + **gate de completude** (`status=completed` **e** zero itens com
  `result=pendente`).
- [X] T048 [P] [US6] `wtnapp/services/internal_audit_export_service.py`: PDF via reportlab a partir do
  `content_snapshot` (rótulos, tipos de constatação, vínculos, evidências referenciadas).
- [X] T049 [US6] `wtnapp/routers/internal_audit.py`: `report/submit-review`, `report/approve`,
  `report/versions`, `report/versions/{id}/export` (audit + `approve_audit_report`).
- [X] T050 [P] [US6] `pages/internal-audit-detail/`: seção relatório (submeter/aprovar/assinar/listar
  versões/exportar PDF) com `getBlob`.

**Checkpoint**: relatório versionável/aprovável/exportável — gate duro da etapa.

---

## Phase 9: User Story 7 — Rastreabilidade / Timeline (Priority: P5)

**Goal**: Timeline read-only por artefato agregando evidências/constatações/eventos.

**Independent Test**: timeline de controle/risco/ativo em ordem cronológica, só metadados; estado vazio
claro; nunca agrega outro tenant.

### Tests for User Story 7 (MANDATORY) ⚠️
- [X] T051 [P] [US7] Agregação + ordem + estado vazio + isolation em
  `wtnapp/test/test_traceability_timeline.py`.

### Implementation for User Story 7
- [X] T052 [US7] `wtnapp/services/traceability_service.py`: agrega `evidence_event`/`evidence_link`/
  `internal_audit_finding` por `target_type`+`target_id` (só metadados).
- [X] T053 [US7] `wtnapp/routers/traceability.py`: `GET /traceability/timeline` com **RBAC composto**
  (view do módulo do artefato-alvo + `view_evidence`; constatações só com `view_internal_audit`, senão
  omitidas sem revelar contagem) + scoped_query + 404 genérico (ver RBAC da timeline no data-model).
- [X] T054 [P] [US7] Componente de timeline embutido nas telas `pages/soa`/`risk-detail`/`asset-detail`
  + `.spec.ts`.

**Checkpoint**: rastreabilidade transversal de leitura.

---

## Phase 10: User Story 8 — Dashboard do Módulo + Readiness (Priority: P5)

**Goal**: Cards do módulo (evidências por status/classificação, auditorias por status, constatações por
tipo) + readiness no Dashboard de Conformidade.

**Independent Test**: contagens corretas escopadas ao tenant; card de readiness reflete auditoria
concluída/relatório aprovado; estado vazio sem erro.

### Tests for User Story 8 (MANDATORY) ⚠️
- [X] T055 [P] [US8] Contagens + isolation em `wtnapp/test/test_audit_metrics.py`.
- [X] T056 [P] [US8] Card de readiness em `wtnapp/test/test_dashboard.py` (extensão).

### Implementation for User Story 8
- [X] T057 [US8] `wtnapp/services/audit_metrics_service.py`: contagens simples por status/
  classificação/tipo (exclui inativas conforme regra).
- [X] T058 [US8] `wtnapp/routers/internal_audit.py`: `GET /internal-audit/dashboard`.
- [X] T059 [US8] Estender `wtnapp/services/dashboard_service.py` + `schemas/dashboard_schema.py` com
  card desta etapa (`DashboardModuleId.internal_audit`, gating por `view_internal_audit`, fail-open).
- [X] T060 [P] [US8] `pages/internal-audit-dashboard/` (cards) + card na home; `.spec.ts`.

**Checkpoint**: visão executiva + readiness na esteira; feature completa.

---

## Phase 11: Polish & Cross-Cutting Concerns

- [X] T061 [P] **Audit review**: confirmar que upload/download/replace/inactivate/link/unlink, CRUD de
  auditoria/constatação, transições e relatório geram audit log sem PII/`storage_key`/conteúdo.
- [X] T062 [P] **Tenant isolation sweep**: revisar que nenhuma query nova (evidence/internal_audit/
  traceability/metrics) escapou de `scoped_query`; consolidação/timeline fail-closed.
- [X] T063 [P] Atualizar seção do módulo no `CLAUDE.md` (Feature 014 implementada) e mover o bloco do
  plano ativo.
- [X] T064 Rodar suíte backend completa (`pytest wtnapp/test`) e frontend (`npm test` em `wtnadmin/`).
- [ ] T065 Validar `quickstart.md` no browser + `alembic upgrade head` no Postgres real (inclui
  regressão do 008 e merge dos heads).

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (P1)** → **Foundational (P2)** bloqueia todas as stories.
- **US1 (P3)** é o MVP; **US2/US3 (P4–P5)** estendem o `evidence_service`/router de US1.
- **US4 (P6)** → **US5 (P7)** → **US6 (P8)** são sequenciais no domínio de auditoria (findings dependem
  da auditoria; relatório depende de findings). US5/US6 também consomem `evidence-panel` (US1).
- **US7/US8** dependem de evidências (US1–US3) e auditoria (US4–US6) para ter conteúdo.
- **Polish (P11)** por último.

### Within Each User Story
- Testes (incl. isolamento) escritos e falhando antes da implementação.
- Models → services → endpoints → UI.

### Parallel Opportunities
- Setup: T002/T003 em paralelo. Foundational: T005/T008/T010 [P].
- Dentro de cada story, tasks [P] (schemas/UI/tests em arquivos distintos) rodam em paralelo.
- Após a Foundational, o domínio de **evidências** (US1–US3) e o de **auditoria** (US4–US6) podem ser
  tocados por devs diferentes; convergem em US5 (evidência↔constatação) e US7/US8.

---

## Implementation Strategy

### MVP First
1. Phase 1 (Setup) → Phase 2 (Foundational, inclui migração do 008) → Phase 3 (US1).
2. **STOP e VALIDE**: anexar evidência transversal + 008 sem regressão.

### Incremental Delivery
- US1 (anexar) → US2 (repositório) → US3 (custódia) = Fase 1 completa.
- US4 (auditoria) → US5 (constatações) → US6 (relatório) = Fase 2 completa.
- US7 (timeline) + US8 (dashboard) = fechamento transversal.

---

## Notes
- [P] = arquivos diferentes, sem dependências.
- Teste de isolamento de tenant é obrigatório (não é polish).
- Migração do 008 deve preservar histórico/hash/autoria e manter os endpoints do Gap.
- `nonconformity_ref` permanece **vazio** nesta feature (gancho da 5b).
- Sem novas dependências; reuso de `evidence_storage`, `controlled_document_service`,
  `document_versions`, `signature_service`, reportlab, `dashboard_service`.
