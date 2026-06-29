---

description: "Task list — Módulo de Gestão de Riscos (Feature 012)"
---

# Tasks: Módulo de Gestão de Riscos (Ameaças/Vulnerabilidades · Avaliação 6.1.2 · Tratamento 6.1.3)

**Input**: Design documents from `/specs/012-risk-management/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml), [quickstart.md](quickstart.md)

**Tests**: ⚠️ **OVERRIDE da constitution (White Tree Nexus):** testes NÃO são opcionais. Toda story de
domínio inclui **teste de isolamento de tenant** + casos de falha principais (Princípio VI + DoD).

**Organization**: por user story (US1–US6), em ordem de prioridade. Cada story é um incremento
independentemente testável.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: a qual user story a task pertence (US1…US6)
- Caminhos de arquivo exatos nas descrições

## Path Conventions (web monorepo)

- Backend: `wtnapp/` (models, schemas, routers, services, helpers, data, alembic, test)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Adicionar enums e constantes em `wtnapp/settings.py`: `ThreatCategory`, `ThreatOrigin`,
  `VulnerabilityCategory`, `RiskStatus`, `RiskTreatmentOption`, `RiskEventType`; `DocType.risk_treatment_plan`;
  `RISK_CODE_PREFIX="RSK"`; e `DEFAULT_RISK_METHODOLOGY` (5x5 — escalas, `risk_levels`, `risk_matrix`,
  `acceptance` ≤ Médio, `cia_impact_map` baixa→2/media→3/alta→4/critica→5).
- [X] T002 [P] Adicionar `view_risk`/`manage_risk`/`approve_risk_plan` à matriz `PERMISSIONS` em
  `wtnapp/helpers/permissions.py` (Super Admin+Admin: as 3; Consultor: view+manage; Gestor/Dono de
  processo/Dono de controle/Auditor/Cliente: view; Convidado: nenhuma).
- [X] T003 [P] Frontend: espelhar `view_risk`/`manage_risk`/`approve_risk_plan` em
  `wtnadmin/src/app/core/permissions.ts`; adicionar tipos do módulo em `wtnadmin/src/app/core/models.ts`
  (Risk, Methodology, Threat, Vulnerability, Treatment, Control, RiskEvent + enums).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: modelos, migration, metodologia-default, semente/adoção e esqueleto do router — base de
TODAS as stories.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase terminar.

- [X] T004 [P] Criar `wtnapp/models/risk_methodology_model.py` (`RiskMethodology`, 1 por org, colunas
  JSON: escalas/`risk_levels`/`risk_matrix`/`acceptance`/`cia_impact_map`; `tenant_id` único).
- [X] T005 [P] Criar `wtnapp/models/risk_catalog_model.py`: `ThreatSeedItem`/`VulnerabilitySeedItem`
  (**sem `tenant_id`** — plataforma), `OrgThreat`/`OrgVulnerability` (tenant + `seed_item_id` +
  arquivamento), `AssetThreatLink`/`AssetVulnerabilityLink` (FK `asset_items`, mesmo tenant).
- [X] T006 [P] Criar `wtnapp/models/risk_model.py`: `Risk`, `RiskAssetLink`, `RiskTreatmentControl`,
  `RiskPlan`, `RiskEvent` (tabela `risk_events`) (+ gatilhos append-only de `risk_events` para SQLite e
  PostgreSQL, padrão `asset_item_events`).
- [X] T007 Registrar os novos modelos em `wtnapp/models/__init__.py`.
- [X] T008 Criar migration `wtnapp/alembic/versions/c2d3e4f5a116_risk_management_module.py`
  (`down_revision="b1c2d3e4f015"`, **idempotente**: `_table_exists`; RLS `tenant_isolation` com
  `DROP POLICY IF EXISTS` nas **10 tabelas tenant-scoped** — `risk_methodology`, `org_threat`,
  `org_vulnerability`, `asset_threat_link`, `asset_vulnerability_link`, `risk`, `risk_asset_link`,
  `risk_treatment_control`, `risk_plan`, `risk_events`; **sem RLS** nas 2 tabelas-semente
  (`threat_seed_item`, `vulnerability_seed_item`); triggers append-only de `risk_events` com
  `CREATE OR REPLACE`/`IF NOT EXISTS`). Validar `alembic check` sem drift.
- [X] T009 Criar `wtnapp/data/iso27005_seed.py` (ameaças + vulnerabilidades, **PT-BR original**, base
  ISO 27005, sem reproduzir texto normativo) e `load_seed()` em `wtnapp/services/risk_catalog_service.py`
  (idempotente por `code`); chamar no startup como o `load_seed` do Gap.
- [X] T010 Criar `wtnapp/services/risk_methodology_service.py` com `get_or_default(tenant)` (devolve a
  config da org ou o **default 5x5** in-code), `compute_level(prob, impact, methodology)` e
  `is_above_acceptance(level_key, methodology)` (funções puras) + mapeamento `cia_impact_map`.
- [X] T011 [P] Criar `wtnapp/schemas/risk_schema.py` com os DTOs base (Methodology, Threat/Vulnerability
  Create/Response, Risk Create/Evaluate/Response, Treatment, Control, Accept, Plan, Heatmap, Dashboard,
  SoaFeedItem, RiskEvent), Pydantic v2 (`from_attributes`).
- [X] T012 Criar o esqueleto do router `wtnapp/routers/risk.py` (`APIRouter(prefix="/risk")`,
  `db_dependency`, `scoped_query`, `AuditService`) e registrá-lo em `wtnapp/main.py`.
- [X] T013 Implementar adoção em `risk_catalog_service.adopt_seed(tenant)` (aditiva/idempotente) +
  endpoints `POST /risk/threats/adopt`, `POST /risk/vulnerabilities/adopt`, `GET /risk/threats`,
  `GET /risk/vulnerabilities` em `wtnapp/routers/risk.py` (para US1 referenciar o catálogo).

**Checkpoint**: fundação pronta — metodologia default, catálogo adotável e modelos disponíveis.

---

## Phase 3: User Story 1 - Avaliar e registrar os riscos do SGSI (Priority: P1) 🎯 MVP

**Goal**: registrar riscos como cenário (ameaça + vulnerabilidade + 0..n ativos), derivar o impacto da
CIA (override justificado), calcular o nível pela matriz e a marcação acima/abaixo do critério, com
listagem (filtros/busca) e heat map 5x5.

**Independent Test**: criar riscos referenciando o catálogo adotado, avaliar prob+impacto+dono e
confirmar nível/aceitação calculados, override justificado, cenário sem ativos com impacto manual, e o
heat map distribuindo os riscos — tudo só no tenant ativo.

### Tests for User Story 1 (MANDATORY) ⚠️

- [X] T014 [P] [US1] **Tenant isolation test**: usuário do tenant A não lê/edita/avalia/arquiva risco do
  tenant B (404 + audit) em `wtnapp/test/test_tenant_isolation_risk.py`.
- [X] T015 [P] [US1] Test do happy path em `wtnapp/test/test_risk_assessment.py`: cenário, código `RSK-####`,
  derivação de impacto `max(C,I,A)`, nível pela matriz, marcação de aceitação, heat map.
