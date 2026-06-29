---

description: "Task list — Feature 013: SoA Normativa dirigida pelo Tratamento de Riscos"
---

# Tasks: SoA Normativa dirigida pelo Tratamento de Riscos

**Input**: Design documents from `specs/013-soa-normativa-risco/`

**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/openapi-delta.yaml ✓

**Tests**: ⚠️ **OVERRIDE da constitution (White Tree Nexus):** testes NÃO são opcionais. Toda story de
domínio inclui **teste de isolamento de tenant** + casos de falha principais (Princípio VI + DoD).

**Natureza**: **evolução in-place** do módulo de SoA (Feature 005). Reusa router `/soa`, serviços,
`document_versions`, reportlab, RBAC (`view_soa`/`manage_soa`/`approve_soa`). **Não** cria módulo novo,
**não** altera Risco (012)/Gap (004). **1 mudança de schema** (coluna `soa_item.risk_links` JSON).

## Path Conventions

- Backend: `wtnapp/` (`models/`, `schemas/`, `routers/`, `services/`, `alembic/versions/`, `test/`)
- Frontend: `wtnadmin/src/app/pages/` (`soa/`, `soa-versions/`)

---

## Phase 1: Setup

- [X] T001 Confirmar baseline verde e localizar pontos de edição: rodar `pytest wtnapp/test/test_soa*.py -q`
  (suíte 005 deve passar) e revisar `wtnapp/models/soa_model.py`, `wtnapp/routers/soa.py`,
  `wtnapp/services/soa_consolidation_service.py`, `wtnapp/services/soa_export_service.py`,
  `wtnapp/schemas/soa_schema.py`, `wtnapp/services/risk_treatment_service.py::soa_feed`. **Sem novas
  dependências** (reportlab já presente).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema + enums + plumbing compartilhado que TODAS as user stories dependem.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase terminar.

- [X] T002 [P] Adicionar enums em `wtnapp/settings.py`: `SoaKind` (`pre_soa`/`normative`) + mapa de
  rótulos PT-BR (`SOA_KIND_LABELS`) e `SoaDivergenceSource` (`gap`/`risk`). Reusar
  `SoaInclusionReason`/`SoaImplementationStatus`/`GAP_TO_SOA_STATUS`.
- [X] T003 Adicionar coluna `risk_links: Mapped[list] = mapped_column(JSON, nullable=False, default=list)`
  em `SoaItem` (`wtnapp/models/soa_model.py`). Sem outras mudanças de modelo.
- [X] T004 Criar migration idempotente `wtnapp/alembic/versions/<rev>_soa_risk_normative.py`
  (`down_revision="c2d3e4f5a116"`): `add_column` de `soa_item.risk_links` guardado por checagem de
  coluna; backfill `UPDATE soa_item SET risk_links='[]' WHERE risk_links IS NULL`. Sem RLS/trigger novos.
- [X] T005 Estender `wtnapp/schemas/soa_schema.py` com as formas compartilhadas: `RiskLink`
  (`risk_id`,`risk_code`); em `SoaItemResponse` → `risk_links: list[RiskLink]`, `origin: str`,
  `incomplete: bool`; em `DivergenceField` → `source: str = "gap"`, `source_value` (manter `gap_value`
  como alias de compat); em `SoaSummary` → `risk_divergent: int`, `incomplete: int`; novo `SoaReadiness`
  (`kind`,`risk_plan_approved`,`pending_for_normative[]`,`out_of_scope_risk_notices[]`) + `readiness`
  em `SoaResponse`; `kind` em `SoaVersionResponse`; `source` em `ReconcileRequest`.
- [X] T006 [P] Adicionar helpers em `wtnapp/services/soa_consolidation_service.py`: `build_feed_index(db,
  tenant_id)` (chama `risk_treatment_service.soa_feed` **1×**, indexa por `gap_catalog_item_id`) e
  `derive_origin(item)` (`risk`/`manual`/`risk+manual`/`none` a partir de `inclusion_reasons`).

**Checkpoint**: schema/enums/plumbing prontos — user stories podem começar.

