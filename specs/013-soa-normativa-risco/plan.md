# Implementation Plan: SoA Normativa — Declaração de Aplicabilidade dirigida pelo Tratamento de Riscos

**Branch**: `013-soa-normativa-risco` | **Date**: 2026-06-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-soa-normativa-risco/spec.md`

## Summary

Evoluir o módulo de SoA existente (Feature 005) — **sem criar módulo novo** — para promover o Pré-SoA
à **Declaração de Aplicabilidade normativa (ISO 27001, 6.1.3 d)**: a aplicabilidade e a justificativa
de inclusão passam a ser dirigidas **primariamente pelo Plano de Tratamento de Riscos** (Feature 012),
consumindo o insumo read-only `GET /risk/soa-feed` (vínculo controle←risco, razão `risk_treatment`).
Preserva tudo o que a 005 já entrega (matriz dos 93 controles, Documento Controlado/versões/baseline/
aprovação, assinatura avançada opcional, exportação PDF, classificação/acesso, divergência/
reconciliação vs. Gap) e adiciona, em paralelo: razões de inclusão dirigidas por risco com **riscos
tratados estruturados**, **divergência/reconciliação contra o insumo de risco vivo**, e o **gate
duro** que rotula a versão emitida como **"SoA normativa (6.1.3 d)"** (quando há Plano de Tratamento
aprovado vigente) ou **"Pré-SoA (consolidação do Gap)"**.

**Abordagem técnica (mínima e aditiva):**
- **Backend**: estender `soa_consolidation_service` (passo dirigido por risco, aditivo/idempotente),
  `soa.py` (readiness do gate na resposta, divergência por fonte, reconciliação de risco),
  `soa_export_service` (snapshot enriquecido) e `soa_schema`. **Uma única mudança de schema**: coluna
  JSON `risk_links` em `soa_item` (projeção dos riscos tratados vinda do feed). O **rótulo da versão**
  e os riscos por controle vivem no `content_snapshot` (JSON) — **sem coluna nova de versão**.
- **Frontend**: evoluir `pages/soa` e `pages/soa-versions` (chips de razão incl. "Risco", riscos
  tratados estruturados, badge de origem, divergência vs. risco + reconciliar, banner Pré-SoA vs.
  normativa com pendências). Sem novas rotas; reusa `permissionGuard('view_soa')`.
- **Sem novas permissões** (`view_soa`/`manage_soa`/`approve_soa`). **Sem novas dependências.**
  **Não altera** o módulo de Risco (012) nem o de Gap (004) — apenas consome.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, reportlab (já em uso
na 005 para PDF) · PrimeNG 21, Angular Signals. **Nenhuma dependência nova.**

**Storage**: PostgreSQL (Alembic + `create_all()` no startup). Mudança de schema: **1 coluna**
(`soa_item.risk_links` JSON, nullable, default `[]`).

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com enforcement central (`helpers/tenant_scope.py`)
+ RLS no PostgreSQL (default do MVP, herdado da 005). O insumo de risco (`soa-feed`) já é
tenant-scoped; a agregação na consolidação **nunca** lê outro tenant (fail-closed).

**Performance Goals**: operações sobre **93 controles** por organização — escala trivial. A consolidação
e a montagem da resposta `GET /soa` devem calcular o insumo de risco (`soa_feed`) **uma vez por
requisição** (não por item), evitando N+1 sobre os riscos.

**Constraints**: backward-compatible com SoA/Pré-SoA já existentes (sem perda de dados); migration
**idempotente**; `risks_treated` legado (texto) preservado e coexistindo com `risk_links` estruturado.

**Scale/Scope**: 1 SoA por organização; 93 itens Anexo A; dezenas de riscos por org. 2 telas evoluídas,
0 telas novas; 1 coluna nova; ~5 endpoints evoluídos (nenhum endpoint novo obrigatório).

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar após a Phase 1 (design).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: toda query via `scoped_query`/`tenant_scope`; o `soa_feed` consumido é
  tenant-scoped; consolidação agrega só vínculos do próprio tenant. Cross-tenant ⇒ 404/403 + audit.
- [x] **RBAC**: reusa `require_permission("view_soa"/"manage_soa"/"approve_soa")`. **Sem permissões
  novas** (SEC-002).
- [x] **Auditoria**: consolidar, editar, reconciliar (Gap e risco), submit-review, aprovar (com rótulo),
  exportar chamam `AuditService.log_from_request()`; trilha `soa_item_event` append-only; sem PII.
- [x] **Integridade de artefatos**: versões imutáveis via `document_versions` (append-only); rótulo
  Pré-SoA/normativa selado no snapshot; assinatura avançada opcional.
- [x] **Dados sensíveis**: SoA é confidencial de negócio (não PII) → rótulo de classificação + política
  de acesso por classificação (Módulo 1) na exportação; risco guardado como **referência** (id/código),
  nunca detalhe sensível; nada em logs/erros.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; SoA router já registrado
  em `main.py` (sem router novo); config em `settings.py` (novos enums `SoaKind`/`SoaDivergenceSource`);
  sem middleware novo.
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms — telas evoluídas seguem o padrão das existentes.
- [x] Schema: modelo SQLAlchemy **+** migration Alembic para a coluna `risk_links`; `soa_item` já tem
  `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: novos testes de consolidação por risco, divergência/reconciliação por risco, gate
  Pré-SoA/normativa, export enriquecido **e** isolamento de tenant (agregação do feed) planejados antes
  da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant (padrão 005).

**Resultado**: PASS — nenhuma violação. **Complexity Tracking** vazio (nada a justificar).

## Project Structure

### Documentation (this feature)

```text
specs/013-soa-normativa-risco/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (openapi-delta.yaml)
└── checklists/
    └── requirements.md  # (do /speckit-specify)
```

