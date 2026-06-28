# Implementation Plan: Módulo de Gestão de Riscos (Ameaças/Vulnerabilidades · Avaliação 6.1.2 · Tratamento 6.1.3)

**Branch**: `012-risk-management` | **Date**: 2026-06-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/012-risk-management/spec.md`

## Summary

Módulo de Riscos do MVP (entre Ativos e SoA definitiva): **um módulo de engenharia** que cobre, como
**três passos distintos na esteira**, (1) catálogos de **ameaças e vulnerabilidades**, (2) **avaliação
de riscos** (cláusula 6.1.2) e (3) **plano de tratamento** (cláusula 6.1.3). A feature adiciona um
domínio novo tenant-scoped com: **metodologia de risco** configurável por org (default 5x5); catálogos
**semente compartilhada (plataforma) + cópia editável por org** (adoção aditiva/idempotente, padrão do
Gap) com vínculo a **ativos** e a **gaps**; **registro de risco** como cenário (ativos + ameaça +
vulnerabilidade) com **impacto derivado da CIA** (`max(C,I,A)`, override justificado), **nível** pela
matriz e marcação **acima/abaixo do critério de aceitação**, heat map 5x5; **tratamento** (mitigar/
aceitar/transferir/evitar) com **controles do catálogo de Gap da org** (responsável + prazo),
**re-pontuação residual**, **aceitação do risco** (justificativa + dono) e **Plano de Tratamento**
versionável (Documento Controlado, assinatura avançada opcional); **insumo da SoA** exposto como vínculo
**controle ← risco read-only** (sem escrever na SoA); preenchimento dos **placeholders do detalhe do
ativo**; **histórico append-only** por risco; **dashboard do módulo** + card de **readiness na esteira**.

**Abordagem técnica**: segue exatamente o padrão dos módulos existentes (Gap/SoA/Ativos). Modelos ORM
síncronos com `tenant_id` + RLS no PostgreSQL e triggers append-only (SQLite+PG) na trilha de risco;
catálogos-semente **platform-level sem `tenant_id`** (mesma exceção do `gap_seed_item`); router único
`risk.py` (`/risk`) com `require_permission` + `scoped_query` + `AuditService`; serviços para
metodologia/cálculo de nível, derivação de impacto, geração de código, adoção de semente, métricas/heat
map e consolidação do plano; reuso de `controlled_document_service` + `document_versions` (novo
`DocType.risk_treatment_plan`) e do motor de assinatura (`signature_service`, opcional); extensão do
`dashboard_service` com um card de risco. Frontend Angular 21 standalone (Signals/OnPush) com páginas
lazy-loaded por fase + `permissionGuard('view_risk')`. **Sem novas dependências** (PDF deferido).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic · PrimeNG 21, Angular
Signals. **Sem novas dependências** — reusa `controlled_document_service`/`document_versions` e
`signature_service` (assinatura avançada opcional). PDF/relatórios são **deferidos** (sem `reportlab`
neste módulo).

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); SQLite in-memory nos testes.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed.

**Target Platform**: Web (API REST + SPA Angular).

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend).

**Tenant Isolation Strategy**: **shared-DB + `tenant_id` com enforcement central** em
`helpers/tenant_scope.py` (`get_org_context` + `scoped_query`) **e** RLS no PostgreSQL (policy
`tenant_isolation` por tabela, `app.tenant_id` via `set_config`). Idêntico aos módulos existentes.
**Exceção**: `threat_seed_item`/`vulnerability_seed_item` são **conteúdo de plataforma sem `tenant_id`**
(somente leitura, sem RLS — mesma exceção do `gap_seed_item` da Feature 004/007). Isolamento sempre
fail-closed.

**Performance Goals**: padrão web; volume de PME (dezenas a poucas centenas de riscos por org).
Listagem paginada/filtrável; heat map, dashboard e SoA-feed agregados em uma chamada cada. Resolução
(Phase 0 R0): sem alvo numérico de latência/throughput além do critério de UX do spec (SC-001: avaliar
um risco em < 5 min).

**Constraints**: sem cifragem de campo (mesma decisão do Ativos — RBAC + isolamento + "sem PII bruta");
sem exclusão física (arquivamento lógico justificado); histórico append-only; **não escrever na SoA**
(apenas expor vínculo); **não alterar o modelo de Ativos** (só consumir/exibir vínculos nos
placeholders); residual = re-pontuação simples (sem fórmula de eficácia); apenas qualitativa 5x5
(sem quantitativo); sem scanners/automação; sem workflow pesado além do Documento Controlado.

**Scale/Scope**: 12 tabelas novas (2 platform-level + 10 tenant-scoped); 1 router novo (`/risk`);
3 permissões novas (`view_risk`/`manage_risk`/`approve_risk_plan`); 1 novo `DocType`
(`risk_treatment_plan`); ~6 telas (metodologia, catálogo, registro/matriz, detalhe, plano, dashboard) +
extensão da tela de detalhe do ativo (preencher placeholders) e do `dashboard_service` (card de risco).

## Constitution Check

*GATE: passou antes da Phase 0; re-checado após a Phase 1 (sem mudanças).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: todas as **10 tabelas de domínio** têm `tenant_id` (`risk_methodology`,
  `org_threat`, `org_vulnerability`, `asset_threat_link`, `asset_vulnerability_link`, `risk`,
  `risk_asset_link`, `risk_treatment_control`, `risk_plan`, `risk_events`); queries via
  `scoped_query`/filtro por `ctx.tenant_id`; **RLS PG nas 10**. Cross-tenant ⇒ 404 genérico + audit.
  Cenários/vínculos/controles só referenciam itens do **mesmo tenant** (ativos, catálogos, gaps da org)
  — checado na app + RLS. As **2** tabelas-semente são platform-level (read-only, sem RLS — exceção
  documentada, igual ao Gap). Teste de isolamento dedicado obrigatório.
- [x] **RBAC**: endpoints usam `require_permission("view_risk")` / `require_permission("manage_risk")`;
  aprovação do plano usa `require_permission("approve_risk_plan")` (Admin); edição do **seed**
  (plataforma) usa `require_super_admin` (sem contexto de org). Permissões batem com SEC-002.
- [x] **Auditoria**: criação/edição de risco, mudança de prob/impacto/nível, override de impacto, troca
  de dono, decisão de tratamento, seleção/remoção de controle, aceitação, consolidação/aprovação do
  plano, adoção/edição/arquivamento de catálogo, vínculos e negações chamam
  `AuditService.log_from_request()`. Sem PII/segredos. Listagem simples não loga.
- [x] **Integridade de evidências/artefatos**: o **Plano de Tratamento** é Documento Controlado com
  versão imutável (reusa `controlled_document_service` + `document_versions` + gatilho append-only já
  existente) e o **`risk_event`** é trilha append-only (triggers SQLite+PG). Ambos preservam autor/data/
  ação. Arquivamento é lógico. (SEC-005)
- [x] **Dados sensíveis**: **cifragem em repouso N/A por design** (SEC-004, mesma decisão do Ativos): o
  módulo guarda decisões/indicadores de risco, **não** PII bruta; descrições/justificativas proibidas de
  conter PII bruta; proteção por RBAC + tenant + não-exposição em logs/erros. Princípio V ("cifrado
  **quando aplicável**") respeitado — não aplicável aqui, justificado na spec.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy **síncrono**; `get_db()` central; novo router `risk`
  registrado em `main.py`; config (prefixo de código, default da metodologia, janela de cálculo) em
  `settings.py` via `load_dotenv()`; sem middleware novo.
- [x] Frontend: standalone (sem NgModules); `input()`/`output()`; `inject()`; control flow nativo;
  `OnPush`; Signals; Reactive Forms (`NonNullableFormBuilder`); `get/post/put/patch/delete` genéricos +
  `getBlob` do `ApiService` (já existem).
- [x] Schema: modelos SQLAlchemy **+** migration Alembic idempotente (`down_revision="b1c2d3e4f015"`,
  head atual = Feature 011); todos os modelos de domínio com `tenant_id`; novo `DocType` aditivo.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas (metodologia ausente → default; validações de cenário/
  tratamento/aceitação; mitigar sem controle; gate duro na aprovação; append-only; cross-tenant em
  cenário/controle/vínculo; idempotência da adoção) **e teste de isolamento de tenant** planejados antes
  da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant (404 genérico).

**Resultado**: ✅ Sem violações. **Complexity Tracking vazio.**

## Project Structure

### Documentation (this feature)

```text
specs/012-risk-management/
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
├── data/
│   └── iso27005_seed.py             # NOVO: semente PT-BR original de ameaças + vulnerabilidades (ISO 27005)
├── models/
│   ├── risk_model.py                # NOVO: Risk, RiskAssetLink, RiskTreatmentControl, RiskPlan, RiskEvent
│   ├── risk_catalog_model.py        # NOVO: ThreatSeedItem, VulnerabilitySeedItem (platform) + OrgThreat, OrgVulnerability + AssetThreatLink, AssetVulnerabilityLink
│   ├── risk_methodology_model.py    # NOVO: RiskMethodology (1 por org; escalas/matriz/critério/CIA→impacto em JSON)
│   └── __init__.py                  # registrar os novos modelos
├── schemas/
│   └── risk_schema.py               # NOVO: Methodology, Threat/Vulnerability (Create/Update/Response), Risk (Create/Update/Response), Treatment, Control, Acceptance, Plan, Matrix/Heatmap, Dashboard, SoaFeed, Event
├── routers/
│   └── risk.py                      # NOVO: /risk (methodology, threats, vulnerabilities, adopt, asset-links, risks CRUD, matrix, treatment, controls, accept, plan, soa-feed, dashboard, history)
├── services/
│   ├── risk_methodology_service.py  # NOVO: get-or-default 5x5, validação de escalas/matriz, cálculo de nível, critério de aceitação, mapa CIA→impacto, recálculo em massa
│   ├── risk_service.py              # NOVO: geração de código (RSK-####), derivação de impacto da CIA + override, transições de status, validações, diffing/eventos com justificativa
│   ├── risk_catalog_service.py      # NOVO: load_seed + adopt_seed (idempotente) de ameaças/vulnerabilidades; vínculos a ativos/gaps
│   ├── risk_treatment_service.py    # NOVO: opção/controles/residual, aceitação, consolidação + aprovação do plano (Documento Controlado), SoA-feed
│   └── risk_metrics_service.py      # NOVO: heat map 5x5, distribuições, top riscos, inerente×residual (dashboard do módulo)
├── helpers/permissions.py           # +view_risk / +manage_risk / +approve_risk_plan na matriz PERMISSIONS
├── settings.py                      # +enums (RiskStatus, RiskTreatmentOption, RiskEventType, ...) + DocType.risk_treatment_plan + RISK_CODE_PREFIX + defaults da metodologia
├── services/dashboard_service.py    # +_risk_card (gated em view_risk) na esteira (Feature 006)
├── schemas/dashboard_schema.py      # +DashboardModuleId.risk
├── main.py                          # app.include_router(risk.router)
├── alembic/versions/
│   └── c2d3e4f5a116_risk_management_module.py  # NOVO (idempotente, RLS nas 10 tabelas tenant + triggers append-only de risk_events)
└── test/
    ├── test_risk_methodology.py     # default 5x5, edição, cálculo de nível, recálculo em massa
    ├── test_risk_catalog.py         # adoção idempotente, custom, arquivar, vínculos a ativos/gaps
    ├── test_risk_assessment.py      # cenário, código, derivação de impacto/override, nível, critério, filtros, heat map
    ├── test_risk_treatment.py       # opção, controles (mitigar exige ≥1 c/ resp+prazo), residual, aceitação, SoA-feed
    ├── test_risk_plan.py            # consolidação, submit-review, gate duro, aprovação + versão imutável, assinatura opcional
    ├── test_risk_history.py         # append-only + justificativa nas mudanças relevantes
    ├── test_risk_metrics.py         # heat map + distribuições + inerente×residual
    ├── test_risk_dashboard_card.py  # card de readiness na esteira (Feature 006)
    └── test_tenant_isolation_risk.py  # OBRIGATÓRIO (risco, catálogo, metodologia, vínculo, controle, plano, histórico)

