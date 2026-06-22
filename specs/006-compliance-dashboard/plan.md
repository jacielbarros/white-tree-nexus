# Implementation Plan: Dashboard de Conformidade

**Branch**: `006-compliance-dashboard` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-compliance-dashboard/spec.md`

## Summary

Tela inicial de cada organização: uma **visão de leitura** que agrega o estado de conformidade
ISO/IEC 27001:2022 dos módulos já existentes (Contexto/Cláusula 4, Gap Analysis, SoA — e
placeholders para Plano de Ação e Evidências). Um **único endpoint de leitura no backend**
(`GET /dashboard`) compõe os serviços existentes (`gap_metrics_service`, `soa` consolidation,
`context/overview`, `form_assignments`, `document_versions`) e devolve um payload pronto para a
home; o frontend faz **uma chamada** e renderiza cards (status, progresso, responsável, prazo,
alerta de revisão vencida, atalho de próxima ação). **Sem novo modelo de domínio, sem migration.**
Uma única peça nova de RBAC: a permissão `view_dashboard`.

Decisões de clarificação (2026-06-21) incorporadas: (1) agregação no **backend**; (2) atalho de
próxima ação navega para a **rota do módulo com a seção em foco** (sem reescrever rotas);
(3) audit log **apenas** de tentativas não autorizadas (leituras bem-sucedidas não são logadas).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2 · PrimeNG 21, Angular Signals.
**Nenhuma dependência nova.**

**Storage**: PostgreSQL (somente leitura nesta feature — agrega tabelas existentes). **Sem migration.**

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`
+ RLS no PG). Igual aos demais módulos — o endpoint usa `OrgContext` resolvido pela dependency
central e nunca filtra tenant ad-hoc.

**Performance Goals**: dashboard responde em < 2 s (SC-001). Agregação ao vivo de consultas pequenas
e escopadas por tenant (1 assessment, 1 SoA ~93 itens, 3 artefatos de contexto, atribuições ativas,
versões correntes). Sem cache no MVP.

**Constraints**: read-only; sem efeito colateral de escrita; sem novo modelo de domínio; sem
middleware novo; degradação por card (falha de agregação de um módulo não derruba os demais).

**Scale/Scope**: 1 endpoint backend + 1 service + 1 permissão; refatora a página `pages/dashboard/`
existente (que hoje compõe endpoints no frontend) para consumir o novo endpoint. ~5 telas afetadas
indiretamente apenas por links (já existentes).

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar após a Phase 1 (design).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: o endpoint resolve `OrgContext` via `get_org_context` (ponto único,
  fail-closed em org suspensa, audita cross-tenant) e todas as queries do service recebem
  `ctx.tenant_id` / `scoped_query`. Nenhum filtro ad-hoc. Teste de isolamento dedicado planejado.
- [x] **RBAC**: endpoint usa `require_permission("view_dashboard")`. Cards de módulo são incluídos
  somente se o papel tiver a permissão de visão correspondente (`view_context`/`view_gap`/`view_soa`)
  — o dashboard nunca eleva permissões. (SEC-002)
- [x] **Auditoria**: leituras bem-sucedidas **não** geram audit log (decisão de clarificação — home
  carregada a cada navegação; evita inflar trilha append-only). Tentativas não autorizadas já são
  logadas pelas dependencies centrais (`get_org_context` ⇒ `CROSS_TENANT_DENIED`;
  `require_permission` ⇒ `PERMISSION_DENIED`). (SEC-003)
- [x] **Integridade de evidências/artefatos**: N/A — feature é read-only, não cria nem versiona
  artefato. (SEC-005)
- [x] **Dados sensíveis**: expõe apenas metadados de status/progresso/responsável/data; não expõe
  conteúdo de evidência, respostas de formulário nem dados classificados. (SEC-004)

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; **novo router
  `dashboard.py` registrado em `main.py`**; lógica reutilizável em `services/dashboard_service.py`;
  sem middleware novo.
- [x] Frontend: standalone; `inject()`; control flow nativo; `OnPush`; Signals. (A página já existe
  nesse padrão; será ajustada para 1 chamada + tipos.)
- [x] Schema: **sem mudança de tabela** ⇒ sem migration. (Regra atendida por não tocar schema.)

**Qualidade (Definition of Done):**

- [x] **Test-first**: planejados teste de happy path (agregação dos 3 módulos), falhas (módulo
  ausente / sem dados ⇒ card "não iniciado"; falha isolada por card), **isolamento de tenant**
  (JWT de outra org ⇒ 404 + sem vazamento) e RBAC (`view_dashboard` ausente ⇒ 403; card omitido
  sem permissão de módulo). Frontend: render dos cards + estados.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant (reusa
  404 genérico das dependencies centrais).

**Resultado do gate**: ✅ PASS — nenhuma violação. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/006-compliance-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (DTOs de leitura — sem entidade nova)
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── openapi.yaml      # GET /dashboard
└── checklists/
    └── requirements.md   # (do /speckit-specify)
```

### Source Code (repository root)

```text
wtnapp/
├── routers/dashboard.py            # NOVO — GET /dashboard (require_permission view_dashboard)
├── services/dashboard_service.py   # NOVO — compõe gap_metrics, soa, context, assignments, versões
├── schemas/dashboard_schema.py     # NOVO — DTOs Pydantic de resposta (read-only)
├── helpers/permissions.py          # EDITADO — adiciona "view_dashboard" à matriz de papéis
├── main.py                         # EDITADO — app.include_router(dashboard.router)
└── test/
    ├── test_dashboard.py               # NOVO — agregação, estados, próxima ação, RBAC
    └── test_tenant_isolation_dashboard.py  # NOVO — isolamento de tenant (obrigatório)

wtnadmin/src/app/
├── pages/dashboard/dashboard.ts        # EDITADO — 1 chamada a /dashboard (em vez de 3 forkJoin)
├── pages/dashboard/dashboard.spec.ts   # EDITADO — mock do novo endpoint único
├── core/permissions.ts                 # EDITADO — espelha a permissão view_dashboard
└── core/api.service.ts                 # (reusa get<T> genérico — sem mudança)
```

**Structure Decision**: Web application monorepo. Backend ganha 1 router + 1 service + 1 schema +
1 permissão (e registro em `main.py`). Frontend migra a home para consumir o endpoint único.

## Complexity Tracking

> Sem violações de constituição. Tabela intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