### Source Code (repository root) — arquivos tocados

```text
wtnapp/                                  # Backend FastAPI (EVOLUI a 005, não cria módulo)
├── models/soa_model.py                  # + coluna risk_links (JSON) em SoaItem
├── schemas/soa_schema.py                # + risk_links, incomplete, source/source_value na divergência,
│                                        #   readiness (kind/risk_plan_approved/pending) no SoaResponse
├── routers/soa.py                       # consolidate (passo risco), divergences (fonte risco),
│                                        #   reconcile (risco), approve (rótulo no snapshot), get_soa (readiness)
├── services/
│   ├── soa_consolidation_service.py     # passo dirigido por risco (aditivo/idempotente, 1ª-mão),
│   │                                    #   compute_risk_divergence, reconcile risco, notices fora-Anexo-A
│   └── soa_export_service.py            # PDF: razões tipadas, riscos estruturados, origem, rótulo da versão
├── settings.py                          # + SoaKind (pre_soa/normative), SoaDivergenceSource (gap/risk)
├── alembic/versions/<rev>_soa_risk_normative.py   # add column risk_links (idempotente)
└── test/
    ├── test_soa_risk_consolidation.py
    ├── test_soa_risk_divergence.py
    ├── test_soa_gate_normative.py
    ├── test_soa_export.py               # (estender)
    └── test_tenant_isolation_soa.py     # (estender: feed nunca cruza tenant)

wtnadmin/src/app/pages/
├── soa/soa.ts (+ soa.spec.ts)           # razões/risco/origem/divergência-risco/banner Pré-SoA×normativa
└── soa-versions/soa-versions.ts (+spec) # rótulo da versão (Pré-SoA / SoA normativa)
```

**Structure Decision**: Web application monorepo. Esta feature é uma **evolução in-place** do módulo de
SoA (005) — reusa router, serviços, telas e o padrão de Documento Controlado. Nenhuma tabela nova
(apenas 1 coluna), nenhum router novo, nenhuma rota nova.

## Design — decisões-chave

### D1. Armazenamento dos riscos tratados estruturados
Coluna **`risk_links` JSON** em `soa_item` = lista de `{risk_id, risk_code}`, **projeção** do
`soa-feed` aplicada na consolidação/reconciliação (espelha o padrão JSON de `inclusion_reasons`).
Motivo: os vínculos de risco são **derivados** do insumo read-only (não têm ciclo de vida próprio),
então não justificam tabela normalizada + RLS + trigger. O campo legado `risks_treated` (texto) é
**preservado** e coexiste (transição não destrutiva). Detecção de divergência compara `risk_links`
armazenado vs. `soa-feed` vivo.

### D2. Consolidação dirigida por risco (aditiva, idempotente, 1ª-mão)
Após o passo Gap existente, um passo de risco: indexa `soa_feed` por `gap_catalog_item_id`; para cada
`SoaItem` cujo `catalog_item_id` casa com o feed e que **nunca carregou vínculo de risco** (sem
`risk_treatment` em `inclusion_reasons` **e** `risk_links` vazio) → marca `applicable=True`, **adiciona**
`risk_treatment` às razões (sem remover manuais), grava `risk_links` do feed. Itens que **já** carregaram
vínculo de risco **não** são alterados na consolidação — drift vira **divergência** (D3). Entradas do
feed sem `SoaItem` correspondente (catálogo custom/descontinuado, fora do Anexo A) ⇒ **notice** retornado
(não cria item, não descarta sinal). Idempotência: rodar de novo não duplica nem altera campos manuais.

### D3. Divergência por fonte (Gap **e** risco) + reconciliação
`DivergenceField` ganha `source` (`gap`|`risk`) e `source_value` (valor vivo da fonte); `gap_value`
mantido como alias quando `source=gap` (compat de transição do frontend). Divergências de risco:
(a) feed aponta controle não-aplicável/sem `risk_treatment` na SoA; (b) item com `risk_treatment` cujo
feed não aponta mais o controle (ou `risk_links` difere do feed). `reconcile` aceita campos de risco:
aplica o valor vivo (incluir + `risk_treatment` + `risk_links`, ou remover `risk_treatment`/`risk_links`
órfãos), **preservando razões manuais**. Se a reconciliação remover a **única** razão (`risk_treatment`)
de um item aplicável sem razão manual ⇒ item **permanece aplicável** e fica **incompleto** (FR-009a),
sem auto-flip. Feed calculado **1×/requisição** e passado ao builder de item (sem N+1).

### D4. Gate duro = rótulo da versão (não bloqueio de aprovação)
`has_approved_risk_plan = (RiskPlan.current_version_id is not None)` para o tenant (versão aprovada
**vigente** do Plano de Tratamento; não há fluxo de revogação que limpe o ponteiro hoje — se for
adicionado, deve limpar `current_version_id`). Na aprovação: o snapshot grava
`soa_kind = "normative"` se houver plano aprovado vigente, senão `"pre_soa"`, mais
`risk_plan_version_number`. A aprovação **continua bloqueada** apenas pela **completude** já existente
(`_incomplete_refs`, que cobre FR-009a). `GET /soa` expõe `kind`/`risk_plan_approved`/`pending_for_normative`
para o banner. Versões emitidas são imutáveis com o rótulo congelado.

### D5. Exportação PDF enriquecida
`render_pdf` lê do snapshot: rótulo (Pré-SoA / SoA normativa) no cabeçalho; por controle aplicável, as
razões tipadas, os **riscos tratados** (códigos de `risk_links`, fallback para `risks_treated` legado) e
a **origem** (risco vs. manual); não-aplicáveis exibem a justificativa de exclusão. Sem libs novas.

## Complexity Tracking

> Sem violações de constitution — seção vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| — | — | — |