---

## Phase 3: User Story 1 - Consolidar a SoA a partir do Tratamento de Riscos (Priority: P1) 🎯 MVP

**Goal**: controle selecionado no tratamento de um risco torna-se Aplicável com razão `risk_treatment`
e riscos tratados estruturados, via consolidação aditiva consumindo o `soa-feed`.

**Independent Test**: numa org com riscos cujo tratamento seleciona controles, `POST /soa/consolidate`
deixa esses controles Aplicável=Sim com `risk_treatment` + `risk_links` (códigos `RSK-####`).

### Tests for User Story 1 (MANDATORY) ⚠️

- [X] T007 [P] [US1] **Tenant isolation**: consolidar no contexto da org B **não** agrega `soa_feed` da
  org A; nenhum `risk_link` cruza tenant — em `wtnapp/test/test_tenant_isolation_soa.py` (estender).
- [X] T008 [P] [US1] Happy path de consolidação por risco (controles do feed → Aplicável + `risk_treatment`
  + `risk_links`) em `wtnapp/test/test_soa_risk_consolidation.py`.
- [X] T009 [P] [US1] Notice fora-Anexo-A: feed aponta `gap_catalog_item` sem `SoaItem` ⇒ não cria item,
  retorna em `out_of_scope` — em `wtnapp/test/test_soa_risk_consolidation.py`.

### Implementation for User Story 1

- [X] T010 [US1] Estender `consolidate(db, tenant_id)` em `wtnapp/services/soa_consolidation_service.py`:
  após o passo Gap, passo risco usando `build_feed_index` — aplicar "1ª-mão" (`applicable=True`, adicionar
  `risk_treatment` sem remover razões existentes, gravar `risk_links`) só a item sem vínculo de risco
  (sem `risk_treatment` **e** `risk_links` vazio); coletar `out_of_scope`. Retornar
  `{added, preserved, risk_applied, out_of_scope}`.
- [X] T011 [US1] `consolidate_soa` em `wtnapp/routers/soa.py`: incluir `risk_applied`/`out_of_scope` no
  `AuditService.log_from_request` (operation `CONSOLIDATE`).
- [X] T012 [US1] `_item_response`/`_soa_response` em `wtnapp/routers/soa.py`: calcular o feed-index **1×**
  por requisição e preencher `risk_links` + `origin` (via `derive_origin`) no item.
- [X] T013 [P] [US1] Frontend `wtnadmin/src/app/pages/soa/soa.ts` (+ `soa.spec.ts`): chips de razão
  (incl. **Risco**), riscos tratados estruturados (códigos) e badge de **origem** (risco/manual).

**Checkpoint**: consolidação dirigida por risco funcional e isolada por tenant.

---

## Phase 4: User Story 3 - Consolidação aditiva/idempotente e transição do Pré-SoA (Priority: P1)

**Goal**: rodar a consolidação não duplica nem apaga edições manuais; orgs com Pré-SoA existente não
quebram (transição sem perda de dados).

**Independent Test**: numa SoA com razões manuais/justificativas, consolidar **2×** não duplica nem
altera campos manuais; itens 005 existentes continuam válidos após a migration.

### Tests for User Story 3 (MANDATORY) ⚠️

- [X] T014 [P] [US3] Idempotência: consolidar 2× sem mudança no insumo ⇒ zero duplicação, zero alteração
  manual — em `wtnapp/test/test_soa_risk_consolidation.py`.
- [X] T015 [P] [US3] Preservação: razão manual `legal` + justificativa preservadas; risco adicionado
  **aditivamente** (ambas as razões) — em `wtnapp/test/test_soa_risk_consolidation.py`.
- [X] T016 [P] [US3] Transição: `risks_treated` legado (texto) preservado; **status de implementação
  derivado do Gap preservado** no passo de risco (FR-005); risco torna **Aplicável** um controle que era
  N/A pelo Gap (1ª-mão) — em `wtnapp/test/test_soa_risk_consolidation.py`.
