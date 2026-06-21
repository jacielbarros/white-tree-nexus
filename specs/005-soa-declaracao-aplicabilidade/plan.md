# Implementation Plan: Statement of Applicability (SoA) — Declaração de Aplicabilidade

**Branch**: `005-soa-declaracao-aplicabilidade` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-soa-declaracao-aplicabilidade/spec.md`

## Summary

Módulo da **Declaração de Aplicabilidade (SoA)** exigida pela cláusula 6.1.3 d): para cada controle
do **Anexo A** (93 controles), registra aplicabilidade, justificativa de inclusão tipada, justificativa
de exclusão, riscos tratados, status de implementação, responsável, prazo e evidências esperadas/
referências — **consolidando a avaliação corrente do Gap Analysis** (Módulo 2) num **Documento
Controlado** versionado e exportável (PDF). Reusa intensivamente os primitivos existentes:
`controlled_document_service` + `document_versions` (versão imutável; novo `DocType.soa`),
`tenant_scope`+RLS, RBAC, `audit_service`, política de classificação (Módulo 1) e — opcionalmente na
aprovação — a assinatura avançada do Motor 003 (`signature_service`/`FormSignature`). A detecção de
divergência é **derivada por comparação com o valor vivo do item de Gap** (sem snapshot por campo).

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, slowapi, Redis ·
PrimeNG 21, Angular Signals. Reusa `controlled_document_service`, `signature_service`,
`audit_service`, `tenant_scope`, `permissions`, `classification_access`. **Nova dependência:**
`reportlab` (geração de PDF server-side, pure-Python, sem libs nativas — ver research.md).

**Storage**: PostgreSQL (Alembic + `create_all()` no startup). RLS em todas as tabelas novas
(por-tenant). A versão imutável da SoA reusa a tabela compartilhada `document_versions`.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory) · Vitest + Angular TestBed. Teste de
isolamento de tenant **obrigatório**.

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`)
+ **RLS** no PostgreSQL — idêntico ao restante da plataforma. Todas as tabelas novas (`soa`,
`soa_item`, `soa_item_event`) carregam `tenant_id`. A SoA lê o Gap Analysis **da mesma organização**
(via `scoped_query`), nunca cross-tenant.

**Performance Goals**: padrão de aplicação web. A SoA tem ~93 itens por organização — volume pequeno;
a única operação mais pesada é a geração de PDF (sob demanda, server-side), aceitável de forma síncrona.

**Constraints**: backward-compatible/aditivo; versão da SoA append-only (gatilho já existente em
`document_versions`); consolidação **aditiva e idempotente** (não sobrescreve edição manual — sinaliza
divergência); exportação reflete **exatamente** o snapshot da versão escolhida.

**Scale/Scope**: multi-tenant; ~93 itens por org; 5 user stories; 3 tabelas novas + 3 enums + 1
extensão de `DocType`; telas: matriz da SoA e versões/exportação (+ assinatura opcional reusando 003).

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checado após a Phase 1 (design) — ver fim.*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: `soa`, `soa_item`, `soa_item_event` passam por `scoped_query`/
  `tenant_scope` + RLS; a leitura do Gap Analysis de origem usa o mesmo escopo; cross-tenant ⇒
  404/403 + audit. (Princípio I — fail-closed.)
- [x] **RBAC**: `require_permission(...)` em todo endpoint; novas permissões `view_soa`, `manage_soa`,
  `approve_soa`; assinatura opcional reusa `sign_form` do 003 (SEC-002).
- [x] **Auditoria**: consolidar do Gap, criar/editar item, mudar aplicabilidade/status, reconciliar,
  enviar para revisão, aprovar, emitir versão e **exportar** ⇒ `AuditService.log_from_request`
  (sem PII/conteúdo confidencial). (Princípio III)
- [x] **Integridade/versionamento**: versão da SoA = `DocumentVersion` imutável (gatilho append-only
  existente); histórico de item em `soa_item_event` append-only. (SEC-005 / Princípio IV)
- [x] **Dados sensíveis**: conteúdo da SoA (justificativas, riscos, referências) é confidencial de
  negócio — protegido por isolamento + RBAC + política de classificação (Módulo 1); nunca em
  logs/erros. Sem field-encryption neste módulo (default aceito, análogo ao Gap). (Princípio V)

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novo router `soa.py`
  registrado em `main.py`; config/enlikes em `settings.py`+`load_dotenv()`; sem middleware novo.
- [x] Frontend: standalone; `input()/output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelos SQLAlchemy **+** migration Alembic (idempotente, conforme diretiva); todas as
  tabelas de domínio com `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path + falhas (aplicável sem razão de inclusão ⇒ 422; N/A sem
  justificativa ⇒ 422; aprovar sem revisão ⇒ 409; aprovar SoA incompleta ⇒ 422; aprovar como
  Consultor ⇒ 403; versão imutável) + **isolamento de tenant** planejados antes da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência cross-tenant.