- [X] T016 [P] [US1] Test dos casos de falha em `wtnapp/test/test_risk_assessment.py`: override sem
  justificativa (422), cenário sem ativos exige impacto manual, CIA incompleta → manual, validações de
  cenário (título/descrição/ameaça/vuln), filtros/busca.

### Implementation for User Story 1

- [X] T017 [US1] Implementar `wtnapp/services/risk_service.py`: geração de `RSK-####` (sequência por
  tenant), derivação de impacto da CIA + override registrado, transições de status
  (identified→assessed), diffing e gravação de `risk_events` (com `reason` nas mudanças de nível).
- [X] T018 [US1] Implementar o heat map 5x5 em `wtnapp/services/risk_metrics_service.py`
  (agregação por célula probabilidade × impacto, colorida pelo `level_key`) — exposto por `GET /risk/matrix`.
- [X] T019 [US1] Implementar endpoints em `wtnapp/routers/risk.py`: `POST /risk/risks`, `GET /risk/risks`
  (filtros: status/level/owner/asset/above_acceptance/has_treatment + busca), `GET /risk/risks/{id}`,
  `PUT /risk/risks/{id}` (avaliar), `POST /risk/risks/{id}/archive`, `GET /risk/matrix` (heat map 5x5
  desta fatia; o dashboard completo do módulo é `GET /risk/dashboard`, construído na US5) — com
  `require_permission` + `AuditService` + 404 genérico cross-tenant.