- [X] T016a [P] [US3] **Degradação fail-closed (SEC-006)**: insumo de risco **vazio/indisponível** na
  consolidação **não** apaga `risk_links` já consolidados (apenas adia) — em
  `wtnapp/test/test_soa_risk_consolidation.py`.

### Implementation for User Story 3

- [X] T017 [US3] Refinar `consolidate()` em `wtnapp/services/soa_consolidation_service.py` para garantir:
  nunca remover razões manuais nem `risks_treated` legado; guard "1ª-mão" idempotente; não duplicar
  `risk_links`.
- [X] T018 [US3] Teste de migração: num DB com itens de SoA pré-existentes (005), aplicar a migration T004
  e asseverar que cada item ganha `risk_links=[]` **sem alterar** nenhum outro campo (razões/justificativas/
  status) — em `wtnapp/test/test_soa_risk_consolidation.py` (ou `test_soa_version.py`). Validação E2E da
  idempotência fica no T041.

**Checkpoint**: consolidação segura, idempotente e não destrutiva para Pré-SoA existente.

---

## Phase 5: User Story 5 - Gate Pré-SoA vs. SoA definitiva na aprovação (Priority: P1)

**Goal**: editar é livre (gate suave); a versão emitida é **rotulada** `normative` (com Plano de
Tratamento aprovado vigente) ou `pre_soa`; UI mostra estado e pendências.

**Independent Test**: sem plano aprovado, aprovar ⇒ versão `pre_soa` + aviso; com
`RiskPlan.current_version_id` ⇒ versão `normative`; rótulo congelado/imutável.

### Tests for User Story 5 (MANDATORY) ⚠️

- [X] T019 [P] [US5] Rótulo do gate: sem plano ⇒ snapshot `soa_kind="pre_soa"`; com plano vigente ⇒
  `"normative"`; rótulo imutável na versão — em `wtnapp/test/test_soa_gate_normative.py`.
- [X] T020 [P] [US5] Completude ainda bloqueia aprovação: item aplicável sem razão (FR-009a) e N/A sem
  justificativa ⇒ 422 com `incomplete` — em `wtnapp/test/test_soa_gate_normative.py`.

### Implementation for User Story 5

- [X] T021 [US5] `_soa_response` em `wtnapp/routers/soa.py`: preencher `readiness` — `kind` (se aprovada
  agora), `risk_plan_approved = RiskPlan.current_version_id is not None` (tenant-scoped),
  `pending_for_normative` (ex.: "Plano de Tratamento de Riscos não aprovado") e `out_of_scope_risk_notices`.
- [X] T022 [US5] `approve_soa` em `wtnapp/routers/soa.py`: gravar no `content_snapshot` `soa_kind` +
  `risk_plan_version_number` + por item `risk_links`/`origin`; manter o bloqueio de completude existente
  (`_incomplete_refs`); audit `APPROVE_SOA` com o rótulo.
- [X] T023 [US5] `_version_response` em `wtnapp/routers/soa.py`: ler `kind` do `content_snapshot`.
- [X] T024 [P] [US5] Frontend `wtnadmin/src/app/pages/soa/soa.ts` (+spec): **banner Pré-SoA × SoA
  normativa** lendo `readiness` (com `pending_for_normative`/notices); `wtnadmin/src/app/pages/
  soa-versions/soa-versions.ts` (+spec): exibir o rótulo `kind` por versão.

**Checkpoint**: gate da esteira operante; versões rotuladas e imutáveis.

---

## Phase 6: User Story 2 - Razões de inclusão manuais e justificativa de exclusão (Priority: P2)

**Goal**: adicionar razões manuais (legal/contratual/melhor prática) coexistindo com `risk_treatment`;
justificar exclusões. (Validação base já existe na 005 — evolução é a coexistência + UI.)

**Independent Test**: adicionar `contractual` a um item incluído por risco mantém **ambas** as razões;
N/A sem justificativa é rejeitado; aplicável sem nenhuma razão é rejeitado.

### Tests for User Story 2 (MANDATORY) ⚠️

