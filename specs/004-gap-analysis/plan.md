# Implementation Plan: Gap Analysis ISO/IEC 27001:2022

**Branch**: `004-gap-analysis` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-gap-analysis/spec.md`

## Summary

Módulo de avaliação de aderência à ISO/IEC 27001:2022 em duas dimensões (Cláusulas 4–10 e os 93
controles do Anexo A), gerando indicadores, lista de lacunas e baseline versionada. **Módulo próprio**
(catálogo-seed + matriz + dashboards) que **reusa** os primitivos existentes: fundação multi-tenant
(`tenant_scope`+RLS, RBAC, auditoria), padrão de **Documento Controlado** (`controlled_document_service`
+ `document_versions`) para a baseline, e o **Motor de Workflow 003** (`FormAssignment`/`FormSignature`/
eventos/OTP/notificação) para a condução atribuível/assinável. Abordagem técnica: catálogo-base
**compartilhado pela plataforma** (sem `tenant_id`, somente leitura) + **cópia editável por organização**
materializada na adoção (opt-in versionado); avaliação como artefato único por org (1 vigente +
baselines como `DocumentVersion`); cálculo de aderência ponderado (Atende=100% / Parcial=50% / Não
atende=0%, excluindo N/A e Não preenchido).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, slowapi, Redis ·
PrimeNG 21, Angular Signals. Reusa `controlled_document_service`, `form_workflow_service`,
`signature_service`, `notification_service`, `audit_service`, `tenant_scope`, `permissions`.

**Storage**: PostgreSQL (Alembic + `create_all()` no startup). RLS nas tabelas por-tenant; catálogo-seed
é tabela **compartilhada** (sem `tenant_id`, sem RLS, somente leitura para a aplicação).

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed. Teste de
isolamento de tenant **obrigatório**.

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`)
+ **RLS** no PostgreSQL — idêntico ao restante da plataforma. **Exceção**: o catálogo-base
(`gap_seed_item`) é dado **da plataforma** (compartilhado, somente leitura); não carrega `tenant_id`
e é exposto apenas para leitura/cópia, nunca para escrita por organização.

**Performance Goals**: padrão de aplicação web. A matriz tem ~100 itens (7 cláusulas + 93 controles)
por organização — volume pequeno; sem requisitos especiais de latência/throughput.

**Constraints**: backward-compatible/aditivo; seed versionável sem perda; append-only para histórico
de itens e baselines (gatilho no banco). Cálculo de aderência determinístico e recomputável.

**Scale/Scope**: multi-tenant; ~100 itens de avaliação por org; 5 user stories; ~6–8 tabelas novas;
telas: matriz, dashboard, catálogo, baselines (+ reuso das telas de atribuição do 003).

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checado após a Phase 1 (design) — ver fim.*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: matriz, itens, cópia do catálogo, baselines e condução passam por
  `scoped_query`/`tenant_scope` + RLS; cross-tenant ⇒ 404/403 + audit. O catálogo-seed compartilhado
  é **somente leitura** (sem escrita por tenant) — não é vetor de vazamento.
- [x] **RBAC**: `require_permission(...)` em todo endpoint; novas permissões `view_gap`, `manage_gap`,
  `approve_gap_baseline`; condução reusa `assign_form`/`fill_form`/`sign_form` (SEC-002).
- [x] **Auditoria**: criar/editar item, marcar N/A, personalizar catálogo, adotar versão do seed,
  atribuir/assinar, congelar/aprovar baseline ⇒ `AuditService.log_from_request` (sem PII/conteúdo).
- [x] **Integridade/versionamento**: histórico de item append-only; baseline = `DocumentVersion`
  imutável (gatilho append-only já existente). (SEC-005)
- [x] **Dados sensíveis**: constatações/ações protegidas por isolamento + RBAC + classificação
  (Módulo 1); nunca em logs/erros. Sem field-encryption neste módulo (default aceito — Clarifications).

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novos routers em
  `main.py`; config em `settings.py`+`load_dotenv()`; sem middleware novo.