- [X] T020 [US1] Adicionar validações condicionais e mensagens de erro (sem vazar internals) +
  audit nos pontos sensíveis no router/serviço da US1.
- [X] T021 [P] [US1] Frontend `wtnadmin/src/app/pages/risks/` (lista + cards/filtros/busca + heat map +
  criar cenário), Signals/OnPush/Reactive Forms; rota com `permissionGuard('view_risk')` em
  `app.routes.ts` + link no shell.
- [X] T022 [P] [US1] Frontend `wtnadmin/src/app/pages/risk-detail/` (cenário + avaliação: prob/impacto/
  dono, exibição de nível/aceitação, divergência de impacto) + rota.
- [X] T023 [P] [US1] Specs frontend `risks.spec.ts` e `risk-detail.spec.ts`.

**Checkpoint**: Registro de Riscos avaliável, filtrável e com heat map — MVP funcional e isolado.

---

## Phase 4: User Story 2 - Catálogo de ameaças/vulnerabilidades + vínculo a ativos (Priority: P2)

**Goal**: gerir os catálogos da org (custom, arquivar) sobre a semente adotada e vincular ameaças/
vulnerabilidades a ativos (preenchendo os placeholders do detalhe do ativo); referência de vuln a gap.

**Independent Test**: adotar (idempotente), criar custom, arquivar, vincular a um ativo e confirmar nos
placeholders do detalhe do ativo; relacionar uma vulnerabilidade a um gap do catálogo da org.

### Tests for User Story 2 (MANDATORY) ⚠️

- [X] T024 [P] [US2] **Tenant isolation test**: catálogo/ameaça/vuln/vínculo do tenant B inacessível ao A
  (404 + audit) em `wtnapp/test/test_tenant_isolation_risk.py`.
- [X] T025 [P] [US2] Test em `wtnapp/test/test_risk_catalog.py`: adoção aditiva/idempotente, criar custom,
  arquivar (exige justificativa, sem exclusão física), vínculo a ativo (mesmo tenant), referência de vuln
  a gap da org.

### Implementation for User Story 2

- [X] T026 [US2] Estender `wtnapp/services/risk_catalog_service.py`: criar/editar custom, arquivar lógico
  com justificativa, vínculos `asset_threat_link`/`asset_vulnerability_link` (mesmo tenant), referência
  de vuln a `gap_catalog_item`.
- [X] T027 [US2] Endpoints em `wtnapp/routers/risk.py`: `POST/PUT /risk/threats`, `POST /risk/threats/{id}/archive`,
  `POST /risk/threats/{id}/assets`; análogos de `/risk/vulnerabilities`; `GET /risk/assets/{asset_id}/links`
  (ameaças/vulnerabilidades) — `manage_risk` + audit.
- [X] T028 [P] [US2] Frontend `wtnadmin/src/app/pages/risk-catalog/` (abas Ameaças e Vulnerabilidades:
  adotar/criar/editar/arquivar/vincular a ativos) + rota + link no shell (Fase 1 da esteira).
- [X] T029 [US2] Frontend `wtnadmin/src/app/pages/asset-detail/`: ligar os placeholders "Ameaças
  vinculadas"/"Vulnerabilidades vinculadas" a `GET /risk/assets/{id}/links` (sem alterar o modelo de Ativos).
- [X] T030 [P] [US2] Spec frontend `risk-catalog.spec.ts` + atualização da `asset-detail.spec.ts`.

**Checkpoint**: catálogos geríveis e vinculados aos ativos; US1 segue funcionando.

---

## Phase 5: User Story 3 - Plano de tratamento e insumo da SoA (Priority: P3)

**Goal**: definir tratamento (mitigar/aceitar/transferir/evitar), selecionar controles do Gap da org
(resp.+prazo), re-pontuar residual, aceitar riscos (justificativa+dono), consolidar/aprovar o Plano
(Documento Controlado, assinatura opcional) e expor o vínculo controle←risco (SoA-feed read-only).

**Independent Test**: tratar "mitigar" com ≥1 controle do Gap (resp.+prazo), re-pontuar e ver nível
residual/critério, aceitar um risco, aprovar o plano (versão imutável; gate duro com risco não
avaliado), e conferir o SoA-feed sem que a SoA seja escrita.

