# Implementation Plan: Gestão de Ativos / Processos / Escopo do SGSI

**Branch**: `011-asset-process-scope` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/011-asset-process-scope/spec.md`

## Summary

Módulo 3 do MVP: um inventário classificado de **ativos, processos e elementos de escopo** do SGSI
que serve de base para os próximos módulos (ameaças, vulnerabilidades, riscos, plano de tratamento,
SoA definitivo, evidências). A feature adiciona um domínio novo, tenant-scoped, com: cadastro/edição/
arquivamento lógico de itens tipados; classificação CIA + criticidade (calculada do maior valor entre
C/I/A, com ajuste manual registrado); situação de escopo (dentro/fora/em análise) com validações
condicionais; relacionamentos flexíveis entre itens; vínculo a gaps do catálogo da própria org;
ação "criar item a partir do contexto"; histórico append-only por item; revisão periódica derivada;
listagem com filtros/busca + cards de resumo + dashboard simples; e seções placeholder no detalhe
para os módulos futuros.

**Abordagem técnica**: segue exatamente o padrão dos módulos existentes (Gap/SoA): modelos ORM
síncronos com `tenant_id` + RLS no PostgreSQL e triggers append-only (SQLite+PG) na trilha de
histórico; routers com `require_permission` + `scoped_query` + `AuditService`; serviços para geração
de código, cálculo de criticidade, derivação de revisão e diffing de histórico; frontend Angular 21
standalone (Signals/OnPush) com páginas lazy-loaded (lista, detalhe, dashboard) e `permissionGuard`.
Sem cifragem de campo (decisão da clarificação 2026-06-26). Sem alterar o módulo Gap.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic · PrimeNG 21, Angular
Signals. **Sem novas dependências** (nem `reportlab`/cifragem — PDF e assinatura são deferidos).

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); SQLite in-memory nos testes.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed.

**Target Platform**: Web (API REST + SPA Angular).

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend).

**Tenant Isolation Strategy**: **shared-DB + `tenant_id` com enforcement central** em
`helpers/tenant_scope.py` (`get_org_context` + `scoped_query`) **e** RLS no PostgreSQL (policy
`tenant_isolation` por tabela, `app.tenant_id` via `set_config`). Igual a todos os módulos
existentes — sem novidade arquitetural. Isolamento sempre fail-closed.

**Performance Goals**: padrão web; inventário de PME (dezenas a poucas centenas de itens por org).
Listagem paginada e filtrável; KPIs/dashboard agregados em uma chamada cada. Sem metas especiais.

**Constraints**: sem cifragem de campo no MVP (clarificação) — proteção por RBAC + isolamento de
tenant + regra "sem PII bruta"; código interno imutável por tipo; não alterar o módulo Gap; sem
exclusão física (arquivamento lógico); histórico append-only.

**Scale/Scope**: 4 tabelas novas; 1 router novo (`/assets`); 2 permissões novas
(`view_asset`/`manage_asset`); ~3 telas (lista, detalhe, dashboard). Centenas de itens/org no MVP.

## Constitution Check

*GATE: passou antes da Phase 0; re-checado após a Phase 1 (sem mudanças).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: todas as 4 tabelas têm `tenant_id`; queries via `scoped_query`/
  filtro por `ctx.tenant_id`; RLS PG por tabela. Cross-tenant ⇒ 404 genérico + audit. Relacionamento
  só une itens do mesmo tenant (checado na app + RLS). Teste de isolamento dedicado obrigatório.
- [x] **RBAC**: endpoints usam `require_permission("view_asset")` / `require_permission("manage_asset")`.
  Permissões batem com SEC-002 (Super Admin/Admin/Consultor gerem; Gestor/Dono de processo/Dono de
  controle/Auditor/Cliente veem; Convidado não acessa).
- [x] **Auditoria**: criação, edição, mudança de escopo/criticidade/responsável, arquivamento,
  add/remove relacionamento, link/unlink de gap e negações chamam `AuditService.log_from_request()`.
  Sem PII/segredos nos campos. Listagem simples não loga.
- [x] **Integridade de evidências/artefatos**: o **histórico do item** (`asset_item_event`) é a
  trilha versionável (SEC-005), append-only via triggers (SQLite+PG), preservando autor/data/ação/
  valor anterior/novo. Arquivamento é lógico (não destrói histórico).
- [x] **Dados sensíveis**: **cifragem em repouso N/A por design** (clarificação 2026-06-26 / SEC-004):
  o módulo guarda indicadores e metadados de classificação, **não** o dado pessoal; observações de
  compliance proibidas de conter PII bruta; proteção por RBAC + tenant + não-exposição em logs/erros.
  O princípio V ("cifrado **quando aplicável**") é respeitado — não aplicável aqui, justificado na spec.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy **síncrono**; `get_db()` central; novo router
  `assets` registrado em `main.py`; config (prefixos de código, limiar de revisão) em `settings.py`
  via `load_dotenv()`; sem middleware novo.
- [x] Frontend: standalone (sem NgModules); `input()`/`output()`; `inject()`; control flow nativo;
  `OnPush`; Signals; Reactive Forms (`NonNullableFormBuilder`); generic `get/post/put/patch/delete`
  do `ApiService` (já existem).
- [x] Schema: modelo SQLAlchemy **+** migration Alembic idempotente (`down_revision="a6b7c8d9e014"`);
  todos os modelos de domínio com `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas (validações condicionais, duplicidade, arquivamento sem
  justificativa, append-only, cross-tenant em relacionamento) **e teste de isolamento de tenant**
  planejados antes da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant (404 genérico).

