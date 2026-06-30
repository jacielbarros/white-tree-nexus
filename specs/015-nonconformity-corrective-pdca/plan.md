# Implementation Plan: Não Conformidades & Ações Corretivas (10.2) + Análise Crítica (9.3) + PDCA (10.1)

**Branch**: `015-nonconformity-corrective-pdca` | **Date**: 2026-06-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/015-nonconformity-corrective-pdca/spec.md`

## Summary

Feature 5b **fecha o ciclo PDCA** do SGSI e realimenta a esteira, em três fases:

1. **Não Conformidades & Ações Corretivas (10.2)** — domínio novo `nonconformity_*`: registrar NC
   (origem, severidade Maior/Menor/Observação, vínculo primário opcional a controle SoA/risco/ativo,
   causa raiz, status), **ações corretivas** (responsável=membro + prazo), **verificação de eficácia**
   (gate de encerramento) e **promoção** de constatações de auditoria (5a) a NC formal. Evidências
   anexadas pelo **repositório transversal da 5a** (estendendo o vínculo polimórfico para os alvos
   `nonconformity`/`corrective_action`).
2. **Análise Crítica pela Direção (9.3)** — domínio `management_review_*` (coleção: uma por reunião),
   como **Documento Controlado** (reusa `controlled_document_service` + `document_versions`, novo
   `DocType.management_review`), com entradas/saídas, aprovação, PDF e assinatura avançada opcional.
3. **Melhoria Contínua / PDCA (10.1)** — domínio `improvement_*`: melhorias (origem auditoria/NC/
   análise crítica/sugestão, status) com **referência read-only** de realimentação a artefato, e uma
   **visão de ciclo PDCA** (read-only) reusando a rastreabilidade/timeline da 5a.

Transversal: dashboard do módulo + card de readiness na esteira (assume o placeholder `action_plan`
deixado na 5a). **Consome** SoA (005), Riscos (012), Ativos (011), Auditoria/Evidências (5a) e
Documento Controlado **read-only** — exceto **uma** escrita deliberada: a promoção preenche o ponteiro
**reservado** `internal_audit_finding.nonconformity_ref` (o gancho que a 5a deixou pronto).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, `reportlab` (PDF, já
em uso), `cryptography` (já em uso) · PrimeNG 21, Angular Signals. **Sem novas dependências.**

**Storage**: PostgreSQL (Alembic + `create_all()` no startup).

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed.

**Target Platform**: Web (API REST + SPA Angular).

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend).

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`) +
RLS no PostgreSQL — igual a todos os módulos. Todas as 7 tabelas novas com `tenant_id`+RLS; trilhas
(`nonconformity_event`, `improvement_event`) append-only (triggers SQLite+PG). Promoção, PDCA e
dashboards **nunca** agregam dados de outro tenant (fail-closed).

**Performance Goals**: padrão de aplicação web — listas/filtros de NC e dashboards respondem em tempo
interativo (< ~1 s para volumes típicos por tenant). Indicadores simples (sem motor de KPIs/9.1).

**Constraints**: gate de encerramento da NC (verificação eficaz) e gate duro de aprovação da Ata
parametrizados no planejamento; promoção idempotente; vínculos a módulos consumidos **read-only**
(única exceção: `nonconformity_ref`).

**Scale/Scope**: dezenas de organizações; por tenant, centenas de NCs/ações, dezenas de análises
críticas e melhorias. ~6 telas novas no admin (reusam `evidence-panel` e `traceability-timeline`).

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar após a Phase 1 (design).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: toda query passa por `scoped_query`/`get_org_context`; 7 tabelas novas
  com `tenant_id`+RLS; cross-tenant ⇒ 404 + audit; promoção/PDCA/dashboard fail-closed. Teste de
  isolamento dedicado obrigatório (NC, ação, verificação, análise crítica, melhoria).
- [x] **RBAC**: novos `require_permission(...)` — `view_nonconformity`/`manage_nonconformity`,
  `view_management_review`/`manage_management_review`/`approve_management_review`.
- [x] **Auditoria**: CRUD/transições de NC, promoção, ações, verificação, encerramento, Ata
  (submeter/aprovar/assinar/exportar) e melhorias chamam `AuditService.log_from_request()`; trilhas
  append-only; sem PII/segredos nos campos.
- [x] **Integridade**: NC/melhoria com trilha append-only; Ata versionada por `document_versions`
  (imutável). Promoção idempotente preserva o registro da constatação (não a apaga).
- [x] **Dados sensíveis**: NCs/Atas podem conter conteúdo sensível — nunca em logs/erros/telemetria;
  evidências seguem a proteção da 5a. Sem PII bruta.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novos routers
  (`nonconformity`, `management_review`, `improvement`) em `main.py`; config em `settings.py`; sem
  middleware novo.
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelos SQLAlchemy + migration Alembic idempotente; modelos de domínio com `tenant_id`;
  `create_all()` mantido.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas principais **e isolamento de tenant** planejados por fase.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant.

