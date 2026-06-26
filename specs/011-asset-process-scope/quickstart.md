# Quickstart — Gestão de Ativos / Processos / Escopo (Feature 011)

Guia rápido para implementar e validar o Módulo 3. Pressupõe a fundação multi-tenant, Gap Analysis
(004) e Contexto (002) já presentes. **Nada do módulo Gap é alterado.**

## 1. Backend — ordem de implementação (test-first)

1. **`settings.py`**: adicionar enums (`AssetType`, `CiaLevel`, `AssetScopeStatus`, `AssetRecordStatus`,
   `AssetRelationshipType`, `AssetReviewStatus`) + `ASSET_CODE_PREFIXES` + `ASSET_REVIEW_DUE_SOON_DAYS`.
2. **`models/asset_item_model.py`**: `AssetItem`, `AssetRelationship`, `AssetGapLink`, `AssetItemEvent`
   (todas com `tenant_id`). Triggers append-only em `AssetItemEvent` (SQLite + PG) no padrão de
   `gap_evidence_event` (`@event.listens_for(..., "after_create")`). Registrar em `models/__init__.py`.
3. **`schemas/asset_schema.py`**: `AssetItemCreate/Update/Response`, `RelationshipCreate/Response`,
   `GapLinkCreate/Response`, `EventResponse`, `SummaryResponse`, `DashboardResponse`,
   `ContextSourceResponse`. ORM schemas com `class Config: from_attributes = True`.
4. **`services/asset_service.py`**:
   - `generate_code(db, ctx, item_type)` → prefixo + seq por tipo (retry em `IntegrityError`).
   - `compute_criticality(c, i, a)` → `max` na ordem `baixa<media<alta<critica`.
   - `derive_review_status(next_review_at)` → enum derivado (usa `ASSET_REVIEW_DUE_SOON_DAYS`).
   - `validate_scope(payload)` → regras condicionais (in/out/under).
   - `apply_changes_and_log(db, item, payload, actor)` → diff + eventos (exige `reason` em
     SCOPE_EXCLUSION/CRITICALITY_CHANGE/ARCHIVE).
   - `check_duplicate(db, ctx, name, item_type, allow_duplicate)`.
5. **`services/asset_metrics_service.py`**: `summary(db, ctx)` (KPIs) e `dashboard(db, ctx)`
   (distribuições) com queries agregadas tenant-scoped.
6. **`routers/assets.py`** (prefix `/assets`): endpoints do `contracts/openapi.yaml`. `view_dep` /
   `manage_dep` via `require_permission`. `AuditService.log_from_request` em todas as mutações e
   negações. Registrar em **`main.py`**.
7. **`helpers/permissions.py`**: adicionar `view_asset` e `manage_asset` à matriz `PERMISSIONS`
   (Super Admin/Admin/Consultor: ambos; Gestor/Dono de processo/Dono de controle/Auditor/Cliente:
   `view_asset`; Convidado: nenhum).
8. **Migration** `alembic/versions/b1c2d3e4f015_asset_process_scope_module.py`
   (`down_revision="a6b7c8d9e014"`): 4 tabelas + índices + RLS + triggers append-only, **idempotente**
   (helpers `_table_exists`/`_index_exists`/`_fk_exists`; `DROP POLICY IF EXISTS`; `CREATE OR REPLACE`).

## 2. Frontend — Angular 21

1. `core/permissions.ts`: espelhar `view_asset` / `manage_asset`.
2. `core/models.ts`: tipos do módulo (enums + `AssetItem` + relacionamento/gap link/evento/summary).
3. `pages/assets/`: lista com cards de resumo, filtros, busca, botão criar (dialog/form Reactive com
   `NonNullableFormBuilder`); seletor de membros para responsável/dono/custodiante (reusar padrão de
   `form-assignments`). `OnPush` + Signals.
4. `pages/asset-detail/`: dados gerais, CIA + criticidade (com aviso de divergência), escopo +
   pendências, responsáveis, relacionamentos (saída/entrada), gaps relacionados, **placeholders** para
   ameaças/vulnerabilidades/riscos/controles/evidências, histórico, situação de revisão.
5. `pages/assets-dashboard/`: distribuições por tipo/criticidade/escopo/revisão + pendências.
6. `app.routes.ts`: `assets`, `assets/:id`, `assets-dashboard` com `permissionGuard('view_asset')`;
   adicionar links no `shell`.

## 3. Testes (obrigatórios antes de "pronto")

Backend (`pytest wtnapp/test`):
- `test_assets.py` — CRUD, geração de código (prefixo+seq por tipo, imutável), validações condicionais
  (in/out/under), criticidade calculada/override+divergência, duplicidade, arquivamento c/ justificativa.
- `test_asset_relationships.py` — criar/remover; self-relacionamento e cross-tenant bloqueados; duplicata.
- `test_asset_gap_links.py` — vincular/desvincular gap do catálogo da org; gap de outro tenant negado.
- `test_asset_history.py` — append-only (UPDATE/DELETE abortam), justificativa obrigatória, revisão derivada.
- `test_asset_metrics.py` — KPIs e distribuições corretos.
- `test_tenant_isolation_assets.py` — **OBRIGATÓRIO**: item/relacionamento/gap link/histórico de outra
  org ⇒ 404 + audit; consultor multi-org vê só o contexto ativo.

Frontend (`npm test` em `wtnadmin/`): `assets.spec.ts`, `asset-detail.spec.ts`, `assets-dashboard.spec.ts`.

## 4. Validação manual (E2E, Postgres real)

1. `alembic upgrade head` (encadeia em `a6b7c8d9e014`); subir backend :8000 + frontend :4200.
2. Criar itens de tipos variados → conferir código por tipo (ATV-0001, PROC-0001...).
3. Marcar `in_scope` sem responsável/CIA → bloqueio; `out_of_scope` sem justificativa → bloqueio.
4. Override de criticidade → flag de ajuste + divergência ao mudar CIA depois.
5. Relacionar dois itens; vincular item a um gap → aparece no detalhe.
6. Arquivar sem justificativa → bloqueio; com justificativa → arquivado + evento no histórico.
7. Conferir cards/filtros/busca e dashboard; "criar a partir do contexto" pré-preenche.
8. Isolamento: tentar acessar item de outra org ⇒ 404.

## Definition of Done (constitution)

Implementa a spec; testes happy/falha/**isolamento**; audit nas mutações; sem PII em logs/erros;
router em `main.py` + rotas no frontend; migration idempotente; spec atualizada se divergir.