wtnadmin/src/app/
├── core/
│   ├── permissions.ts               # +view_risk / +manage_risk / +approve_risk_plan
│   └── models.ts                    # +tipos do módulo (Risk, Methodology, Threat, Vulnerability, Treatment, etc.)
├── pages/
│   ├── risk-methodology/            # NOVO: config de escalas/matriz/critério/CIA→impacto (+ .spec.ts)
│   ├── risk-catalog/                # NOVO: Fase 1 — ameaças + vulnerabilidades (adotar/custom/arquivar/vincular) (+ .spec.ts)
│   ├── risks/                       # NOVO: Fase 2 — registro (lista + filtros/busca + heat map + criar) (+ .spec.ts)
│   ├── risk-detail/                 # NOVO: detalhe (cenário/avaliação/tratamento/controles/residual/aceitação/histórico) (+ .spec.ts)
│   ├── risk-treatment-plan/         # NOVO: Fase 3 — plano consolidado (submit/aprovar/assinar/versões) (+ .spec.ts)
│   ├── risk-dashboard/              # NOVO: heat map + distribuições + inerente×residual (+ .spec.ts)
│   └── asset-detail/                # ALTERADO: preencher placeholders (ameaças/vulnerabilidades/riscos/controles) via /risk
└── app.routes.ts                    # +rotas risk-* (permissionGuard('view_risk')); shell: links das 3 fases do módulo
```

**Structure Decision**: Web monorepo. Domínio novo isolado em `risk_*` (backend) e `pages/risk*`
(frontend), espelhando Gap/SoA/Ativos. Nenhum arquivo de outro módulo é alterado **exceto** pontos de
registro/integração padrão (`models/__init__.py`, `main.py`, `permissions.py`, `settings.py`,
`app.routes.ts`, shell, `core/permissions.ts`, `core/models.ts`), a **extensão de leitura** do
`dashboard_service`/`dashboard_schema` (card de risco, Feature 006) e a tela `pages/asset-detail`
(preencher placeholders já existentes via endpoints `/risk`, sem tocar no modelo de Ativos).

## Complexity Tracking

> Sem violações de constitution — seção intencionalmente vazia. (12 tabelas — 2 semente + 10
> tenant-scoped — é acima da média, mas justificado: o módulo cobre três fases ISO encadeadas; cada
> tabela tem responsabilidade única e segue o padrão já estabelecido — nenhuma exige novo mecanismo
> arquitetural.)

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |
