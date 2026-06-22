# Implementation Plan: Orientação de Avaliação por Item (Gap Analysis)

**Branch**: `007-gap-item-guidance` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-gap-item-guidance/spec.md`

## Summary

Enriquecer cada item da matriz do Gap Analysis com **orientação de avaliação** (referência,
objetivo, como avaliar, evidências esperadas, nota) e exibir uma **legenda global** de Status e
Prioridade. A orientação é **conteúdo de plataforma compartilhado** (no catálogo-base do Gap, sem
`tenant_id`), exibida em **somente leitura** na matriz da organização (resolvida pelo vínculo
`gap_catalog_item.seed_item_id → gap_seed_item`, que **já existe**) e **editável apenas pelo Super
Admin da plataforma**, com **trilha append-only** + auditoria. Conteúdo PT-BR **original** dos 100
itens (93 controles + 7 cláusulas) — sem reproduzir texto normativo (IP).

**Achados que reduzem o escopo:**
- `gap_seed_item` **já tem `objective`** e o seed (`data/iso27001_seed.py`) **já o autora** em PT-BR
  para todos os 100 itens. `objetivo` não é campo novo — só os demais campos de orientação.
- `gap_catalog_item` **já tem `seed_item_id`** (preenchido em `adopt_seed`) → leitura por join já é
  possível, sem backfill na maioria dos casos.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic · PrimeNG 21, Signals.
Nenhuma dependência nova.

**Storage**: PostgreSQL (Alembic + `create_all()` no startup). **Tem migration** (colunas no seed +
2 tabelas de plataforma).

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` + `wtnadmin/`)

**Tenant Isolation Strategy**: orientação/legenda/trilha são **conteúdo de plataforma** (sem
`tenant_id`), mesma natureza já adotada para o **catálogo-base do Gap** (Feature 004). Leitura em
contexto de org (gated por `view_gap`) devolve conteúdo compartilhado (sem dado de tenant). Edição é
operação de plataforma (`require_super_admin`, sem `X-Org-Context`). Os dados de avaliação por item
continuam escopados por tenant (Módulo 2) e **não** são tocados.

**Performance Goals**: leitura da orientação é 1 chamada por sessão de matriz (mapa por `ref_code`/
`seed_item_id`), consultas pequenas. Sem metas especiais.

**Constraints**: IP (texto original, sem reproduzir norma); `load_seed` **nunca sobrescreve**
orientação não-vazia (preserva edições do admin); migration idempotente.

**Scale/Scope**: 100 itens de orientação (conteúdo); 4 colunas novas no seed; 2 tabelas novas; 1
endpoint de leitura + 2 de edição admin; painel da matriz + legenda + área admin no front.

## Constitution Check

*GATE: passar antes da Phase 0; re-checar após a Phase 1.*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: leitura via `require_permission("view_gap")` (contexto de org)
  devolve **conteúdo de plataforma compartilhado** — sem expor dado de avaliação de nenhum tenant.
  Edição via `require_super_admin` (sem contexto de org). Tabelas de orientação/legenda/trilha são
  **platform-level sem `tenant_id`** — mesma exceção já justificada para o catálogo-base do Gap
  (ver Complexity Tracking). Avaliação por item permanece tenant-scoped (Módulo 2). Teste de
  RBAC/isolamento planejado.
- [x] **RBAC**: leitura `view_gap`; edição **Super Admin** (`require_super_admin`). Tentativa de
  edição por não-plataforma ⇒ 403 + audit.
- [x] **Auditoria**: edições de orientação/legenda chamam `AuditService.log_from_request`
  (ações do Super Admin especialmente logadas) + **trilha append-only** (antes→novo). Leitura não loga.
- [x] **Integridade/versionamento**: trilha de edição **append-only** (gatilho bloqueia UPDATE/DELETE,
  SQLite+PG), preserva autor/data/antes→novo. A orientação em si é mutável in-place (conteúdo de
  referência, não documento controlado) — rastreabilidade via trilha.