- [X] T025 [P] [US2] Coexistência/validação: `risk_treatment` + razão manual persistem juntas; aplicável
  sem razão ⇒ 422; N/A sem justificativa ⇒ 422 — em `wtnapp/test/test_soa.py` (estender).

### Implementation for User Story 2

- [X] T026 [US2] Conferir `update_item` em `wtnapp/routers/soa.py`: edição de razões manuais **não**
  descarta `risk_treatment`/`risk_links`; validações de aplicável/N/A intactas.
- [X] T027 [P] [US2] Frontend `wtnadmin/src/app/pages/soa/soa.ts` (+spec): multiselect de razões manuais
  + campo de justificativa de exclusão, coexistindo com o chip de Risco.

**Checkpoint**: razões manuais e exclusões completas, coexistindo com risco.

---

## Phase 7: User Story 4 - Divergência e reconciliação contra o insumo de risco (Priority: P2)

**Goal**: detectar divergência vs. o insumo de risco vivo e reconciliar item a item explicitamente,
preservando razões manuais; remoção da última razão deixa o item aplicável-incompleto.

**Independent Test**: risco passa a tratar controle não-incluso ⇒ divergente; item com `risk_treatment`
sem risco no feed ⇒ divergente; reconciliar aplica o valor vivo só por ação explícita.

### Tests for User Story 4 (MANDATORY) ⚠️

- [X] T028 [P] [US4] **Tenant isolation**: reconciliar item da org B a partir do contexto A ⇒ 404 + audit
  — em `wtnapp/test/test_tenant_isolation_soa.py` (estender).
- [X] T029 [P] [US4] Detecção dos 2 tipos de divergência de risco (feed aponta mas não incluso; incluso
  por risco mas feed órfão / `risk_links` difere) — em `wtnapp/test/test_soa_risk_divergence.py`.
- [X] T030 [P] [US4] Reconciliação add/remove + remover a **única** razão (`risk_treatment`) ⇒ item
  aplicável-**incompleto** (sem auto-flip); razões manuais preservadas — em
  `wtnapp/test/test_soa_risk_divergence.py`.

### Implementation for User Story 4

- [X] T031 [US4] `compute_risk_divergence(db, item, feed_index)` em
  `wtnapp/services/soa_consolidation_service.py` (fonte `risk`, comparando `risk_links`/inclusão vs. feed).
- [X] T032 [US4] Estender `reconcile(db, item, fields, source)` em
  `wtnapp/services/soa_consolidation_service.py`: aplicar/remover do feed vivo conforme `source`;
  preservar razões manuais; deixar incompleto ao remover a última razão.
- [X] T033 [US4] `wtnapp/routers/soa.py`: `_item_response` agrega divergências de risco (com `source`);
  `list_divergences` inclui fonte risco; `reconcile_item` repassa `body.source` e registra eventos
  append-only por campo (incl. `risk_links`).
- [X] T034 [P] [US4] Frontend `wtnadmin/src/app/pages/soa/soa.ts` (+spec): indicador de **divergência de
  risco** + botão **Reconciliar** (`source=risk`), distinto da divergência de Gap.

**Checkpoint**: divergência/reconciliação por fonte (Gap **e** risco) operante.

---

## Phase 8: User Story 6 - Documento Controlado, versões e exportação PDF enriquecida (Priority: P3)

**Goal**: o PDF da versão reflete o snapshot com razão tipada, riscos estruturados, origem e o rótulo
Pré-SoA / SoA normativa.

**Independent Test**: exportar uma versão `normative` produz PDF com razões/risco/origem por controle e
o rótulo no cabeçalho; versão `pre_soa` antiga reflete seu snapshot.

### Tests for User Story 6 (MANDATORY) ⚠️

- [X] T035 [P] [US6] Export: snapshot/PDF contêm `soa_kind`, `risk_links` (códigos), razões e origem;
  fallback ao `risks_treated` legado; **falha na geração do PDF é fail-closed** (erro limpo e auditável,
  sem corromper a versão — SEC-006) — em `wtnapp/test/test_soa_export.py` (estender).

### Implementation for User Story 6

