---
description: "Task list — Feature 007: Orientação de Avaliação por Item (Gap Analysis)"
---

# Tasks: Orientação de Avaliação por Item (Gap Analysis)

**Input**: Design em `/specs/007-gap-item-guidance/` ([plan](plan.md), [spec](spec.md),
[research](research.md), [data-model](data-model.md), [contracts](contracts/openapi.yaml),
[quickstart](quickstart.md))

**Tests**: ⚠️ Obrigatórios (constitution Princípio VI) — inclui **teste de RBAC/isolamento** + casos
de falha. Escritos antes da implementação dentro de cada story.

**Organization**: por user story (US1 = MVP read; US2 = edição admin; US3 = legenda). **Tem migration**
(colunas no seed + 2 tabelas de plataforma). Conteúdo = autoria PT-BR **original** (IP: sem reproduzir
texto normativo ISO).

## Path Conventions
- Backend: `wtnapp/` · Frontend: `wtnadmin/src/app/`

---

## Phase 1: Setup

- [X] T001 Confirmar branch `007-gap-item-guidance` e os reaproveitamentos: `gap_seed_item.objective`
  já existe e é autorado; `gap_catalog_item.seed_item_id` já existe (vínculo p/ leitura por join).
  Revisar Structure Decision em [plan.md](plan.md).
