# Implementation Plan: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

**Branch**: `009-signable-print-documents` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-signable-print-documents/spec.md`

## Summary

Implementar uma capacidade transversal para gerar PDFs controlados dos artefatos principais do SGSI
(Contexto consolidado, Gap Analysis e SoA), permitir preview com snapshot temporario, baixar PDF
preliminar marcado como "Nao assinado / Preview", assinar eletronicamente com permissoes de aprovacao
do modulo de origem e preservar documento final imutavel com template versionado, hash, storage seguro
e trilha de auditoria.

A abordagem reutiliza a fundacao existente de tenant scope, RBAC, `DocumentVersion`, classificacao,
audit log e motor inicial de assinatura, mas adiciona modelos proprios para templates imprimiveis,
previews, documentos assinados, snapshots e assinaturas documentais. A renderizacao PDF usa
`reportlab`, ja presente no backend, para manter compatibilidade com o ambiente Windows do projeto.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (sincrono), Pydantic v2, Alembic, python-jose,
slowapi, Redis, `reportlab>=4.0` para PDF, hashlib/json/pathlib da stdlib, cryptography/Fernet via
`FIELD_ENCRYPTION_KEY` para PDF em repouso; PrimeNG 21, Angular Signals, Reactive Forms.

**Storage**: PostgreSQL para metadados, templates, previews, snapshots, assinaturas e eventos
(Alembic + `create_all()` no startup). PDFs preliminares e finais ficam em filesystem local
configuravel por `.env` (`DOCUMENT_STORAGE_DIR`), com chaves opacas e cifragem em repouso usando
`FIELD_ENCRYPTION_KEY`. Conteudo de PDF nao fica em audit log nem em respostas de erro.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory + `tmp_path` para storage de documentos).
Vitest + Angular TestBed para componentes/servicos Angular.

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB com `tenant_id` obrigatorio em previews, documentos assinados,
snapshots, assinaturas, eventos e templates de organizacao. Queries de dominio usam
`helpers/tenant_scope.scoped_query`; templates padrao do sistema sao registros globais somente leitura
(`scope=system`, `tenant_id=NULL`) e nunca contem dados de tenant. Tentativas cross-tenant retornam
404/403 generico e geram audit. As novas tabelas tenant-scoped recebem RLS no PostgreSQL como defesa
em profundidade.

**Performance Goals**: preview para Contexto, Gap ou SoA em ate 30 segundos em condicoes normais;
assinatura + download do PDF final em menos de 2 minutos; listagem historica paginavel por tipo
documental; PDF gerado em memoria apenas ate limite configuravel (`DOCUMENT_MAX_PDF_BYTES`, default
20 MB) antes de gravar no storage; renderizacao protegida por timeout configuravel
(`DOCUMENT_RENDER_TIMEOUT_SECONDS`, default 30) com erro claro e sem PDF parcial.

**Constraints**: assinatura e download final sao fail-closed quando storage, cifragem, renderizacao ou
hash falhar; preview expirado/stale nao pode ser assinado; organizacao suspensa bloqueia preview,
assinatura, listagem sensivel, verificacao e download; `FIELD_ENCRYPTION_KEY` ausente bloqueia
storage de PDF; dados minimos ausentes e variaveis obrigatorias de template sem valor retornam erro
acionavel; audit details nao incluem conteudo do documento, PDF, storage key, path interno, tokens ou
PII; PDFs preliminares nunca exibem selo/identificador de documento assinado.

**Scale/Scope**: 1 router transversal, 1 servico de snapshot por tipo documental, 1 renderer PDF, 1
util de storage, 7 modelos/tabelas novas, seeds de 3 templates padrao, integracoes UI em Contexto,
Gap Analysis e SoA, tela simples de templates para Admin da organizacao, testes backend/frontend.
Escopo MVP cobre Contexto consolidado, Gap Analysis e SoA; modelagem prepara Gap Baseline e
Form Response sem migrar todos os fluxos legados imediatamente.

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar apos a Phase 1 (design).*

**Seguranca (Core Principles I-V):**

- [x] **Isolamento de tenant**: previews, documentos assinados, snapshots, assinaturas, eventos e
  templates de organizacao possuem `tenant_id`; routers usam `scoped_query`; acesso cross-tenant
  retorna 404/403 generico e gera audit; RLS planejado no PostgreSQL.
- [x] **RBAC**: preview/download preliminar seguem permissao de visualizacao do modulo de origem;
  assinatura segue permissao de aprovacao do modulo de origem; templates customizados exigem
  `manage_print_templates` ou papel Admin da organizacao conforme mapeamento em `permissions.py`.
- [x] **Auditoria**: preview, download preliminar, assinatura, download final, verificacao, criacao e
  ativacao/desativacao de template e tentativas negadas chamam `AuditService.log_from_request()`
  sem conteudo sensivel.
- [x] **Integridade de evidencias/artefatos**: documento assinado, snapshot e assinatura sao
  append-only; cada versao preserva template versionado, fingerprint do artefato, SHA-256 do
  conteudo/PDF, responsavel e data/hora.
- [x] **Dados sensiveis**: PDFs e snapshots podem conter PII/confidencialidade; storage cifrado em
  repouso via `FIELD_ENCRYPTION_KEY`; erros/audit/logs nao expoem conteudo, path ou storage key.

**Arquitetura (Regras que nao dobram):**

- [x] Backend: sem repository layer; SQLAlchemy sincrono; `get_db()` central; novo router registrado
  em `main.py`; configuracoes em `settings.py`; sem middleware novo.
- [x] Frontend: standalone; `inject()`; control flow nativo; `OnPush`; Signals; Reactive Forms com
  `NonNullableFormBuilder` para preview/sign/templates.
- [x] Schema: modelos SQLAlchemy + migration Alembic idempotente para novas tabelas e seeds; modelos
  tenant-scoped possuem `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: planejar testes de happy path, stale preview, permissoes, classificacao, storage
  fail-closed, audit e isolamento cross-tenant antes da implementacao.
