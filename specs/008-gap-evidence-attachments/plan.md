# Implementation Plan: Anexos e Evidencias na Matriz do Gap Analysis

**Branch**: `008-gap-evidence-attachments` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-gap-evidence-attachments/spec.md`

## Summary

Implementar evidencias documentais reais por item da Matriz do Gap Analysis, separadas da orientacao
canonica da Feature 007 ("Evidencias esperadas"). A abordagem cria entidades tenant-scoped para
evidencia, versao de evidencia e evento de evidencia, com metadados no PostgreSQL, conteudo em storage
local configuravel por `.env`, integridade por SHA-256, remocao logica, versionamento e audit log para
acoes sensiveis. A UI entra no painel lateral da matriz, logo apos a orientacao de avaliacao.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (sincrono), Pydantic v2, Alembic,
`python-multipart` (nova dependencia backend necessaria para upload multipart do FastAPI),
`cryptography.fernet` para cifragem em repouso via `FIELD_ENCRYPTION_KEY`, hashlib/pathlib do Python,
PrimeNG 21, Angular Signals.

**Storage**: PostgreSQL para metadados e eventos (Alembic + `create_all()` no startup). Conteudo dos
arquivos em filesystem local configuravel via `EVIDENCE_STORAGE_DIR`, cifrado em repouso com Fernet
usando `FIELD_ENCRYPTION_KEY`, com `EVIDENCE_MAX_FILE_BYTES` default 20 MB e allowed extensions/MIME
configuraveis em `settings.py`.

**Testing**: pytest + FastAPI TestClient (SQLite in-memory + `tmp_path` para storage) · Vitest +
Angular TestBed

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo: `wtnapp/` backend + `wtnadmin/` frontend)

**Tenant Isolation Strategy**: shared-DB com `tenant_id` em todas as tabelas de evidencia
(`gap_evidence`, `gap_evidence_version`, `gap_evidence_event`) e consultas via
`helpers/tenant_scope.scoped_query`. O storage fisico usa chaves opacas derivadas de tenant/evidence/
version, mas o caminho interno nunca aparece em resposta, erro ou audit log. PostgreSQL recebe RLS nas
novas tabelas como defesa em profundidade.

**Performance Goals**: listar evidencias do item em uma chamada leve por item selecionado; uploads ate
20 MB por arquivo no MVP; hash incremental quando possivel e limite de 20 MB para manter a cifragem em
memoria controlada; download por streaming/FileResponse apos decifragem.

**Constraints**: isolamento de tenant fail-closed; upload/download fail-closed se storage ou cifragem
falhar; upload deve falhar se `FIELD_ENCRYPTION_KEY` exigida nao estiver configurada; conteudo de
arquivo e paths internos nunca em audit/errors; listagem de metadados nao gera audit; conteudo
aberto/baixado e mutacoes geram audit; historico/inativas visiveis apenas para `manage_gap`.

**Scale/Scope**: 1 router novo, 3 modelos/tabelas novas, 1 util de storage, 1 migration, extensao do
painel lateral de `gap-analysis`, modelos TS e testes backend/frontend. Escopo inicial limitado a
Matriz do Gap Analysis; modelagem prepara reuso futuro em SoA/auditoria/plano de acao sem implementar
essas integracoes.

## Constitution Check

*GATE: Deve passar antes da Phase 0 (research). Re-checar apos a Phase 1 (design).*

**Seguranca (Core Principles I-V):**

- [x] **Isolamento de tenant**: todas as novas tabelas tem `tenant_id`; routers usam `scoped_query`;
  acesso cross-tenant retorna 404/403 generico e gera audit. RLS planejado no PostgreSQL.
- [x] **RBAC**: listagem ativa/corrente exige `view_gap`; upload, substituicao, inativacao e
  historico exigem `manage_gap`; download segue regra de classificacao da spec.
- [x] **Auditoria**: upload, download/visualizacao de conteudo, substituicao, inativacao e tentativas
  negadas chamam `AuditService.log_from_request()` sem conteudo, path interno, tokens ou PII.
- [x] **Integridade de evidencias/artefatos**: cada arquivo vira versao imutavel com SHA-256,
  `version_number`, autor e data; substituicao cria nova versao; eventos sao append-only.
- [x] **Dados sensiveis**: conteudo fica fora de logs/erros/audit. Classificacao obrigatoria com
  default `uso_interno`. Arquivos de evidencia sao cifrados em repouso via `FIELD_ENCRYPTION_KEY`;
  paths sao opacos e segregados por tenant.

**Arquitetura (Regras que nao dobram):**

- [x] Backend: sem repository layer; SQLAlchemy sincrono; `get_db()` central; novo router registrado em
  `main.py`; config em `settings.py`; sem middleware novo.
- [x] Frontend: standalone; `inject()`; control flow nativo; `OnPush`; Signals; forms reativos para
  upload/classificacao/descricao.
- [x] Schema: modelos SQLAlchemy + migration Alembic para as novas tabelas; todos os modelos de dominio
  da feature tem `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: planejar testes de happy path, invalid uploads, permission/classification,
  historico, audit, fail-closed e isolamento cross-tenant antes da implementacao.