### Tests for User Story 3 (MANDATORY) ⚠️

- [X] T031 [P] [US3] **Tenant isolation test**: tratamento/controle/plano/SoA-feed do tenant B inacessível
  ao A (404 + audit) em `wtnapp/test/test_tenant_isolation_risk.py`.
- [X] T032 [P] [US3] Test em `wtnapp/test/test_risk_treatment.py`: opção; mitigar exige ≥1 controle com
  responsável+prazo (422); residual re-pontuado + comparação inerente×residual + marcação de critério;
  aceitar exige justificativa + dono (422); SoA-feed expõe controle←riscos e **não** grava na SoA;
  controle só referencia gap do mesmo tenant.
- [X] T033 [P] [US3] Test em `wtnapp/test/test_risk_plan.py`: consolidação; `submit-review`; **gate duro**
  (aprovar com risco não avaliado → 409); aprovação cria versão imutável (`DocType.risk_treatment_plan`);
  assinatura avançada opcional **fail-closed** (falha de OTP/e-mail bloqueia apenas a assinatura, não a
  aprovação sem assinatura — SEC-006); append-only da versão.

### Implementation for User Story 3

- [X] T034 [US3] Implementar `wtnapp/services/risk_treatment_service.py`: opção de tratamento +
  re-pontuação residual (transições assessed→in_treatment/accepted), controles (gap da org ou custom,
  validação resp.+prazo p/ mitigar), aceitação (justificativa + dono), eventos com `reason`.
- [X] T035 [US3] Consolidação + aprovação do Plano no `risk_treatment_service` reusando
  `services/controlled_document_service` (`submit_review`/`approve_document`, novo
  `DocType.risk_treatment_plan`) + assinatura opcional via `services/signature_service` (**fail-closed**:
  indisponibilidade de OTP/e-mail falha apenas a assinatura, sem bloquear a aprovação não assinada —
  SEC-006); e `soa_feed(tenant)` (read-only) que agrega controle←riscos. **Não** escrever em `soa`/`soa_item`.
- [X] T036 [US3] Endpoints em `wtnapp/routers/risk.py`: `PUT /risk/risks/{id}/treatment`,
  `GET/POST /risk/risks/{id}/controls`, `DELETE /risk/risks/{id}/controls/{control_id}`,
  `POST /risk/risks/{id}/accept`, `GET /risk/plan`, `POST /risk/plan/submit-review`,
  `POST /risk/plan/approve` (`approve_risk_plan`), `GET /risk/plan/versions`, `GET /risk/soa-feed`.
- [X] T037 [P] [US3] Frontend `wtnadmin/src/app/pages/risk-treatment-plan/` (consolidar/revisar/aprovar/
  assinar/listar versões) + rota + link no shell (Fase 3 da esteira) + spec.
- [X] T038 [US3] Frontend `pages/risk-detail/`: seção de tratamento (opção, controles do Gap, residual,
  aceitação) + atualizar `risk-detail.spec.ts`.
- [X] T039 [US3] Frontend `pages/asset-detail/`: ligar placeholders "Riscos vinculados"/"Controles
  relacionados" a `GET /risk/assets/{id}/links` (riscos/controles).

**Checkpoint**: tratamento + plano aprovável + SoA-feed prontos; US1/US2 intactos.

---

## Phase 6: User Story 4 - Configurar a metodologia de risco (Priority: P4)

**Goal**: editar escalas, matriz, critério de aceitação e mapa CIA→impacto; recálculo em massa dos
riscos ao alterar a metodologia (gate suave: default 5x5 quando não configurada).

**Independent Test**: editar rótulos/matriz/critério, salvar e confirmar que novos e existentes riscos
recalculam nível/aceitação a partir de prob/impacto; sem config, confirmar aviso + default 5x5.

### Tests for User Story 4 (MANDATORY) ⚠️

- [X] T040 [P] [US4] Test em `wtnapp/test/test_risk_methodology.py`: default 5x5 quando ausente; edição
  válida; validação (5 níveis/25 células/keys consistentes — 422); **recálculo em massa** reescreve
  `inherent_level_key`/`above_acceptance` e sinaliza/registra os que mudaram; isolamento de tenant.

### Implementation for User Story 4