- [x] **Dados sensíveis**: orientação é texto de referência genérico; sem PII/segredos; sem cifragem.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; **novo router
  registrado em `main.py`**; lógica em `services/`; sem middleware novo.
- [x] Frontend: standalone; `inject()`; control flow nativo; `OnPush`; Signals.
- [x] Schema: modelo SQLAlchemy **+** migration Alembic idempotente; seed idempotente que **não**
  sobrescreve edições.

**Qualidade (Definition of Done):**

- [x] **Test-first**: leitura (matriz vê orientação via join), edição admin (Super Admin OK;
  não-plataforma 403+audit), trilha append-only (antes→novo), seed não sobrescreve edição,
  legenda, propagação (edição reflete a qualquer org) e **teste de RBAC/isolamento**.
- [x] Mensagens de erro não vazam internals.

**Resultado do gate**: ✅ PASS — uma entrada em Complexity Tracking (tabelas platform-level sem
`tenant_id`), a **mesma exceção já aprovada** na Feature 004 para o catálogo-base do Gap.

## Project Structure

### Documentation (this feature)

```text
specs/007-gap-item-guidance/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/openapi.yaml
└── checklists/requirements.md
```

### Source Code (repository root)

```text
wtnapp/
├── models/gap_seed_model.py          # EDITADO — +referencia, +como_avaliar(JSON), +evidencias_esperadas(JSON), +nota
├── models/gap_legend_model.py        # NOVO — GapLegendEntry (platform; status/prioridade)
├── models/gap_guidance_event_model.py# NOVO — trilha append-only (platform) + triggers
├── data/iso27001_seed.py             # EDITADO — orientação PT-BR (referencia/como_avaliar/evidencias_esperadas/nota) dos 100 itens + legenda
├── services/gap_seed_service.py      # EDITADO — load_seed preenche orientação SÓ quando vazia (preserva edição); seed da legenda
├── services/gap_guidance_service.py  # NOVO — leitura agregada (itens+legenda) e edição com trilha+audit
├── schemas/gap_guidance_schema.py    # NOVO — DTOs (Guidance, LegendEntry, edição)
├── routers/gap_guidance.py           # NOVO — GET /gap/guidance (view_gap) + edição admin (require_super_admin)
├── main.py                           # EDITADO — include_router(gap_guidance.router)
├── alembic/versions/<rev>_gap_guidance.py  # NOVO — colunas + 2 tabelas + triggers (idempotente)
└── test/
    ├── test_gap_guidance.py              # NOVO — leitura, edição admin, trilha, legenda, propagação
    └── test_gap_guidance_rbac.py         # NOVO — não-plataforma 403+audit; sem vazamento de avaliação

wtnadmin/src/app/
├── pages/gap-analysis/gap-analysis.ts        # EDITADO — seção "Orientação" (read-only) no painel + busca /gap/guidance
├── pages/gap-analysis/gap-analysis.spec.ts   # EDITADO — render da orientação
├── pages/gap-guidance-admin/gap-guidance-admin.ts      # NOVO — área admin (Super Admin): editar orientação + legenda
├── pages/gap-guidance-admin/gap-guidance-admin.spec.ts # NOVO
├── core/api.service.ts               # (reusa get/put genéricos)
└── app.routes.ts                     # EDITADO — rota admin guardada (Super Admin)
```

**Structure Decision**: monorepo. Backend ganha 2 modelos + 1 service + 1 schema + 1 router (+ edição
do seed/model/migration). Frontend ganha a seção de orientação na matriz, a legenda e a área admin.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tabelas de orientação/legenda/trilha **sem `tenant_id`** (platform-level) | A orientação é **conteúdo canônico único** da plataforma (igual para todas as orgs) e deve propagar com 1 edição; mesma natureza do catálogo-base do Gap (`gap_seed_item`, sem tenant_id) | Pôr `tenant_id` exigiria duplicar ~100×N blocos por org e quebraria a propagação (FR-005/SC-003). Exceção **já aprovada** na Feature 004 para o seed do Gap. |