**Resultado**: PASS. Única nota de design → **Complexity Tracking** (escrita controlada na 5a).

## Project Structure

### Documentation (this feature)

```text
specs/015-nonconformity-corrective-pdca/
├── plan.md · research.md · data-model.md · quickstart.md
├── contracts/openapi.yaml
└── tasks.md   # (/speckit.tasks)
```

### Source Code (repository root)

```text
wtnapp/
├── models/
│   ├── nonconformity_model.py        # NOVO: nonconformity, corrective_action, nonconformity_verification, nonconformity_event
│   ├── management_review_model.py    # NOVO: management_review (Documento Controlado, coleção)
│   └── improvement_model.py          # NOVO: improvement, improvement_event
├── schemas/{nonconformity_schema, management_review_schema, improvement_schema}.py   # NOVOS
├── routers/{nonconformity, management_review, improvement}.py                         # NOVOS (em main.py)
├── services/
│   ├── nonconformity_service.py      # NC/ações/verificação/promoção/state machine/gate
│   ├── management_review_service.py  # snapshot + reuso controlled_document/signature
│   ├── management_review_export_service.py  # PDF (reportlab)
│   ├── improvement_service.py        # melhorias + status
│   ├── pdca_service.py               # visão de ciclo PDCA (read-only; reusa traceability_service)
│   └── nc_metrics_service.py         # dashboard do módulo
├── services/evidence_service.py      # ESTENDIDO: _TARGET_MODELS += nonconformity/corrective_action
├── services/dashboard_service.py     # ESTENDIDO: card readiness "Act/PDCA" (substitui placeholder action_plan)
├── settings.py                       # +enums + DocType.management_review + NC_/IMPROVEMENT_CODE_PREFIX
├── helpers/permissions.py            # +5 permissões
└── alembic/versions/<rev>_nonconformity_pdca_module.py   # NOVO (down_revision=b8c9d0e1f016)

wtnadmin/src/app/
├── core/{models.ts, api.service.ts, permissions.ts}   # tipos + métodos + 5 permissões
├── pages/nonconformities/ · nonconformity-detail/      # NOVOS
├── pages/management-reviews/ · management-review-detail/  # NOVOS
├── pages/improvements/ (+ visão PDCA) · nonconformity-dashboard/  # NOVOS
└── shared/{evidence-panel, traceability-timeline}      # REUSO (5a)
```

**Structure Decision**: monorepo. Três domínios novos (`nonconformity_*`, `management_review_*`,
`improvement_*`). Reuso máximo de `controlled_document_service`/`document_versions`,
`signature_service`, `soa_export`/reportlab, `evidence_*` (5a) + `traceability_service`,
`dashboard_service`, `tenant_scope`/RLS e auditoria.

## Phase 0 — Research

Ver [research.md](research.md). Decisões consolidadas (clarify fechou as 5 de alto impacto):

- Promoção **1:1 idempotente** que preenche `internal_audit_finding.nonconformity_ref` (única escrita
  na 5a); constatação permanece ativa.
- Análise crítica = **coleção** (uma por reunião), Documento Controlado com novo `DocType`.
- Severidade **Maior/Menor/Observação**; vínculo NC↔artefato = **um primário opcional**.
- PDCA = **referência read-only** + visualização (reusa `traceability_service`); sem write-back.
- Evidências por **extensão** da taxonomia `SgsiArtifactType` (novos alvos), sem novo esquema.

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md): 7 tabelas, enums, máquina de estados (NC + ação), gate de
  encerramento, contrato de promoção, matriz de permissões.
- [contracts/openapi.yaml](contracts/openapi.yaml): endpoints de `/nonconformities`,
  `/management-reviews`, `/improvements` (+ PDCA) e a extensão do `/evidence` (alvos novos).
- [quickstart.md](quickstart.md): E2E (registrar/promover NC → ação → verificação → encerrar; análise
  crítica aprovada/PDF; melhoria + visão PDCA; isolamento).
- Agent context: atualizar `CLAUDE.md` entre os marcadores SPECKIT.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Escrita em `internal_audit_finding.nonconformity_ref` (tabela da 5a) ao promover | É o **contrato de promoção** já previsto na 5a (campo reservado p/ esta feature); materializa o vínculo bidirecional auditoria↔NC | Não escrever deixaria a constatação sem referência à NC (perde rastreabilidade); duplicar só na NC quebra a navegação reversa a partir da auditoria. **Escopo**: apenas esse ponteiro é escrito; nenhum outro dado da 5a/SoA/Risco/Ativo é alterado. |