- [X] T041 [US4] Estender `risk_methodology_service` com validação da config e `recompute_all(tenant)`
  (recalcula níveis/aceitação de todos os riscos a partir de prob/impacto e gera `risk_events` de mudança
  de nível).
- [X] T042 [US4] Endpoints `GET /risk/methodology` e `PUT /risk/methodology` (`manage_risk`; o PUT
  persiste e dispara `recompute_all`) em `wtnapp/routers/risk.py` + audit.
- [X] T043 [P] [US4] Frontend `wtnadmin/src/app/pages/risk-methodology/` (escalas/matriz/critério/CIA→
  impacto) + rota + link no shell + spec.

**Checkpoint**: metodologia configurável com recálculo consistente.

---

## Phase 7: User Story 5 - Dashboard do módulo e readiness na esteira (Priority: P5)

**Goal**: dashboard do módulo (heat map + distribuições + top riscos + sem tratamento + aceitos + por
ativo/dono + inerente×residual) e card de readiness do módulo na esteira (Feature 006).

**Independent Test**: com riscos avaliados/tratados, conferir o dashboard e o card da esteira refletindo
status/próxima ação/bloqueios — só do tenant ativo.

### Tests for User Story 5 (MANDATORY) ⚠️

- [X] T044 [P] [US5] Test em `wtnapp/test/test_risk_metrics.py`: heat map, distribuição por nível, top
  riscos, sem tratamento, aceitos, residual pendente, por ativo/dono, inerente×residual.
- [X] T045 [P] [US5] Test em `wtnapp/test/test_risk_dashboard_card.py`: card de risco na esteira
  (gating `view_risk`, fail-open, status/próxima ação/bloqueios) + isolamento.

### Implementation for User Story 5

- [X] T046 [US5] Estender `wtnapp/services/risk_metrics_service.py` com as distribuições/recortes do
  dashboard (além do heat map da US1).
- [X] T047 [US5] Adicionar `GET /risk/dashboard` em `wtnapp/routers/risk.py` com o payload completo do
  dashboard do módulo (distribuições, top riscos, sem tratamento, aceitos, residual pendente, por ativo/
  dono, inerente×residual + heat map reusando a agregação da US1). Distinto do `GET /risk/matrix` (US1).
- [X] T048 [US5] Adicionar `DashboardModuleId.risk` em `wtnapp/schemas/dashboard_schema.py` e
  `_risk_card(db, ctx)` (gated em `view_risk`, fail-open) em `wtnapp/services/dashboard_service.py`.
- [X] T049 [P] [US5] Frontend `wtnadmin/src/app/pages/risk-dashboard/` (heat map + distribuições +
  inerente×residual) + rota + spec; e refletir o card de risco na home.

**Checkpoint**: visão gerencial do módulo + readiness na esteira.

---

## Phase 8: User Story 6 - Histórico, rastreabilidade e auditoria (Priority: P6)

**Goal**: expor o histórico append-only por risco (decisões com autor/data/valor anterior/novo/
justificativa) e garantir auditoria das operações sensíveis.

**Independent Test**: alterar prob/impacto/dono/tratamento/controle/aceitação/aprovação e confirmar
registros append-only com justificativa nas mudanças relevantes; tentar editar/apagar evento → bloqueado.

### Tests for User Story 6 (MANDATORY) ⚠️

- [X] T050 [P] [US6] Test em `wtnapp/test/test_risk_history.py`: `risk_events` append-only (UPDATE/DELETE
  bloqueados), justificativa obrigatória nas mudanças relevantes, ordem cronológica, isolamento.
- [X] T051 [P] [US6] Test de cobertura de auditoria em `wtnapp/test/test_risk_history.py`: operações
  sensíveis geram audit log sem PII/segredos; listagem simples não loga.

### Implementation for User Story 6

- [X] T052 [US6] Endpoint `GET /risk/risks/{id}/history` em `wtnapp/routers/risk.py` e revisão da
  exigência de `reason` nas mudanças relevantes nos serviços (risk/treatment/methodology).
- [X] T053 [US6] Frontend `pages/risk-detail/`: seção de histórico (linha do tempo) + atualizar
  `risk-detail.spec.ts`.

**Checkpoint**: rastreabilidade completa das decisões de risco.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T054 [P] Adicionar a seção do **Módulo de Riscos (Feature 012 — implementada)** em `CLAUDE.md`
  (espelhando o padrão dos módulos anteriores).