- [x] Mensagens de erro nao vazam stack/tabela/storage key/path interno nem existencia de recurso de
  outro tenant.

**Resultado do gate**: PASS. Sem violacoes constitucionais.

## Project Structure

### Documentation (this feature)

```text
specs/009-signable-print-documents/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/openapi.yaml
|-- checklists/requirements.md
`-- tasks.md                 # Phase 2 output (/speckit.tasks; nao criado aqui)
```

### Source Code (repository root)

```text
wtnapp/
|-- models/print_document_model.py          # NOVO: templates, previews, signed docs, snapshots, events
|-- schemas/print_document_schema.py        # NOVO: DTOs de template, preview, assinatura, historico
|-- routers/print_documents.py              # NOVO: /print-documents/*
|-- services/print_snapshot_service.py      # NOVO: snapshots de Contexto, Gap e SoA
|-- services/print_render_service.py        # NOVO: renderizacao ReportLab a partir de template versionado
|-- services/document_signature_service.py  # NOVO: assinatura interna generica para documentos
|-- utils/document_storage.py               # NOVO: storage local cifrado, hash, leitura segura
|-- settings.py                             # EDITADO: DOCUMENT_STORAGE_DIR, TTL, limites, enums
|-- main.py                                 # EDITADO: include_router(print_documents.router)
|-- models/__init__.py                      # EDITADO: registrar modelos para create_all/Alembic
|-- data/print_template_seed.py             # NOVO: templates padrao Contexto, Gap, SoA
|-- alembic/versions/                      # NOVO: revision Feature 009 de documentos imprimiveis
`-- test/
    |-- test_print_documents.py
    |-- test_print_document_templates.py
    `-- test_tenant_isolation_print_documents.py

wtnadmin/src/app/
|-- core/models.ts                          # EDITADO: PrintDocument*, PrintTemplate*
|-- core/api.service.ts                     # EDITADO: endpoints de preview/sign/download/templates
|-- shared/document-preview/                # NOVO: modal/painel de preview e assinatura
|-- pages/context/                          # EDITADO: acao "Pre-visualizar relatorio"
|-- pages/gap-analysis/                     # EDITADO: acao "Gerar documento" / historico
|-- pages/soa/                              # EDITADO: acao "Pre-visualizar/assinar"
`-- pages/print-templates/                  # NOVO: administracao simples de templates controlados
```

**Structure Decision**: criar dominio transversal `print_documents` para evitar duplicar logica de
PDF/preview/assinatura em Contexto, Gap e SoA. Os modulos de origem continuam donos dos dados e das
permissoes; o novo modulo recebe `document_type` e delega snapshot para servicos especializados.

## Phase 0: Research

Ver [research.md](research.md). Todas as decisoes de planejamento foram resolvidas sem pendencias.

## Phase 1: Design & Contracts

- Modelo de dados: [data-model.md](data-model.md)
- Contrato OpenAPI: [contracts/openapi.yaml](contracts/openapi.yaml)
- Quickstart/validacao: [quickstart.md](quickstart.md)
- Contexto de agente atualizado em [AGENTS.md](../../AGENTS.md)

## Post-Design Constitution Check

- [x] Tabelas novas mantem tenant scope; templates globais do sistema nao armazenam dado de tenant.
- [x] Endpoints tem mapeamento explicito de permissao por tipo documental e regras de classificacao.
- [x] Audit log e eventos locais nao registram conteudo do PDF, snapshot sensivel, storage key ou path.
- [x] Preview stale e storage/renderizacao falhos bloqueiam assinatura de modo fail-closed.
- [x] Testes obrigatorios incluem isolamento de tenant, permissoes, stale preview, imutabilidade,
  hash/verificacao, watermark de preview e falhas de storage.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |

## Completion Notes

- Backend implementado com modelos, migration, storage cifrado local, seed idempotente de templates,
  renderer ReportLab, snapshots deterministicos para Contexto/Gap/SoA, preview, assinatura,
  historico e verificacao de integridade.
- Frontend implementado com componentes compartilhados de preview/assinatura e historico,
  integracao nas telas de Contexto, Gap Analysis e SoA, e tela simples de administracao de templates.
- Migration validada em PostgreSQL com `alembic upgrade head` executado duas vezes; a segunda execucao
  nao reaplicou alteracoes.
- Validacoes executadas: 16 testes backend da feature, 123 testes frontend, `npm run build` e
  `git diff --check`.
- Warnings conhecidos: avisos legados de Pydantic/Starlette no backend e warnings de budget Angular
  para bundle inicial/component styles, sem erro de build.