> **Sem violações de isolamento.** A única nova dependência (reportlab) é uma lib de renderização sem
> efeito sobre o modelo de segurança. Nenhuma exceção arquitetural a registrar (diferente da 004, que
> tinha o seed compartilhado). **GATE: PASS.**

## Project Structure

### Documentation (this feature)

```text
specs/005-soa-declaracao-aplicabilidade/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1 (openapi.yaml)
└── tasks.md             # Phase 2 (/speckit.tasks — NÃO criado aqui)
```

### Source Code (repository root)

```text
wtnapp/
├── models/
│   └── soa_model.py                 # Soa + SoaItem + SoaItemEvent (todos com tenant_id + RLS)
├── schemas/
│   └── soa_schema.py                # Pydantic (Create/Update/Response; ConfigDict from_attributes)
├── routers/
│   └── soa.py                       # /soa: get, consolidate, items PUT, reconcile, divergences,
│                                    #   submit-review, approve, versions, export (PDF)
├── services/
│   ├── soa_consolidation_service.py # consolida a avaliação corrente do Gap → itens da SoA (aditivo)
│   └── soa_export_service.py        # gera PDF (reportlab) a partir do snapshot da versão
├── settings.py                       # +DocType.soa, +SoaImplementationStatus, +SoaInclusionReason
├── helpers/permissions.py            # +view_soa, manage_soa, approve_soa
├── main.py                           # registra o router soa
├── alembic/versions/<rev>_soa_module.py  # 3 tabelas + RLS + gatilho append-only (idempotente)
└── test/
    ├── test_soa.py                  # get + edição + validações (inclusão/exclusão)
    ├── test_soa_consolidation.py    # consolidação + mapeamento de status + idempotência
    ├── test_soa_divergence.py       # detecção de divergência (valor vivo) + reconcile explícito
    ├── test_soa_version.py          # submit-review→approve, imutabilidade, 409/403/422, assinatura
    ├── test_soa_export.py           # PDF reflete a versão selecionada; auditado
    └── test_tenant_isolation_soa.py # cross-tenant 404 + audit

wtnadmin/src/app/pages/
├── soa/                             # matriz da SoA: 93 controles por tema, editar, consolidar,
│                                    #   divergências + reconciliar
└── soa-versions/                    # enviar p/ revisão, aprovar (+assinatura opcional), listar,
                                     #   exportar PDF, comparar
```

**Structure Decision**: monorepo web; backend por domínio (model/schema/router/services) reusando os
serviços transversais (Documento Controlado, assinatura, auditoria, classificação); frontend com
páginas lazy `pages/soa` e `pages/soa-versions`, registradas em `app.routes.ts` com
`permissionGuard('view_soa')` e links no shell.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Nova dependência `reportlab` | FR-015/US4 exigem exportar a SoA como documento (PDF) fiel à versão imutável; o auditor de certificação consome esse artefato | Print-to-PDF no navegador não garante fidelidade ao snapshot nem auditabilidade server-side; weasyprint exige libs nativas (GTK) problemáticas no Windows. reportlab é pure-Python, sem deps nativas. |

## Phase 0 — Research

Ver [research.md](research.md): decisões sobre (1) consolidação a partir da avaliação corrente do Gap
(mapeamento de status, aditivo/idempotente, preservação de edição manual); (2) detecção de divergência
por valor vivo (sem snapshot) e reconciliação explícita; (3) SoA como Documento Controlado via
`controlled_document_service` (novo `DocType.soa`) + assinatura opcional do Motor 003; (4) geração de
PDF (reportlab) a partir do `content_snapshot` da versão; (5) validação de completude antes da
aprovação; (6) modelagem das razões de inclusão tipadas (multi-valor).

## Phase 1 — Design & Contracts

- [data-model.md](data-model.md): entidades (`Soa`, `SoaItem`, `SoaItemEvent`), campos,
  relacionamentos, enums, transições e regras de validação.
- [contracts/openapi.yaml](contracts/openapi.yaml): endpoints REST do módulo.
- [quickstart.md](quickstart.md): roteiro E2E (consolidar → editar/validar → divergência/reconciliar
  → revisar/aprovar → exportar PDF → isolamento).

## Post-Design Constitution Re-Check

Sem violações de isolamento; todas as tabelas novas têm `tenant_id`+RLS; versão e histórico de item
append-only; RBAC e auditoria cobertos; exportação e consolidação auditadas; teste de isolamento
planejado. Única complexidade registrada: dependência `reportlab` (renderização, sem impacto de
segurança). **GATE: PASS.**