**Resultado**: ✅ Sem violações. **Complexity Tracking vazio.**

## Project Structure

### Documentation (this feature)

```text
specs/011-asset-process-scope/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── openapi.yaml     # Phase 1 output
├── checklists/
│   └── requirements.md  # (do /speckit-specify)
└── tasks.md             # Phase 2 (/speckit-tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
wtnapp/                              # Backend FastAPI
├── models/
│   ├── asset_item_model.py          # NOVO: AssetItem + AssetRelationship + AssetGapLink + AssetItemEvent
│   └── __init__.py                  # registrar os novos modelos
├── schemas/
│   └── asset_schema.py              # NOVO: Create/Update/Response + Relationship/GapLink/Event/Summary/Dashboard/ContextSource
├── routers/
│   └── assets.py                    # NOVO: /assets (CRUD, archive, history, relationships, gap-links, summary, dashboard, context-sources)
├── services/
│   ├── asset_service.py             # NOVO: geração de código, cálculo de criticidade, derivação de revisão, validações, diffing/eventos
│   └── asset_metrics_service.py     # NOVO: KPIs + distribuições do dashboard
├── helpers/permissions.py           # +view_asset / +manage_asset na matriz PERMISSIONS
├── settings.py                      # +enums (AssetType, CiaLevel, AssetScopeStatus, AssetRecordStatus, AssetRelationshipType, AssetReviewStatus) + ASSET_CODE_PREFIXES + ASSET_REVIEW_DUE_SOON_DAYS
├── main.py                          # app.include_router(assets.router)
├── alembic/versions/
│   └── b1c2d3e4f015_asset_process_scope_module.py  # NOVO (idempotente, RLS + triggers append-only)
└── test/
    ├── test_assets.py               # CRUD, código, validações, criticidade, arquivamento, duplicidade
    ├── test_asset_relationships.py  # relacionamentos (self/cross-tenant bloqueados)
    ├── test_asset_gap_links.py      # vínculo a gap do catálogo da org
    ├── test_asset_history.py        # append-only + justificativa + revisão derivada
    ├── test_asset_metrics.py        # KPIs + distribuições
    └── test_tenant_isolation_assets.py  # OBRIGATÓRIO

wtnadmin/src/app/
├── core/
│   ├── permissions.ts               # +view_asset / +manage_asset
│   └── models.ts                    # +tipos do módulo (AssetItem, enums, etc.)
├── pages/
│   ├── assets/                      # NOVO: lista + cards + filtros/busca + criar (+ .spec.ts)
│   ├── asset-detail/                # NOVO: detalhe (dados/CIA/escopo/responsáveis/relacionamentos/gaps/placeholders/histórico) (+ .spec.ts)
│   └── assets-dashboard/            # NOVO: distribuições + pendências (+ .spec.ts)
└── app.routes.ts                    # +rotas assets / assets/:id / assets-dashboard (permissionGuard('view_asset'))
                                     # shell: links do módulo
```

**Structure Decision**: Web monorepo. Domínio novo isolado em `asset_*` (backend) e `pages/assets*`
(frontend), espelhando o módulo Gap. Nenhum arquivo de outro módulo é alterado, exceto pontos de
registro padrão (`models/__init__.py`, `main.py`, `permissions.py`, `settings.py`, `app.routes.ts`,
`shell`, `core/permissions.ts`, `core/models.ts`).

## Complexity Tracking

> Sem violações de constitution — seção intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |
