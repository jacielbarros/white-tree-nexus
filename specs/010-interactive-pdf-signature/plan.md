# Implementation Plan: Preview Interativo e Posicionamento Visual de Assinatura em PDF

**Branch**: `010-interactive-pdf-signature` | **Date**: 2026-06-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/010-interactive-pdf-signature/spec.md`

## Summary

Evoluir a Feature 009 para permitir preview inline de PDFs controlados, posicionamento visual de
selo de assinatura, persistencia auditavel da posicao confirmada no preview e congelamento dessa
posicao no documento assinado. A solucao estende o dominio transversal `print_documents`, mantendo
assinatura eletronica interna no MVP e preparando metadados/abstracao para futura assinatura
PAdES/ICP-Brasil.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy sincrono, Pydantic v2, Alembic, ReportLab,
cryptography/Fernet, python-jose, slowapi, Redis; Angular 21, PrimeNG 21, Signals, Reactive Forms,
`pdfjs-dist` para visualizacao controlada do PDF no frontend.

**Storage**: PostgreSQL para metadados, posicoes, snapshots, assinatura e eventos; PDFs continuam no
storage cifrado local da Feature 009 (`DOCUMENT_STORAGE_DIR` + `FIELD_ENCRYPTION_KEY`). Novas
migrations devem ser idempotentes e reconciliar tabelas existentes.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory + storage temporario) e Vitest + Angular
TestBed. Testes obrigatorios: happy path, falhas principais, isolamento de tenant, validacao de
coordenadas, areas bloqueadas, preview expirado/stale, e assinatura final com selo na posicao
congelada.

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB com `tenant_id` em todas as novas entidades de posicao e
custodia; queries passam por `helpers/tenant_scope.scoped_query` ou contexto de organizacao central.
RLS em PostgreSQL reforca defesa em profundidade. Acesso cross-tenant retorna 404/403 e gera audit.

**Performance Goals**: abrir preview inline em ate 5 segundos apos preview gerado; revisar,
posicionar e iniciar assinatura em ate 2 minutos para PDFs de ate 20 paginas; confirmacao de posicao
e validacao de assinatura em menos de 2 segundos em condicoes locais normais.

**Constraints**: PAdES/ICP-Brasil real fica fora do MVP; selo visual interno nao pode ser apresentado
como assinatura digital criptografica; posicoes persistidas usam coordenadas canonicas da pagina PDF
em pontos, origem inferior esquerda; zoom/viewport/scroll sao apenas camada visual; storage,
renderizacao, validacao, permissao e tenant isolation sao fail-closed.

**Scale/Scope**: integra tres telas existentes (Contexto, Gap Analysis, SoA), um componente
compartilhado de viewer/posicionamento, extensoes no router `/print-documents`, novas tabelas para
posicoes confirmadas/congeladas, e contratos para layout/page metrics/placement/sign.

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar apos a Phase 1 (design).*

**Seguranca (Core Principles I-V):**

- [x] **Isolamento de tenant**: posicoes, snapshots e eventos terao `tenant_id`; endpoints usam
  `get_org_context`/`scoped_query`; acesso cross-tenant retorna 404/403 + audit.
- [x] **RBAC**: preview inline segue permissoes de visualizacao dos modulos; posicionar/assinar
  segue permissoes de aprovacao ja usadas pela Feature 009.
- [x] **Auditoria**: abrir preview inline, confirmar posicao, assinar, baixar/verificar e tentativas
  negadas geram audit sanitizado e eventos locais append-only.
- [x] **Integridade de evidencias/artefatos**: posicoes confirmadas sao versionadas/append-only; ao
  assinar, a posicao valida e congelada e preservada junto ao documento assinado.
- [x] **Dados sensiveis**: conteudo de PDF/snapshot/storage key nao entra em logs/audit/erros;
  visualizacao respeita classificacao e storage cifrado existente.

**Arquitetura (Regras que nao dobram):**

- [x] Backend: sem repository layer; SQLAlchemy sincrono; `get_db()` central; sem middleware novo;
  router existente `print_documents` sera estendido.
- [x] Frontend: standalone components, `input()`/`output()`, `inject()`, control flow nativo,
  OnPush, Signals e Reactive Forms.
- [x] Schema: modelos SQLAlchemy + migrations Alembic idempotentes; novas entidades tenant-scoped
  tem `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: planejar testes backend/frontend para happy path, falhas, coordenadas,
  areas bloqueadas, tenant isolation e build.
- [x] Mensagens de erro nao vazam stack/tabela/storage key/path interno nem existencia de recurso de
  outro tenant.

## Project Structure

### Documentation (this feature)

```text
specs/010-interactive-pdf-signature/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- openapi.yaml
`-- tasks.md
```

### Source Code (repository root)

```text
wtnapp/
|-- models/print_document_model.py          # estender com placement e signed placement
|-- schemas/print_document_schema.py        # schemas de layout, placement, sign method
|-- routers/print_documents.py              # endpoints de inline preview/layout/placement/sign
|-- services/document_signature_service.py  # persistencia/assinatura com placement congelado
|-- services/print_render_service.py        # page metrics e selo visual posicionado
|-- services/print_template_service.py      # politica de default/blocked areas no template
|-- settings.py                             # enums de signature method/placement origin
|-- alembic/versions/                       # migration idempotente da feature 010
`-- test/                                  # testes print document placement/viewer

wtnadmin/src/app/
|-- core/models.ts                          # tipos de layout/placement/sign method
|-- core/api.service.ts                     # metodos layout/inline-pdf/placement/sign
|-- shared/document-preview/                # integrar viewer inline e fluxo de sign
|-- shared/pdf-signature-viewer/            # novo viewer/posicionador reutilizavel
|-- pages/context-overview/
|-- pages/gap-analysis/
`-- pages/soa/
```

**Structure Decision**: manter a feature no dominio transversal `print_documents`, com componente
frontend compartilhado para visualizar/posicionar e sem duplicar logica nas telas de origem.

## Phase 0: Research

Ver [research.md](research.md). Todas as decisoes tecnicas de planejamento foram resolvidas sem
pendencias.

## Phase 1: Design & Contracts

- Modelo de dados: [data-model.md](data-model.md)
- Contrato OpenAPI: [contracts/openapi.yaml](contracts/openapi.yaml)
- Quickstart/validacao: [quickstart.md](quickstart.md)
- Contexto de agente atualizado em [AGENTS.md](../../AGENTS.md)

## Post-Design Constitution Check

- [x] Entidades novas preservam tenant scope, auditoria e append-only quando representam custodia.
- [x] Endpoints novos seguem mapeamento de permissao da Feature 009 e classificacao/sensibilidade.
- [x] Posicao do selo e congelada antes da assinatura final; documentos assinados permanecem
  imutaveis mesmo com mudancas futuras no preview/template.
- [x] Validacao de coordenadas e areas bloqueadas e fail-closed.
- [x] PAdES/ICP-Brasil fica fora do MVP, mas metadados distinguem metodo interno de metodos
  criptograficos futuros.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
