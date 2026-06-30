# Implementation Plan: Repositório Transversal de Evidências + Auditoria Interna (9.2)

**Branch**: `014-cross-evidence-internal-audit` | **Date**: 2026-06-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/014-cross-evidence-internal-audit/spec.md`

## Summary

Feature 5a fecha a base probatória do SGSI em duas fases:

1. **Repositório transversal de evidências** — generaliza o módulo de evidências do Gap (Feature 008)
   para um **store unificado** (`evidence_*`) onde a evidência é objeto de 1ª classe vinculável a
   **1..N** artefatos por **vínculo polimórfico** (`evidence_link`) a linhas de artefato já existentes
   e tenant-scoped: item da SoA, risco, ativo, item do Gap e — nesta feature — constatação de
   auditoria. Reusa o `utils/evidence_storage.py` (upload + SHA-256 + cifragem Fernet em repouso),
   versões imutáveis, inativação lógica, trilha de custódia append-only e auditoria. As evidências do
   Gap (008) são **migradas** para o store unificado e os endpoints do Gap continuam funcionando via
   adaptador. Acrescenta um **repositório central pesquisável/filtrável** e um painel de evidências
   reutilizável nas telas de cada artefato.

2. **Auditoria interna (9.2)** — domínio novo `internal_audit_*`: programa de auditoria → auditoria
   (escopo/critérios/auditor/período/estado) → checklist de itens auditados (vinculados a
   controle/cláusula/risco, entrada manual + importação opcional do escopo SoA/Gap) → **constatações**
   (conforme / NC maior / NC menor / oportunidade / observação) com evidência anexada e vínculo;
   constatações de NC são **promovíveis** com ponto de vínculo reservado para a Feature 5b. O
   **relatório de auditoria** é um Documento Controlado (reusa `controlled_document_service` +
   `document_versions`, novo `DocType.internal_audit_report`), aprovável com assinatura avançada
   opcional e exportável em PDF. **Gate duro** só na aprovação/congelamento do relatório.

Transversal: **timeline** somente-leitura por artefato (agrega evidências/constatações/eventos),
**dashboard do módulo** (cards simples) e **card de readiness** no Dashboard de Conformidade.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, `cryptography`
(Fernet, já em uso), `reportlab` (PDF, já em uso) · PrimeNG 21, Angular Signals. **Sem novas
dependências.**

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); arquivos de evidência via
`utils/evidence_storage.py` (local/`EVIDENCE_STORAGE_DIR`, cifrado com Fernet).

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`)
e RLS no PostgreSQL — igual a todos os módulos. Todas as tabelas novas carregam `tenant_id` + RLS;
trilhas (`evidence_version`, `evidence_event`, `internal_audit_event`) são append-only (triggers
SQLite + PG). Consolidação de relatório e timeline **nunca** agregam dados de outro tenant
(fail-closed).

**Performance Goals**: padrão de aplicação web — listas paginadas/filtradas do repositório central e
da auditoria respondem em tempo interativo (< ~1 s para volumes típicos de um tenant). Sem alvos
quantitativos rígidos (indicadores simples por design — sem motor de KPIs 9.1).

**Constraints**: `EVIDENCE_MAX_FILE_BYTES` (20 MB default) e política de extensão/MIME já
configuráveis em `settings.py`; `FIELD_ENCRYPTION_KEY` obrigatória para upload (fail-closed). Migração
do 008 deve preservar histórico/hash/autoria sem perda de dados.

**Scale/Scope**: dezenas de organizações; por tenant, centenas/milhares de evidências e dezenas de
auditorias. ~5 telas novas no admin + 1 painel de evidências reutilizável + extensões em 3 telas de
artefato (SoA/risco/ativo) e na tela do Gap.

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar após a Phase 1 (design).*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: toda query de domínio passa por `scoped_query`/`get_org_context`;
  tabelas novas têm `tenant_id` + RLS; cross-tenant ⇒ 404 genérico + audit (padrão do 008). Teste de
  isolamento dedicado obrigatório (evidência, vínculo, auditoria, constatação, relatório).
- [x] **RBAC**: novos `require_permission(...)` — `view_evidence`/`manage_evidence`,
  `view_internal_audit`/`manage_internal_audit`/`approve_audit_report`. Conteúdo confidencial/restrito
  exige permissão elevada conforme política de classificação (reusa `classification_access`).
- [x] **Auditoria**: upload/download/replace/inactivate/link/unlink, CRUD de auditoria/constatação,
  transições de estado e geração/aprovação/assinatura/exportação do relatório chamam
  `AuditService.log_from_request()`; trilha append-only; sem PII/segredos/`storage_key` nos campos.
- [x] **Integridade de evidências/artefatos**: `evidence_version` imutável com hash por versão;
  relatório versionado por `document_versions`; constatação/auditoria com trilha append-only
  (`internal_audit_event`).
- [x] **Dados sensíveis**: conteúdo cifrado em repouso (Fernet, herdado de `evidence_storage`);
  `storage_key`/conteúdo nunca expostos em API/logs/erros/telemetria; timeline/repositório só metadados.

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novos routers
  (`evidence`, `internal_audit`, `traceability`) registrados em `main.py`; config em `settings.py` +
  `load_dotenv()`; sem middleware novo.
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelos SQLAlchemy + migration Alembic idempotente; modelos de domínio com `tenant_id`;
  `create_all()` mantido.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas principais **e isolamento de tenant** planejados por fase
  (evidência transversal, auditoria, constatação, relatório, migração 008).
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant (padrão 008).