- [x] Frontend: standalone; `input()/output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms.
- [x] Schema: modelo SQLAlchemy **+** migration Alembic; modelos de domínio com `tenant_id` (exceto o
  seed compartilhado, justificado abaixo).

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path + falhas (N/A sem justificativa ⇒ 422; aprovar baseline sem revisão ⇒
  409) + **isolamento de tenant** planejados antes da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência cross-tenant.

> **Nota de exceção arquitetural (justificada, não é violação de isolamento):** o catálogo-base
> (`gap_seed_item`) é **dado da plataforma compartilhado** e por isso **não** carrega `tenant_id`.
> Isso NÃO enfraquece o isolamento: é somente leitura para as organizações; toda escrita/avaliação
> acontece na **cópia por org** (`gap_catalog_item`, com `tenant_id` + RLS). Análogo a uma tabela de
> referência/seed. Registrado em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-gap-analysis/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1 (openapi.yaml)
└── tasks.md             # Phase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
wtnapp/
├── models/
│   ├── gap_seed_model.py            # GapSeedItem (compartilhado) + GapSeedVersion
│   ├── gap_catalog_model.py         # GapCatalogItem (cópia editável por org)
│   ├── gap_assessment_model.py      # GapAssessment + GapAssessmentItem (+ histórico)
│   └── gap_assignment_model.py      # GapAssignment (condução; reusa eventos/assinatura do 003)
├── schemas/
│   ├── gap_catalog_schema.py
│   ├── gap_assessment_schema.py
│   └── gap_assignment_schema.py
├── routers/
│   ├── gap_catalog.py               # catálogo (seed read-only + cópia editável da org)
│   ├── gap_assessment.py            # matriz, itens, dashboard, lacunas, baseline
│   └── gap_assignment.py            # condução atribuível/assinável (reusa 003)
├── services/
│   ├── gap_seed_service.py          # provisão/adoção versionada do seed → cópia da org
│   └── gap_metrics_service.py       # cálculo de aderência + lacunas
├── data/iso27001_seed.py            # seed das Cláusulas 4–10 + 93 controles Anexo A
├── alembic/versions/<rev>_gap_analysis_module.py
└── test/
    ├── test_gap_assessment.py
    ├── test_gap_catalog.py
    ├── test_gap_metrics.py
    ├── test_gap_baseline.py
    ├── test_gap_assignment.py
    └── test_tenant_isolation_gap.py

wtnadmin/src/app/pages/
├── gap-analysis/                    # matriz (avaliar) + filtros por dimensão/tema/cláusula
├── gap-dashboard/                   # indicadores + lista de lacunas
├── gap-catalog/                     # personalizar catálogo da org + adotar versão do seed
└── gap-baselines/                   # congelar/aprovar/comparar baselines
```

**Structure Decision**: monorepo web; backend segue o padrão por domínio (models/schemas/routers/
services) e reusa serviços transversais; frontend com páginas lazy sob `pages/gap-*`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Tabela `gap_seed_item` **sem `tenant_id`** (dado compartilhado da plataforma) | O catálogo-base da norma é único para todas as organizações e mantido pela plataforma; duplicá-lo por tenant antes de qualquer edição desperdiça espaço e dificulta versionar o seed central | Pôr `tenant_id` no seed exigiria N cópias idênticas só-leitura e um "tenant plataforma" artificial; a cópia editável **por org** (com `tenant_id`+RLS) já garante o isolamento de tudo que a organização altera. Seed é somente leitura. |

## Phase 0 — Research

Ver [research.md](research.md): decisões sobre (1) seed compartilhado vs cópia por org e momento da
materialização; (2) modelagem da avaliação (artefato único + itens) e histórico; (3) baseline via
Documento Controlado (novo `DocType.gap_baseline`); (4) reuso do Motor 003 na condução (entidade
`GapAssignment` dedicada reusando eventos/assinatura/OTP/notificação); (5) fórmula de aderência;
(6) estratégia de RLS para tabela compartilhada.

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md): entidades, campos, relacionamentos, transições e regras.
- [contracts/openapi.yaml](contracts/openapi.yaml): endpoints REST do módulo.
- [quickstart.md](quickstart.md): roteiro E2E (avaliar → dashboard → personalizar → baseline →
  atribuir/assinar → isolamento).

## Post-Design Constitution Re-Check

Sem novas violações além da exceção do seed compartilhado (justificada em Complexity Tracking). Todas
as tabelas por-tenant mantêm `tenant_id`+RLS; baseline e histórico append-only; RBAC e auditoria
cobertos; teste de isolamento planejado. **GATE: PASS.**
