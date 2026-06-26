---
description: "Task list — Gestão de Ativos / Processos / Escopo (Feature 011)"
---

# Tasks: Gestão de Ativos / Processos / Escopo do SGSI

**Input**: Design documents from `/specs/011-asset-process-scope/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml)

**Tests**: ⚠️ **OVERRIDE da constitution (White Tree Nexus):** testes NÃO são opcionais. Toda story
de domínio inclui, no mínimo, **teste de isolamento de tenant** + casos de falha principais.

**Organization**: Tasks agrupadas por user story (P1→P5) para implementação/teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: a qual user story a task pertence (US1…US5)
- Caminhos de arquivo exatos nas descrições

## Path Conventions (web monorepo)

- Backend: `wtnapp/` (models, schemas, routers, services, helpers, test)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)

---

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Adicionar enums e config em `wtnapp/settings.py`: `AssetType`, `CiaLevel`,
  `AssetScopeStatus`, `AssetRecordStatus`, `AssetRelationshipType`, `AssetReviewStatus` +
  `ASSET_CODE_PREFIXES` (mapa tipo→prefixo) + `ASSET_REVIEW_DUE_SOON_DAYS` (default 30 via `os.getenv`).
- [x] T002 [P] Backend RBAC: adicionar `view_asset` e `manage_asset` à matriz `PERMISSIONS` em
  `wtnapp/helpers/permissions.py` (Super Admin/Admin/Consultor: ambos; Gestor/Dono de processo/Dono de
  controle/Auditor interno/Cliente: `view_asset`; Colaborador convidado: nenhum).
- [x] T003 [P] Frontend: espelhar `view_asset`/`manage_asset` em `wtnadmin/src/app/core/permissions.ts`
  e declarar os tipos do módulo (enums + `AssetItem`/relacionamento/gap link/evento/summary) em
  `wtnadmin/src/app/core/models.ts`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: schema, modelos, contrato base e esqueleto de router/serviço que TODAS as stories usam.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase terminar.

- [x] T004 Criar `wtnapp/models/asset_item_model.py` com as 4 classes ORM (todas com `tenant_id`):
  `AssetItem`, `AssetRelationship`, `AssetGapLink`, `AssetItemEvent` (índices da data-model.md;
  triggers **append-only** em `AssetItemEvent` para SQLite e PostgreSQL no padrão de
  `gap_evidence_event` via `@event.listens_for(..., "after_create")`). Registrar em
  `wtnapp/models/__init__.py`.
- [x] T005 Criar migration `wtnapp/alembic/versions/b1c2d3e4f015_asset_process_scope_module.py`.
  **Pré-passo obrigatório**: confirmar o head real com `alembic heads` (ou `git log` das migrations) e
  usar esse valor como `down_revision` — o head esperado é `a6b7c8d9e014`, mas ele ainda está **não
  commitado** (trabalho de print templates); se tiver sido commitado/renomeado/revertido, ajustar
  `down_revision` para o head efetivamente presente. Conteúdo: 4 tabelas + índices + RLS (policy
  `tenant_isolation` por tabela) + triggers append-only em `asset_item_events`. **Idempotente**
  (`_table_exists`/`_index_exists`/`_fk_exists`; `DROP POLICY IF EXISTS`; `CREATE OR REPLACE`/
  `IF NOT EXISTS`). Conferir `alembic check` (sem múltiplos heads).
- [x] T006 [P] Criar `wtnapp/schemas/asset_schema.py` com o contrato base do item:
  `AssetItemCreate`, `AssetItemUpdate`, `AssetItemResponse` (incl. campos derivados:
  `review_status`, `criticality_computed`, `criticality_divergent`, `cia_complete`, `pending_fields`).
  ORM schemas com `class Config: from_attributes = True`.
- [x] T007 Criar `wtnapp/services/asset_service.py` (esqueleto + helpers puros): `generate_code`
  (prefixo+seq por tipo, retry em `IntegrityError`), `compute_criticality` (max baixa<media<alta<critica),
  `derive_review_status` (usa `ASSET_REVIEW_DUE_SOON_DAYS`), `build_response` (popula derivados).
- [x] T008 Criar `wtnapp/routers/assets.py` (esqueleto: `router = APIRouter(prefix="/assets")`,
  `view_dep`/`manage_dep` via `require_permission`, `db_dep`) e registrar em `wtnapp/main.py`
  (`app.include_router(assets.router)`).

**Checkpoint**: schema migrado, modelos/contrato/serviço/rota disponíveis — user stories podem começar.

---

## Phase 3: User Story 1 - Inventariar e classificar ativos e processos (Priority: P1) 🎯 MVP

**Goal**: cadastrar/editar/visualizar/listar(básico)/arquivar itens tipados, com classificação CIA +
criticidade (calculada/override) e situação de escopo com validações condicionais.

**Independent Test**: criar itens de tipos diferentes, classificar CIA, marcar escopo; confirmar
código único por tipo, validações (in_scope ⇒ responsável+CIA; out_of_scope ⇒ justificativa) e
arquivamento lógico com justificativa.

**Nota de escopo (incremental)**: no MVP (US1) as operações são auditadas via `AuditService`, mas a
**trilha de histórico por item** (`asset_item_events`) só é instrumentada na US4 (T028) — itens
criados antes da US4 não recebem evento `CREATE` retroativo. FR-023 é plenamente atendida ao concluir
a US4.

### Tests for User Story 1 (MANDATORY) ⚠️

> Escreva PRIMEIRO e garanta que FALHAM antes de implementar.

- [x] T009 [P] [US1] **Tenant isolation test**: usuário do tenant A não lê/edita/arquiva item do
  tenant B (404 + audit) em `wtnapp/test/test_tenant_isolation_assets.py`.
- [x] T010 [P] [US1] Happy path CRUD + geração de código (prefixo+seq por tipo, imutável) em
  `wtnapp/test/test_assets.py`.
- [x] T011 [P] [US1] Casos de falha em `wtnapp/test/test_assets.py`: validações condicionais
  (in_scope sem responsável/CIA; out_of_scope sem justificativa), criticidade calculada vs. override +
  divergência, duplicidade de nome no mesmo tipo, arquivamento sem justificativa,
  `related_system_id`/`related_process_id`/`related_supplier_id` apontando para item de outro tenant
  ⇒ rejeitado (404/422), permissão negada.

### Implementation for User Story 1

- [x] T012 [US1] Implementar regras de negócio em `wtnapp/services/asset_service.py`:
  `validate_scope` (in/out/under), `check_duplicate` (nome×tipo, `allow_duplicate`+`reason`),
  override de criticidade (`criticality_is_manual`), `archive_item` (exige `archive_reason`),
  validação de que `related_system_id`/`related_process_id`/`related_supplier_id` (quando informados)
  pertencem ao tenant ativo.
- [x] T013 [US1] Implementar endpoints em `wtnapp/routers/assets.py`: `POST /assets`, `GET /assets/{id}`,
  `PUT /assets/{id}`, `GET /assets` (lista básica, sem filtros) e `POST /assets/{id}/archive` —
  tenant-scoped + `require_permission` + `AuditService.log_from_request` nas mutações e negações.
- [x] T014 [P] [US1] Frontend `wtnadmin/src/app/pages/assets/` (lista + botão criar + form Reactive com
  `NonNullableFormBuilder`, `OnPush`, Signals; seletor de membros p/ responsável/dono/custodiante
  reusando o padrão de `form-assignments`; campos CIA + criticidade com aviso de divergência). Adicionar
  rota `assets` (`permissionGuard('view_asset')`) em `app.routes.ts` + link no `shell`.
- [x] T015 [P] [US1] Testes frontend em `wtnadmin/src/app/pages/assets/assets.spec.ts`.

**Checkpoint**: MVP — inventário classificável e escopável, com isolamento verificado.

---

## Phase 4: User Story 2 - Listagem com filtros, busca e dashboard (Priority: P2)

**Goal**: cards de resumo (KPIs), filtros, busca textual e dashboard simples do módulo.

**Independent Test**: com itens cadastrados, conferir que os cards refletem contagens corretas e que
cada filtro/busca retorna o subconjunto esperado, somente do tenant ativo.

### Tests for User Story 2 (MANDATORY) ⚠️

- [x] T016 [P] [US2] `wtnapp/test/test_asset_metrics.py`: KPIs (total/ativos/processos/fornecedores/
  in_scope/críticos/sem responsável/sem CIA) e distribuições do dashboard corretos e tenant-scoped.
- [x] T017 [P] [US2] Testes de filtros/busca em `wtnapp/test/test_assets.py` (tipo, escopo,
  criticidade, CIA, dados pessoais/sensíveis, sem responsável, CIA incompleta, gaps relacionados, `q`).

### Implementation for User Story 2

- [x] T018 [US2] Criar `wtnapp/services/asset_metrics_service.py`: `summary(db, ctx)` (KPIs) e
  `dashboard(db, ctx)` (distribuições por tipo/criticidade/escopo/revisão + dados pessoais + críticos
  sem revisão + sem responsável) com queries agregadas tenant-scoped.
- [x] T019 [US2] Em `wtnapp/routers/assets.py`: adicionar `GET /assets/summary`, `GET /assets/dashboard`
  e os query params de filtro/busca em `GET /assets` (ver contrato); schemas de resposta em
  `wtnapp/schemas/asset_schema.py`.
- [x] T020 [P] [US2] Frontend: cards de resumo + barra de filtros + busca textual na página
  `wtnadmin/src/app/pages/assets/`.
- [x] T021 [P] [US2] Frontend `wtnadmin/src/app/pages/assets-dashboard/` (distribuições + pendências) +
  rota `assets-dashboard` (`permissionGuard('view_asset')`) + link no `shell` + `assets-dashboard.spec.ts`.

**Checkpoint**: US1 + US2 funcionam independentemente.

---

## Phase 5: User Story 3 - Detalhe, relacionamentos e vínculo com gaps (Priority: P3)

**Goal**: tela de detalhe com relacionamentos entre itens, vínculo a gaps do catálogo da org e seções
placeholder para módulos futuros.

**Independent Test**: relacionar dois itens (direcional) e vincular um item a um gap; confirmar que o
relacionamento aparece no detalhe de ambos os itens e o gap na seção "Gaps relacionados".

### Tests for User Story 3 (MANDATORY) ⚠️

- [x] T022 [P] [US3] `wtnapp/test/test_asset_relationships.py`: criar/remover; self-relacionamento
  bloqueado; relacionamento cross-tenant bloqueado; duplicata bloqueada; isolamento de tenant.
- [x] T023 [P] [US3] `wtnapp/test/test_asset_gap_links.py`: vincular/desvincular gap do catálogo da org;
  gap de outro tenant negado; duplicidade de vínculo bloqueada; isolamento de tenant.

### Implementation for User Story 3

- [x] T024 [P] [US3] Schemas `RelationshipCreate/Response` e `GapLinkCreate/Response` em
  `wtnapp/schemas/asset_schema.py`.
- [x] T025 [US3] Endpoints em `wtnapp/routers/assets.py`: `POST/DELETE /assets/{id}/relationships[/{rel_id}]`
  e `POST/DELETE /assets/{id}/gap-links[/{link_id}]` (validações de self/cross-tenant/duplicata,
  `gap_catalog_item` do tenant), e enriquecer `GET /assets/{id}` com relacionamentos de saída/entrada e
  gaps vinculados — todos tenant-scoped + audit.
- [x] T026 [P] [US3] Frontend `wtnadmin/src/app/pages/asset-detail/` (dados gerais, CIA, escopo,
  responsáveis, relacionamentos saída/entrada, gaps relacionados, **placeholders** de ameaças/
  vulnerabilidades/riscos/controles/evidências) + rota `assets/:id` (`permissionGuard('view_asset')`) +
  `asset-detail.spec.ts`.

**Checkpoint**: US1–US3 funcionam independentemente; o detalhe mapeia o item no SGSI.

---

## Phase 6: User Story 4 - Histórico, rastreabilidade e revisão periódica (Priority: P4)

**Goal**: trilha append-only de alterações relevantes (com justificativa nas críticas) e situação de
revisão derivada/filtrável.

**Independent Test**: alterar escopo/criticidade/responsável e arquivar; confirmar eventos append-only
com autor/data/valor anterior/novo e justificativa nas críticas; definir datas e conferir
`review_status` derivado e filtrável.

### Tests for User Story 4 (MANDATORY) ⚠️

- [x] T027 [P] [US4] `wtnapp/test/test_asset_history.py`: eventos gerados por
  CREATE/UPDATE/SCOPE_CHANGE/CRITICALITY_CHANGE/RESPONSIBLE_CHANGE/ARCHIVE/RELATIONSHIP/GAP; append-only
  (UPDATE/DELETE abortam); justificativa obrigatória em SCOPE_EXCLUSION/CRITICALITY_CHANGE/ARCHIVE;
  `review_status` derivado (up_to_date/due_soon/overdue/undefined) e filtro por revisão.

### Implementation for User Story 4

- [x] T028 [US4] Em `wtnapp/services/asset_service.py`: `apply_changes_and_log` — diffing do estado
  anterior×novo e gravação de eventos em `asset_item_events` para todas as mutações (item,
  relacionamento, gap link), exigindo `reason` nas mudanças críticas.
- [x] T029 [US4] Em `wtnapp/routers/assets.py`: `GET /assets/{id}/history` (ordem cronológica,
  tenant-scoped) e filtro `review_status`/sem próxima revisão em `GET /assets`.
- [x] T030 [P] [US4] Frontend: seção de histórico + indicador de situação de revisão na página
  `asset-detail/` e filtro de revisão (vencida/sem próxima) na lista `assets/`.

**Checkpoint**: US1–US4 funcionam; rastreabilidade e revisão completas.

---

## Phase 7: User Story 5 - Criar item a partir da Análise de Contexto (Priority: P5)

**Goal**: acelerar o cadastro pré-preenchendo a partir de elementos da Análise de Contexto.

**Independent Test**: com Contexto preenchido, acionar "criar a partir do contexto", escolher um
elemento e confirmar o formulário pré-preenchido; sem Contexto, mensagem clara e cadastro manual segue.

### Tests for User Story 5 (MANDATORY) ⚠️

- [x] T031 [P] [US5] `wtnapp/test/test_assets.py` (ou arquivo dedicado): `GET /assets/context-sources`
  retorna apenas elementos de contexto do tenant ativo; isolamento de tenant; estado vazio sem Contexto.

### Implementation for User Story 5

- [x] T032 [US5] Endpoint `GET /assets/context-sources` em `wtnapp/routers/assets.py` (leitura
  somente: partes interessadas, issues de contexto e escopo preliminar dos modelos de Contexto 002) +
  `ContextSourceResponse` em `wtnapp/schemas/asset_schema.py`; gravar `context_origin_type`/
  `context_origin_id` quando o item for criado a partir de uma origem.
- [x] T033 [P] [US5] Frontend: ação "criar item a partir do contexto" na página `assets/` que carrega
  as fontes e pré-preenche o formulário de novo item (campos compatíveis: nome/área/descrição).

**Checkpoint**: todas as user stories funcionando.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [x] T034 [P] Atualizar `CLAUDE.md` (seção do módulo, marcar como implementada) e docs relevantes.
- [x] T035 **Audit review**: confirmar que toda mutação (item/relacionamento/gap link/arquivamento) e
  toda negação geram audit log e que nenhum log/erro/telemetria expõe PII ou observações sensíveis.
- [x] T036 **Tenant isolation sweep**: revisar que toda query nova passa por `tenant_id`/`scoped_query`
  e que relacionamentos/links nunca cruzam tenant.
- [ ] T037 Rodar `quickstart.md` (E2E Postgres real) + suíte completa (`pytest wtnapp/test` e
  `npm test` em `wtnadmin/`); validar `alembic upgrade head`/`downgrade`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências.
- **Foundational (Phase 2)**: depende do Setup — **BLOQUEIA** todas as user stories.
- **US1 (Phase 3)**: depende da Foundational. MVP.
- **US2 (Phase 4)**: depende da Foundational; usa itens criados pela US1 para dados reais (mas
  testável com seed próprio).
- **US3 (Phase 5)**: depende da Foundational; usa itens da US1.
- **US4 (Phase 6)**: depende da Foundational; o event-logging instrumenta as mutações de US1/US3
  (additivo — não quebra as stories anteriores).
- **US5 (Phase 7)**: depende da Foundational + Contexto (002) já presente.
- **Polish (Phase 8)**: depende das stories desejadas.

### Within Each User Story

- Testes (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação.
- Schemas/models → services → endpoints → frontend.
- Story completa antes da próxima prioridade.

### Parallel Opportunities

- Setup: T002 e T003 em paralelo.
- Foundational: T006 em paralelo com T007 (arquivos distintos); T004→T005 sequenciais (modelo antes da
  migration); T008 após T006/T007.
- Em cada story, as tasks de teste `[P]` rodam juntas; backend e frontend `[P]` podem ser tocados por
  devs diferentes após os endpoints.
- Após a Foundational, US1→US5 podem ser distribuídas entre devs (respeitando que US4 instrumenta US1/US3).

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → 2. Phase 2 (Foundational, CRITICAL) → 3. Phase 3 (US1, incl. isolamento) →
4. **STOP e VALIDE** US1 isolada → 5. demo (inventário classificável já entrega valor).

### Incremental Delivery

Setup+Foundational → US1 (MVP) → US2 (gestão/visão) → US3 (mapa/gaps) → US4 (rastreabilidade/revisão)
→ US5 (acelerador de contexto) → Polish. Cada story agrega valor sem quebrar as anteriores.

---

## Notes

- [P] = arquivos diferentes, sem dependências.
- [Story] mapeia task → user story (rastreabilidade).
- **Teste de isolamento de tenant é obrigatório** (US1 cobre itens; US3 cobre relacionamentos/gap links).
- Verifique que os testes falham antes de implementar.
- Migration única `b1c2d3e4f015` cria as 4 tabelas. Encadeia no head `a6b7c8d9e014`, que ainda está
  **não commitado**: commitar o trabalho de print templates **antes** (ou junto, na ordem correta)
  para não quebrar a cadeia; validar com `alembic heads` que existe **um único head** antes de
  implementar T005.
- Sem novas dependências; sem cifragem de campo; o módulo Gap **não** é alterado.