- [x] Mensagens de erro nao vazam stack/tabela/path interno nem existencia de recurso de outro tenant.

**Resultado do gate**: PASS. Sem violacoes constitucionais.

## Project Structure

### Documentation (this feature)

```text
specs/008-gap-evidence-attachments/
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
|-- models/gap_evidence_model.py          # NOVO: GapEvidence, GapEvidenceVersion, GapEvidenceEvent
|-- schemas/gap_evidence_schema.py        # NOVO: DTOs de metadata, upload, historico
|-- routers/gap_evidence.py               # NOVO: endpoints em /gap/assessment/items/{item_id}/evidences
|-- utils/evidence_storage.py             # NOVO: storage local, hash, validacao, cifragem, streaming
|-- settings.py                           # EDITADO: EVIDENCE_STORAGE_DIR/MAX/ALLOWED defaults
|-- main.py                               # EDITADO: include_router(gap_evidence.router)
|-- models/__init__.py                    # EDITADO: registrar modelos para create_all/Alembic
|-- alembic/versions/<rev>_gap_evidence.py
`-- test/
    |-- test_gap_evidence.py
    `-- test_tenant_isolation_gap_evidence.py

wtnadmin/src/app/
|-- core/models.ts                         # EDITADO: GapEvidence*, Classification aliases
|-- core/api.service.ts                    # EDITADO: upload FormData + download Blob helpers, se util
`-- pages/gap-analysis/
    |-- gap-analysis.ts                    # EDITADO: secao "Evidencias anexadas" no painel
    `-- gap-analysis.spec.ts               # EDITADO: render, upload, permissions, empty state
```

**Structure Decision**: manter o dominio dentro do modulo Gap Analysis, com router proprio para evitar
inflar `gap_assessment.py`. Storage fica em `utils/` por ter efeito colateral; regras de negocio leves
ficam no router/helper local, seguindo o padrao atual do backend.

## Phase 0: Research

Ver [research.md](research.md). Todas as decisoes de planejamento foram resolvidas sem pendencias.

## Phase 1: Design & Contracts

- Modelo de dados: [data-model.md](data-model.md)
- Contrato OpenAPI: [contracts/openapi.yaml](contracts/openapi.yaml)
- Quickstart/validacao: [quickstart.md](quickstart.md)
- Contexto de agente atualizado em [AGENTS.md](../../AGENTS.md)

## Post-Design Constitution Check

- [x] Tabelas novas continuam tenant-scoped e com RLS planejado.
- [x] Endpoints tem gates de RBAC e regras por classificacao documentados no contrato.
- [x] Audit log e evento de evidencia nao registram conteudo nem path de storage.
- [x] Versionamento preserva historico; remocao fisica por usuario comum nao existe.
- [x] Testes obrigatorios incluem isolamento de tenant, permissoes, invalid uploads e audit.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| N/A | N/A | N/A |