**Resultado**: PASS — sem violações. **Complexity Tracking** não necessário.

## Project Structure

### Documentation (this feature)

```text
specs/014-cross-evidence-internal-audit/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── openapi.yaml      # Phase 1 (endpoints novos)
└── tasks.md             # Phase 2 (/speckit.tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
wtnapp/
├── models/
│   ├── evidence_model.py            # NOVO: evidence, evidence_version, evidence_link, evidence_event
│   ├── internal_audit_model.py      # NOVO: internal_audit_program/audit/checklist_item/finding/event
│   └── gap_evidence_model.py        # REMOVIDO após migração (tabelas migradas p/ evidence_*)
├── schemas/
│   ├── evidence_schema.py           # NOVO
│   └── internal_audit_schema.py     # NOVO
├── routers/
│   ├── evidence.py                  # NOVO  (/evidence)
│   ├── internal_audit.py            # NOVO  (/internal-audit)
│   ├── traceability.py              # NOVO  (/traceability/timeline)
│   └── gap_evidence.py              # ADAPTADO: delega ao evidence_service (mesmos paths)
├── services/
│   ├── evidence_service.py          # NOVO: upload/replace/inactivate/link/unlink/list/search/custody
│   ├── internal_audit_service.py    # NOVO: programas/auditorias/checklist/findings + state machine
│   ├── internal_audit_report_service.py  # NOVO: snapshot + reuso controlled_document/signature
│   ├── internal_audit_export_service.py  # NOVO: PDF (reusa padrão soa_export_service/reportlab)
│   ├── traceability_service.py      # NOVO: timeline agregada (read-only)
│   └── audit_metrics_service.py     # NOVO: dashboard do módulo
├── utils/evidence_storage.py        # REUSO (sem mudança funcional)
├── helpers/
│   ├── permissions.py               # +5 permissões nos papéis
│   └── classification_access.py     # REUSO p/ acesso ao conteúdo
├── settings.py                      # +enums (EvidenceStatus/EvidenceEventType/SgsiArtifactType/
│                                    #  InternalAuditStatus/AuditFindingType/AuditChecklistResult) +
│                                    #  DocType.internal_audit_report + AUDIT_CODE_PREFIX
├── services/dashboard_service.py    # +card de readiness (DashboardModuleId.internal_audit)
├── main.py                          # registra os 3 routers novos
└── alembic/versions/<rev>_cross_evidence_internal_audit.py   # NOVO (merge dos 2 heads + migração 008)

wtnadmin/src/app/
├── core/{models.ts, permissions.ts, api.ts}   # tipos + 5 permissões + helpers de upload/blob
├── shared/evidence-panel/                       # NOVO: painel de evidências reutilizável
├── pages/evidence-repository/                    # NOVO: repositório central pesquisável
├── pages/internal-audit/                         # NOVO: programas + auditorias (lista)
├── pages/internal-audit-detail/                  # NOVO: condução (checklist+findings+relatório)
├── pages/internal-audit-dashboard/               # NOVO: cards do módulo
├── pages/soa|risk-detail|asset-detail|gap-analysis/  # embutem o evidence-panel + timeline
└── app.routes.ts                                 # rotas com permissionGuard
```

**Structure Decision**: Web application monorepo. Domínio novo `evidence_*` (transversal) + domínio
novo `internal_audit_*`. Reuso máximo de `evidence_storage`, `controlled_document_service`,
`document_versions`, `signature_service`, `soa_export`/reportlab, `classification_access`,
`tenant_scope`/RLS, auditoria e `dashboard_service`.

## Phase 0 — Research

Ver [research.md](research.md). Decisões consolidadas (todas resolvidas; nenhum NEEDS CLARIFICATION
remanescente):

- Store **unificado** com vínculo polimórfico 1..N; migração das tabelas `gap_evidence*` para
  `evidence*` + criação de `evidence_link(target_type=gap_item)`; Gap router vira adaptador.
- Cifragem em repouso **herdada** do `evidence_storage` (Fernet) — a decisão de clarify (sem *novo*
  esquema de cifragem de aplicação) é satisfeita reusando a cifragem já existente, sem regressão.
- Taxonomia de alvo canônica (`SgsiArtifactType`) compartilhada por evidência e auditoria; aponta para
  linhas tenant-scoped (`soa_item`/`gap_catalog_item` ou item de avaliação/`risk`/`asset`).
- Relatório de auditoria reusa o ciclo de Documento Controlado (novo `DocType`); gate duro só na
  aprovação por completude.
- Migration resolve os **dois heads** atuais (`a9b0c1d2e308` Feature 007 + `d3e4f5a6b217` Feature 013)
  como **merge**.

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md): entidades, enums, relacionamentos, máquina de estados e migração do
  008.
- [contracts/openapi.yaml](contracts/openapi.yaml): endpoints de `/evidence`, `/internal-audit`,
  `/traceability` e adaptação do Gap.
- [quickstart.md](quickstart.md): roteiro E2E (anexar evidência transversal, repositório central,
  auditoria→constatações→relatório, timeline, isolamento de tenant, regressão do 008).
- Agent context: atualizar a referência do plano nos marcadores `<!-- SPECKIT START/END -->` do
  `CLAUDE.md`.

## Complexity Tracking

Sem violações de constitution — seção não aplicável.