- [X] T055 [P] Criar `scripts/seed_risk_demo.py` (cenário de demonstração E2E, padrão `seed_soa_demo.py`).
- [X] T056 **Audit review**: confirmar que toda operação sensível do `/risk` gera log e que nenhum
  log/erro/telemetria expõe PII/segredos/conteúdo confidencial.
- [X] T057 **Tenant isolation sweep**: revisar que nenhuma query nova do módulo escapou de `scoped_query`/
  filtro por `ctx.tenant_id`; confirmar RLS nas **10 tabelas tenant** e a exceção documentada das 2 sementes.
- [ ] T058 Validar `alembic upgrade head` + `alembic downgrade -1` no PostgreSQL real e rodar o roteiro
  do [quickstart.md](quickstart.md) no browser (metodologia, adoção, avaliação, tratamento, aprovação
  com/sem assinatura, heat map/dashboard, SoA-feed, placeholders do ativo).
- [X] T059 Rodar a suíte completa: `pytest wtnapp/test` (inclui isolamento de tenant) e `npm test` em
  `wtnadmin/`.
- [X] T060 [P] **FR-047 (prep de relatórios)** — confirmar que os modelos/serviços estruturam os dados
  para os relatórios futuros (Registro de Riscos, Matriz/Heat map, Plano de Tratamento, Riscos Aceitos,
  Riscos Residuais Pendentes) sem implementar PDF/assinatura agora (apenas a assinatura opcional do plano).
  Sem build — task de rastreabilidade/checagem.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA** todas as user stories (modelos, migration,
  metodologia-default, semente/adoção, router skeleton).
- **US1 (Phase 3)**: depende da Foundational. É o MVP.
- **US2 (Phase 4)**: depende da Foundational; complementa US1 (catálogo já adotável na Foundational).
- **US3 (Phase 5)**: depende da Foundational + **US1** (precisa de riscos avaliados).
- **US4 (Phase 6)**: depende da Foundational; afeta US1 (recálculo). Independente de US2/US3.
- **US5 (Phase 7)**: depende da Foundational + **US1** (riscos) e idealmente **US3** (residual).
- **US6 (Phase 8)**: depende da Foundational; os eventos são escritos por US1/US3/US4 — US6 os expõe.
- **Polish (Phase 9)**: depende das stories desejadas.

### Within Each User Story

- Testes (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação.
- Models → services → endpoints → frontend; core antes de integração.
- Story completa antes da próxima prioridade (para entrega incremental).

### Parallel Opportunities

- **Setup**: T002 e T003 em paralelo (T001 primeiro, pois enums são base).
- **Foundational**: T004, T005, T006 em paralelo (modelos em arquivos distintos); T007/T008 depois; T011
  em paralelo com T009/T010.
- **Por story**: as tasks de teste `[P]` rodam juntas; o frontend `[P]` (telas) em paralelo ao backend
  da mesma story após os endpoints existirem.
- **Entre stories**: após a Foundational, US2 e US4 podem ser tocadas em paralelo a US1 por devs
  distintos (arquivos majoritariamente distintos); US3/US5 aguardam US1.

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 2 (Foundational — CRÍTICO) → Phase 3 (US1, incl. teste de isolamento).
2. **STOP e VALIDE**: avaliar riscos com o catálogo adotado e a metodologia default; conferir heat map.
3. Demo do Registro de Riscos (já entrega valor).

### Incremental Delivery

1. Foundational pronta → US1 (MVP) → US2 (catálogo/ativos) → US3 (tratamento/plano/SoA-feed) → US4
   (metodologia) → US5 (dashboard/esteira) → US6 (histórico).
2. Cada story agrega valor sem quebrar as anteriores; o teste de isolamento de tenant acompanha cada uma.

---

## Notes

- [P] = arquivos diferentes, sem dependências.
- **Teste de isolamento de tenant é obrigatório** por story de domínio (não é "polish").
- **Não** escrever na SoA (apenas `GET /risk/soa-feed`); **não** alterar o modelo de Ativos (só consumir
  os placeholders); **sem** exclusão física (arquivamento lógico justificado); histórico/plano append-only.
- Verifique que os testes falham antes de implementar; commit após cada task ou grupo lógico.