- [X] T002 [P] Revisar pontos de reuso: `gap_seed_service.load_seed`/`adopt_seed`
  (`wtnapp/services/gap_seed_service.py`), padrão de trigger append-only
  (`wtnapp/models/document_version_model.py` e `gap_assessment_model.py`), `require_super_admin`
  (`wtnapp/helpers/permissions.py`), e o item response da matriz (`wtnapp/routers/gap_assessment.py`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: scaffolding compartilhado por todas as stories. Nenhuma user story começa antes.

- [X] T003 Adicionar colunas de orientação a `GapSeedItem` em `wtnapp/models/gap_seed_model.py`:
  `referencia` (String 120, default ""), `como_avaliar` (JSON, default list), `evidencias_esperadas`
  (JSON, default list), `nota` (Text, nullable). (`objetivo` reaproveita o `objective` existente.)
- [X] T004 [P] Criar modelo `GapLegendEntry` em `wtnapp/models/gap_legend_model.py` (platform, **sem
  `tenant_id`**): `kind` (status|priority), `code`, `label`, `definition`, `order`; único por (kind,code).
- [X] T005 [P] Criar modelo `GapGuidanceEvent` (append-only, platform, **sem `tenant_id`**) em
  `wtnapp/models/gap_guidance_event_model.py`: `target_type`, `target_id`, `field`, `old_value`,
  `new_value`, `actor_id`, `created_at` + **triggers** bloqueando UPDATE/DELETE (SQLite
  `IF NOT EXISTS`; PG função+trigger idempotentes), no padrão de `document_versions`.
- [X] T006 [P] Criar DTOs em `wtnapp/schemas/gap_guidance_schema.py`: `ItemGuidance`, `LegendEntry`,
  `Legend`, `GuidanceResponse`, `ItemGuidanceUpdate`, `LegendEntryUpdate`, `GuidanceEvent`
  (conforme [data-model.md](data-model.md)).
- [X] T007 Criar migration `wtnapp/alembic/versions/<rev>_gap_guidance.py` com
  `down_revision="f8a9b0c1d207"`: `add_column` guardado (x4 em `gap_seed_item`), `create_table`
  guardado (`gap_legend_entry`, `gap_guidance_event`), triggers idempotentes. **Sem RLS** (tabelas de
  plataforma). **Idempotente** (rodar 2× sem erro).
- [X] T008 **Legenda (conteúdo + seed)** em `wtnapp/data/iso27001_seed.py` + `wtnapp/services/
  gap_seed_service.py`: (a) autorar as **8 definições** da legenda — **4 Status** (`meets`/`partial`/
  `not_meet`/`not_applicable`; **exclui `not_filled`**) e **4 Prioridade** (`critical`/`high`/`medium`/
  `low`), PT-BR **original**, em `iso27001_seed.py`; (b) `load_seed` **semeia `gap_legend_entry`**
  idempotentemente (por `kind`+`code`); (c) `load_seed` preenche os campos de orientação do seed
  **somente quando vazios** — **nunca sobrescreve** valor não-vazio (preserva edição do admin).
  Versão segue 2022.1.

**Checkpoint**: schema + legenda prontos; endpoint pode ser construído.

---

## Phase 3: User Story 1 — Avaliar item com orientação ao lado (P1) 🎯 MVP

**Goal**: ao selecionar um item na matriz, o avaliador vê a orientação (referência, objetivo, como
avaliar, evidências esperadas, nota) em somente leitura.

**Independent Test**: org com catálogo adotado ⇒ `GET /gap/guidance` devolve a orientação resolvida
por `seed_item_id`; o painel da matriz exibe os campos; item sem orientação ⇒ "sem orientação
disponível".

### Tests for User Story 1 (MANDATORY) ⚠️
- [X] T009 [P] [US1] Teste de leitura em `wtnapp/test/test_gap_guidance.py`: `GET /gap/guidance`
  devolve `items` (orientação do seed) + `legend`; item adotado resolve via `seed_item_id`; item sem
  orientação volta com listas vazias / `nota` nula.
- [X] T010 [P] [US1] Teste de RBAC de leitura em `wtnapp/test/test_gap_guidance.py`: usuário sem
  `view_gap` ⇒ 403.

### Implementation for User Story 1
- [X] T011 [US1] Implementar `get_guidance(db)` em `wtnapp/services/gap_guidance_service.py` (itens do
  seed corrente + legenda, no formato `GuidanceResponse`).
- [X] T012 [US1] Criar `wtnapp/routers/gap_guidance.py` com `GET /gap/guidance`
  (`require_permission("view_gap")`) e **registrar em `wtnapp/main.py`**.
- [X] T013 [US1] **Conteúdo** — autorar `referencia`/`como_avaliar`/`evidencias_esperadas`/`nota`
  (PT-BR **original**) das **7 cláusulas (4–10)** em `wtnapp/data/iso27001_seed.py`.
- [X] T014 [US1] **Conteúdo** — Anexo A **A.5 Organizacional (37 controles)** em
  `wtnapp/data/iso27001_seed.py`.
- [X] T015 [US1] **Conteúdo** — Anexo A **A.6 Pessoas (8)** + **A.7 Físico (14)** em
  `wtnapp/data/iso27001_seed.py`.
- [X] T016 [US1] **Conteúdo** — Anexo A **A.8 Tecnológico (34)** em `wtnapp/data/iso27001_seed.py`.
- [X] T017 [P] [US1] Frontend: em `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`, buscar
  `GET /gap/guidance` e renderizar, no painel lateral, a seção **"Orientação de avaliação"**
  (somente leitura: referência, objetivo, `como_avaliar` em bullets, `evidencias_esperadas` em
  bullets, nota); mapear por `ref_code`; "sem orientação disponível" quando ausente; **reservar
  espaço** para a futura seção de Evidências (FR-010). **Rotular distintamente (FR-009)**: a
  orientação é "Evidências esperadas"; o campo da org (`evidence_ref`, já na matriz) é "Evidência
  existente" — não confundir os dois.
- [X] T018 [P] [US1] Frontend: atualizar `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`
  para mockar `/gap/guidance` e validar render da orientação + estado "sem orientação".

**Checkpoint**: matriz exibe orientação; conteúdo dos 100 itens disponível; leitura gated por `view_gap`.

---

## Phase 4: User Story 2 — Administrar (editar) a orientação (P2)

**Goal**: Super Admin edita orientação/legenda numa área administrativa; cada edição vai para trilha
append-only + audit e reflete em todas as orgs.

**Independent Test**: autenticado como Super Admin, editar um campo ⇒ persiste, registra antes→depois,
reflete na leitura de qualquer org; não-Super-Admin ⇒ 403.

### Tests for User Story 2 (MANDATORY) ⚠️
- [X] T019 [P] [US2] `wtnapp/test/test_gap_guidance.py`: Super Admin edita campo de item ⇒ persistido;
  `gap_guidance_event` registra `old→new`; audit gerado; nova leitura reflete; **propagação** (edição
  vista por leitura de outra org).
- [X] T020 [P] [US2] **Teste de RBAC/isolamento** em `wtnapp/test/test_gap_guidance_rbac.py`:
  não-Super-Admin (incl. Admin de org) em `PUT /gap/guidance/items/{id}` e `.../legend/{id}` ⇒ **403**
  + audit; nenhum endpoint da feature expõe/altera dado de avaliação de organização.
- [X] T021 [P] [US2] `wtnapp/test/test_gap_guidance.py`: rodar `load_seed` após edição **não**
  sobrescreve; UPDATE/DELETE em `gap_guidance_event` falha (append-only).

### Implementation for User Story 2
- [X] T022 [US2] Implementar `update_item_guidance(db, seed_item_id, patch, actor)` e
  `update_legend(db, entry_id, patch, actor)` em `wtnapp/services/gap_guidance_service.py`: diff por
  campo → grava `gap_guidance_event` + `AuditService.log_from_request`.
- [X] T023 [US2] Adicionar em `wtnapp/routers/gap_guidance.py`: `PUT /gap/guidance/items/{seed_item_id}`,
  `PUT /gap/guidance/legend/{entry_id}` e `GET /gap/guidance/events` — todos `require_super_admin`.
- [X] T024 [P] [US2] Frontend: criar `wtnadmin/src/app/pages/gap-guidance-admin/gap-guidance-admin.ts`
  (área admin) para editar orientação dos itens + legenda via `api.put`; registrar rota em
  `wtnadmin/src/app/app.routes.ts` com **guard de Super Admin**.
- [X] T025 [P] [US2] Frontend: `wtnadmin/src/app/pages/gap-guidance-admin/gap-guidance-admin.spec.ts`
  (render + chamada do PUT correto).

**Checkpoint**: curadoria de conteúdo funcional, auditada e rastreável; propaga a todas as orgs.

---

## Phase 5: User Story 3 — Legenda global de Status/Prioridade (P3)

**Goal**: o avaliador consulta a legenda das escalas na tela do Gap.

**Independent Test**: abrir a tela do Gap e ver as 4 definições de Status + 4 de Prioridade.

### Tests for User Story 3 (MANDATORY) ⚠️
- [X] T026 [P] [US3] `wtnapp/test/test_gap_guidance.py`: a `legend` de `GET /gap/guidance` traz **4**
  entradas `status` + **4** `priority` (semeadas no T008), com `label` e `definition`.

### Implementation for User Story 3

> A autoria das definições da legenda foi movida para **T008 (Foundational)**; US3 cobre apenas a
> exibição na tela.

- [X] T027 [US3] Frontend: exibir a **legenda** (status + prioridade) em
  `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts` (painel recolhível/ajuda), consumindo a
  `legend` de `GET /gap/guidance`.
- [X] T028 [P] [US3] Frontend: spec do render da legenda em
  `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts` (4 status + 4 prioridade).

**Checkpoint**: US1, US2 e US3 funcionam independentemente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Atualizar status da Feature 007 em `CLAUDE.md` (planejada → implementada, com contagem
  de testes) + seção do módulo.
- [X] T030 **Audit review**: confirmar que edições (item/legenda) e tentativas negadas são auditadas,
  sem PII/segredos nos eventos/audit; leitura não loga.
- [X] T031 **Revisão de IP do conteúdo**: confirmar que os 100 itens têm orientação **original** em
  PT-BR — nenhuma reprodução de texto normativo da ISO/IEC 27001/27002 (FR-011).
- [X] T032 Rodar validação do [quickstart.md](quickstart.md): `pytest wtnapp/test/test_gap_guidance.py
  wtnapp/test/test_gap_guidance_rbac.py` + `cd wtnadmin && npm test` + `alembic upgrade head` 2× no
  Postgres real (idempotência).

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (P1)**: sem dependências.
- **Foundational (P2)**: depende do Setup — **BLOQUEIA** todas as stories (modelos + migration + DTOs
  + legenda semeada + load_seed fill-when-empty).
- **US1 (P3)**: depende da Foundational. MVP (read + conteúdo).
- **US2 (P4)**: depende da Foundational + estende o service/router criados na US1 (mesmos arquivos →
  sequencial nesses arquivos).
- **US3 (P5)**: depende da Foundational (legenda semeada) e do endpoint de leitura (US1); aditiva.
- **Polish (P6)**: depende das stories entregues.

### Within Each User Story
- Testes (incl. **RBAC/isolamento** em US2) escritos e FALHANDO antes da implementação.
- **Conteúdo** edita `iso27001_seed.py` em vários pontos (T008 legenda, depois T013–T016 itens) →
  **sequencial** entre si no mesmo arquivo.
- Frontend (T017/T018, T024/T025, T027/T028) em paralelo ao backend da mesma story (arquivos diferentes).

### Parallel Opportunities
- **Foundational**: T004, T005, T006 em paralelo (arquivos diferentes); T003 e T007/T008 à parte.
- **US1**: T009/T010 (testes) em paralelo; frontend (T017/T018) em paralelo aos card builders/serviço.
- **US2**: T019/T020/T021 (testes) em paralelo; frontend (T024/T025) em paralelo ao backend.

---

## Implementation Strategy

### MVP First (User Story 1)
1. Setup → Foundational → US1 (mecanismo de leitura + conteúdo dos 100 itens + painel).
2. **STOP e VALIDE**: `pytest` + `npm test`; ver a orientação na matriz (Postgres).
3. Demo (MVP — o avaliador já tem orientação por item).

### Incremental Delivery
1. Foundational → endpoint/legenda no ar.
2. US1 (read + conteúdo) → testa → demo (MVP).
3. US2 (curadoria admin) → testa → demo.
4. US3 (legenda na tela) → testa.
5. Polish (docs + revisões de audit/IP + validação do quickstart).

---

## Notes
- **IP**: todo conteúdo é autoral PT-BR; proibido reproduzir texto normativo ISO (T031 verifica).
- **Seed seguro**: `load_seed` preenche orientação só quando vazia — nunca reverte edição do admin.
- **Platform-level**: orientação/legenda/trilha sem `tenant_id` (exceção já aprovada na Feature 004);
  sem RLS. Edição só Super Admin; leitura `view_gap`.
- Teste de RBAC/isolamento (T020) é **obrigatório** (não é polish).
- Commit após cada task ou grupo lógico.