- [X] T036 [US6] `render_pdf` em `wtnapp/services/soa_export_service.py`: cabeçalho com rótulo do
  `soa_kind`; coluna de riscos a partir de `risk_links` (fallback `risks_treated`); razões tipadas +
  origem por controle; exclusão para não-aplicáveis.
- [X] T037 [US6] `wtnadmin/src/app/pages/soa-versions/soa-versions.ts` (+spec): garantir export e exibição
  do `kind` na lista de versões (integra com T024).

**Checkpoint**: entregável de certificação (PDF) enriquecido e fiel ao snapshot.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T038 [P] Atualizar a seção do Módulo SoA (005) em `CLAUDE.md` para registrar a evolução 013
  (consolidação dirigida por risco, `risk_links`, gate de rótulo) após implementação.
- [X] T039 **Audit review**: confirmar que consolidar/editar/reconciliar/aprovar/exportar geram log e que
  nenhum log/erro expõe PII ou detalhe sensível de risco (só id/código).
- [X] T040 **Tenant isolation sweep**: revisar que a agregação do `soa_feed` e toda query nova passam por
  `tenant_scope`/contexto (fail-closed).
- [ ] T041 Rodar `quickstart.md` (E2E browser, Postgres real) + `alembic upgrade head` **2×** (DB zerado e
  com `create_all`) confirmando idempotência.
- [X] T042 Suítes verdes: `pytest wtnapp/test -q` e `cd wtnadmin && npm test`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA todas as user stories** (schema/enums/schemas/
  feed-index são compartilhados).
- **US1 (Phase 3)**: depende da Foundational. É o MVP.
- **US3 (Phase 4)**: refina/garante propriedades da consolidação de US1 → depende de T010.
- **US5 (Phase 5)**: depende de US1 (itens com `risk_links` no snapshot); independente de US3/US4.
- **US2 (Phase 6)**: depende da Foundational; majoritariamente independente (coexistência de razões).
- **US4 (Phase 7)**: depende de US1 (feed-index/`risk_links`) para divergência/reconciliação.
- **US6 (Phase 8)**: depende de US1 (`risk_links`) **e** US5 (`soa_kind` no snapshot).
- **Polish (Phase 9)**: depende das stories desejadas.

### Within Each User Story

- Testes (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação.
- Service antes do router; router antes do frontend.

### Parallel Opportunities

- Foundational: T002 e T006 em paralelo (arquivos distintos); T003→T004 sequenciais (modelo→migration);
  T005 paralelo a T002/T006.
- Por story, todos os testes `[P]` rodam juntos; tasks de frontend `[P]` correm em paralelo ao backend.
- Após a Foundational, US2 pode ser tocada em paralelo às demais (arquivos quase disjuntos), exceto pelo
  `soa.ts` compartilhado (coordenar T013/T024/T027/T034 no mesmo arquivo).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 2 (Foundational) → Phase 3 (US1, incl. isolamento de tenant).
2. **STOP e VALIDE**: consolidar a partir do tratamento de risco produz itens Aplicável + `risk_treatment`
   + `risk_links`, isolados por tenant. Demo do MVP.

### Incremental Delivery

1. Foundational → US1 (MVP) → US3 (idempotência/transição) → US5 (gate/rótulo) → US2 (razões manuais) →
   US4 (divergência/reconciliação) → US6 (PDF). Cada story agrega valor sem quebrar as anteriores.

---

## Notes

- **Atenção a arquivo compartilhado**: `wtnadmin/src/app/pages/soa/soa.ts` é tocado por T013/T024/T027/
  T034 — sequenciar ou coordenar para evitar conflito (não são `[P]` entre si).
- `routers/soa.py` é tocado por várias stories — coordenar T011/T012/T021/T022/T023/T026/T033.
- **Teste de isolamento de tenant é obrigatório** (US1 e US4) — não é "polish".
- Migration idempotente é regra do projeto; validar em DB zerado **e** com `create_all`.
- Sem novas permissões, sem novas dependências, sem alterar Risco (012)/Gap (004).
