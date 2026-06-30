# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> **Codinome provisório:** "White Tree Nexus". Faça find-replace pelo nome real do produto.
> Prefixo de diretórios: `wtn` (`wtnapp/` backend, `wtnadmin/` admin web).

## Project Overview

A **White Tree Nexus** é uma plataforma **SaaS multi-tenant** de Gestão de SGSI e Compliance
**ISO/IEC 27001:2022**, organizada como um **monorepo**:

| Directory | Module | Stack |
|-----------|--------|-------|
| `wtnapp/` | Backend API | Python, FastAPI, SQLAlchemy, PostgreSQL |
| `wtnadmin/` | Admin/Web (frontend) | Angular 21, PrimeNG 21, Signals, TypeScript 5.9 |

O produto acompanha a jornada de implementação do SGSI de múltiplas organizações (tenants),
com isolamento estrito de dados entre elas. Ver os princípios inegociáveis em
[`.specify/memory/constitution.md`](.specify/memory/constitution.md) — **leia antes de
qualquer spec, plano ou implementação.**

## Common Commands

### Backend
```bash
# Activate virtual environment (Windows)
source <venv>/Scripts/activate

# Install dependencies
pip install -r requirements.txt

# Run dev server
uvicorn wtnapp.main:app --reload

# Run all tests
pytest wtnapp/test/

# Run a single test file
pytest wtnapp/test/test_auth.py

# Database migrations
alembic revision --autogenerate -m "description"
alembic upgrade head
alembic downgrade -1
```

### Admin Frontend
```bash
cd wtnadmin
npm install
npm start                       # dev server on http://localhost:4200
npm run build                   # production build
npm test                        # Vitest unit tests
```

### Required `.env` variables (ponto de partida — ajuste por feature)
```
DATABASE_URL=postgresql://postgres:password@localhost/wtndatabase
JWT_SECRET_KEY=<64-byte hex>
TOKEN_EXPIRY_MINUTES=20
RESET_TOKEN_EXPIRY_MINUTES=30
REDIS_URL=redis://localhost:6379/0
TRUSTED_PROXY_COUNT=0
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_PASSWORD_REQUEST=3/minute
RATE_LIMIT_FORM_TOKEN=20/minute   # endpoints públicos do motor de workflow (token)
RATE_LIMIT_FORM_OTP=5/minute      # OTP de assinatura eletrônica (mais restrito)
MAX_LOGIN_ATTEMPTS=5
SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM
CSP_ENABLED=true
HSTS_ENABLED=false        # opt-in — só ligar em produção HTTPS
HSTS_MAX_AGE=31536000
# --- Proteção de dados sensíveis em repouso ---
FIELD_ENCRYPTION_KEY=     # Fernet (urlsafe-b64 32B) p/ cifrar campos sensíveis (risco/PII/evidência)
# --- Storage de evidências (escolher na feature de Evidências) ---
EVIDENCE_STORAGE_DIR=./evidence_store/   # local; trocar por S3/objeto em produção
EVIDENCE_MAX_FILE_BYTES=20971520          # 20 MB
# --- Recursos de IA (Módulo 10, opt-in por organização) ---
AI_FEATURES_ENABLED=false
ANTHROPIC_API_KEY=
AI_MODEL=claude-sonnet-4-6                # default; usar os modelos Claude mais recentes
```

---

## Backend Architecture (`wtnapp/`)

### Layers
1. **`main.py`** — FastAPI app com metadata, CORS, IntegrityError handler, health check com
   verificação de DB, registra todos os routers via `app.include_router(...)`. Todo novo router
   é registrado aqui.
2. **`database/database.py`** — engine SQLAlchemy, `SessionLocal` e **`get_db()` centralizado** —
   importado por todos os routers e helpers. NÃO criar `get_db()` local.
3. **`routers/`** — um arquivo por domínio; queries SQLAlchemy direto. A maior parte da lógica
   de negócio vive aqui.
4. **`models/`** — modelos ORM SQLAlchemy (`<domain>_model.py`). Base declarativa em `models/base.py`.
5. **`schemas/`** — modelos Pydantic de request/response (`<domain>_schema.py`). Padrão
   `<Domain>Base / Create / Update / Response`.
6. **`services/`** — lógica reutilizável/isolada: `audit_service.py`, `crypto_service.py`,
   `notification_service.py`.
7. **`helpers/`** — utilitários: `permissions.py` (RBAC), `tenant_scope.py` (escopo de tenant),
   `settings_helper.py`.
8. **`utils/`** — integrações com efeito colateral: e-mail (SMTP), storage de evidências, IA.
9. **`settings.py`** — lê `.env` via `load_dotenv()`; define enums e parâmetros configuráveis.

Não há **repository layer** e não há **middleware** além de CORS, rate limiting e (se justificado)
resolução de tenant.

### Multi-tenant — invariante central
- Todo modelo de domínio carrega `tenant_id` (FK para `organizations`).
- A resolução do tenant do usuário autenticado e o filtro por tenant vivem em
  `helpers/tenant_scope.py` (ponto único e não-contornável). Nunca filtre tenant ad-hoc no router.
- Acesso cross-tenant ⇒ `404`/`403` sem revelar existência + audit log.
- Toda feature tem **teste de isolamento de tenant** dedicado.

### RBAC (Perfis de Acesso)
Papéis: **Super Admin da plataforma** (único cross-tenant), **Admin da organização**,
**Consultor**, **Cliente**, **Gestor**, **Dono de processo**, **Dono de controle**,
**Auditor interno**, **Colaborador convidado**. Permissões granulares verificadas via
`require_permission()` de `helpers/permissions.py`. Super Admin tem bypass de permissão,
**mas não de auditoria** — suas ações são especialmente logadas.

### Audit Logs
- `AuditService.log_from_request()` registra metadata de toda operação relevante.
- Usa `SessionLocal` própria (persiste mesmo em rollback, falha em silêncio).
- Trilha **append-only**: nunca editar/apagar registros.
- **NUNCA** logar PII, senhas, tokens, chaves ou conteúdo confidencial de evidência.

### Authentication
- JWT (HS512) assinado com `JWT_SECRET_KEY`, emitido por `routers/auth.py`. Rate limited.
- Claims: `sub`, `tenant_id` (ou lista, p/ consultor multi-org), `role`, `iss`, `exp`, `jti`.
- Login lockout após `MAX_LOGIN_ATTEMPTS`. Logout revoga `jti` no Redis (fail-open).

### Módulos do produto (preencher conforme as features chegam)
Sequência da esteira guiada (ordem ISO): 1) Diagnóstico e Contexto · 2) Gap Analysis ·
3) Gestão de Ativos/Processos/Escopo · 4) Gestão de Riscos (Ameaças & Vulnerabilidades →
Avaliação 6.1.2 → Tratamento 6.1.3) · 5) SoA (consolidada a partir do tratamento de risco) ·
6) Evidências / Auditoria / Melhoria Contínua (PDCA). Evolução: IA · Dashboards avançados.
**Nota de sequência:** a SoA é output do tratamento de risco (6.1.3 d); o módulo de SoA atual
consolida o Gap como **Pré-SoA** até a consolidação definitiva pós-tratamento. Cada módulo nasce de
uma spec própria ([Spec Kit](.specify/)) e ganha sua seção aqui quando implementado.

#### Fundação Multi-Tenant (Feature 001 — implementada)
Base de todos os módulos. Spec/plano em `specs/001-fundacao-multi-tenant/`.
- **Backend** (`wtnapp/`): organizações (ciclo de vida), bootstrap do Super Admin, auth JWT HS512
  (login/bloqueio/logout), redefinição de senha, convites + aceite, RBAC, isolamento de tenant e
  auditoria append-only. Routers: `bootstrap`, `auth`, `organizations`, `invitations`,
  `memberships`, `me`. Escopo de tenant central em `helpers/tenant_scope.py` (+ RLS no PostgreSQL);
  RBAC em `helpers/permissions.py` (`require_permission` / `require_super_admin`); auditoria em
  `services/audit_service.py`. Contexto de organização via header `X-Org-Context`. O aceite de
  convite reaproveita usuário existente (ex.: Super Admin/Consultor multi-org): quem já tem conta
  **confirma o vínculo sem redefinir a senha**; `GET /invitations/lookup` (público) informa à tela
  se é usuário novo (pede senha) ou existente (só confirma). E-mail de convite leva link
  `/accept?token=` e texto adequado a cada caso.
- **Frontend** (`wtnadmin/`): core (AuthStore com Signals, interceptor, guards, `ApiService`) e
  telas login, senha (esqueci/redefinir), aceite de convite, shell c/ seletor de organização,
  organizações e usuários/convites.
- **Testes**: `pytest wtnapp/test` (inclui isolamento de tenant) e `npm test` em `wtnadmin/`.
- **Migrations**: `wtnapp/alembic/` (schema inicial + RLS/gatilho append-only). Ainda **não**
  validado contra PostgreSQL real (RLS é PG-only; testes rodam em SQLite).

#### Módulo 1 — Diagnóstico e Contexto (Feature 002 — implementada)
Cláusula 4 do SGSI. Spec/plano em `specs/002-diagnostico-contexto/`. Segue o padrão
[Documento Controlado SGSI](docs/iso27001-documento-controlado.md).
- **Backend** (`wtnapp/`): Diagnóstico inicial (`routers/diagnostic.py`), Análise de Contexto 4.1
  (PESTEL/SWOT + impacto — `routers/context_analysis.py`), Mapa de Partes Interessadas 4.2
  (Poder×Interesse/Mendelow — `routers/stakeholders.py`), Declaração de Escopo 4.3 com referências
  de versão a Contexto/Partes (`routers/scope.py`), visão consolidada + sugestões heurísticas
  (`routers/context_overview.py` + `services/suggestion_service.py`). Ciclo de vida do documento
  controlado (rascunho→revisão→aprovação, identificador/versão/classificação/retenção) em
  `services/controlled_document_service.py`. Versões imutáveis em `document_versions` (gatilho
  append-only); "1 em vigor + rascunho paralelo" — a versão vigente é o ponteiro
  `current_version_id` do artefato e a obsolescência de uma referência é **derivada por recência**
  (`is_superseded`), nunca por mutação de status (preserva o append-only). Aprovação exige
  `approve_context_document` (Admin da organização). Acesso por classificação configurável por org
  (`helpers/classification_access.py` + `models/classification_policy_model.py`, default RBAC).
  Um conjunto por organização (índice único em `tenant_id`).
- **Frontend** (`wtnadmin/`): telas `diagnostic/`, `context-analysis/`, `stakeholders/`, `scope/`,
  `context-overview/` (lazy, `permissionGuard('view_context')`), com histórico de versões e ações
  enviar-para-revisão/aprovar; links no shell.
- **Testes**: `pytest wtnapp/test` (diagnóstico, contexto, partes, escopo, versionamento/append-only,
  classificação, sugestões + isolamento de tenant) e `npm test` em `wtnadmin/`.
- **Migrations**: `wtnapp/alembic/versions/c3d4e5f6a702_context_module.py` (tabelas + RLS + gatilho
  append-only de `document_versions`); `alembic check` sem drift. **Pendente**: validação E2E
  manual no browser (T038) e contra PostgreSQL real.

#### Motor de Workflow de Preenchimento (Feature 003 — implementada)
Capacidade transversal. Spec/plano em `specs/003-workflow-preenchimento/`.
- **Backend** (`wtnapp/`): `FormTemplate` (CRUD de template por org, kind/status, schema JSON) em
  `routers/form_templates.py`; `FormAssignment` (ciclo de vida: pending→in_progress→submitted→signed
  →completed + return + cancel) em `routers/form_assignments.py`; respondente externo via token
  (apenas hash em `respondent_token_hash`) em `routers/form_respond.py`; assinatura eletrônica avançada
  (Lei 14.063/2020) com SHA-256 canônico, DocumentVersion imutável e OTP por e-mail (fail-closed)
  em `services/signature_service.py`; máquina de estados e snapshot do template em
  `services/form_workflow_service.py`; integração com Diagnóstico em `services/diagnostic_intake.py`;
  política de assinatura por org (única ou dupla) em `routers/form_signature_policy.py`.
  Notificações de atribuição/lembrete/OTP em `services/notification_service.py` (best-effort).
  Trilha append-only em `models/form_assignment_event_model.py` (SQLite+PG triggers).
  Permissões: `assign_form`, `fill_form`, `sign_form`, `view_form`.
- **Testes backend**: `pytest wtnapp/test/test_form_assignment_lifecycle.py` (ciclo de vida + devolução/cancelamento),
  `test_form_respond_token.py` (token externo + OTP), `test_form_signature.py` (assinatura + integridade),
  `test_tenant_isolation_forms.py` (isolamento), `test_diagnostic_intake.py` (US5). 37 testes, todos passando.
- **Testes frontend**: `form-templates.spec.ts`, `form-assignments.spec.ts`, `form-respond.spec.ts`. 30 testes, todos passando.
- **Migrations**: `wtnapp/alembic/versions/d6e7f8a9b005_workflow_module.py` (6 tabelas + RLS +
  triggers append-only em `form_assignment_events` e `form_signatures`).
- **Frontend** (`wtnadmin/`): `pages/form-templates/` (CRUD de template + auto-chave + arquivar/
  desarquivar; campos com metadados ricos: `section`, `order`, `mask`, `help_text`, `options` —
  persistidos no `schema` JSON, sem migration),
  `pages/form-assignments/` (lista + criar/atribuir com **dropdown de membros** + wizard/linha do tempo
  + assinar + devolver/cancelar/lembrar + **toggle de política de assinatura dupla**),
  `pages/form-fill/` (assumir/preencher/salvar/enviar), `pages/form-respond/` (rota pública tokenizada
  `/respond/:token` + OTP + assinatura avançada sem auth). Links no shell. A tela `pages/diagnostic/`
  foi **repaginada**: deixou de ter form-builder inline — agora lista os **templates de diagnóstico**
  (com ação Atribuir) e exibe o **diagnóstico vigente** (de `form_intake`). Permissões
  (`assign_form`, `fill_form`, `sign_form`, `view_form`) espelhadas em `core/permissions.ts`.
- **Testes manuais**: roteiro E2E em `docs/guia-de-testes-workflow.md` (membro, externo/token+OTP,
  devolução, política dupla, consumo do diagnóstico, isolamento). Fluxo externo exige *catcher* SMTP local.

#### Módulo 2 — Gap Analysis ISO/IEC 27001:2022 (Feature 004 — implementada)
Spec/plano em `specs/004-gap-analysis/`. Avalia aderência da organização às cláusulas 4–10 e os 93
controles do Anexo A da norma.
- **Arquitetura dois níveis**: catálogo compartilhado (`gap_seed_version`/`gap_seed_item`, sem `tenant_id`,
  somente leitura) + cópia editável por org (`gap_catalog_item` com `tenant_id`+RLS). Adoção aditiva
  e idempotente (novos itens como `not_filled`, personalizações preservadas, removidos marcados como
  `is_discontinued`).
- **Backend** (`wtnapp/`): seed ISO 27001:2022 em `data/iso27001_seed.py` (100 itens: 7 cláusulas + 93
  controles A.5–A.8); `services/gap_seed_service.py` (`load_seed`/`adopt_seed`); `services/gap_metrics_service.py`
  (aderência ponderada 1.0/0.5/0.0, N/A e not_filled excluídos; denominador zero ⇒ None); routers
  `gap_catalog.py` (catálogo + adoção + CRUD custom), `gap_assessment.py` (matriz, itens, dashboard,
  lacunas, submit-review/approve/baselines/compare), `gap_assignment.py` (atribuição de condução:
  membro ou externo via token). Baseline reusa `controlled_document_service` com `DocType.gap_baseline`.
  Trilha de item append-only em `gap_assessment_item_event` (SQLite + PG triggers). Permissões:
  `view_gap`, `manage_gap`, `approve_gap_baseline`.
- **Testes backend** (38 testes, todos passando): `test_gap_assessment.py` (9), `test_tenant_isolation_gap.py`
  (5), `test_gap_metrics.py` (6), `test_gap_catalog.py` (4), `test_gap_baseline.py` (6), `test_gap_assignment.py` (8).
- **Migration**: `wtnapp/alembic/versions/e7f8a9b0c106_gap_analysis_module.py` (7 tabelas + RLS + triggers
  append-only). `down_revision="d6e7f8a9b005"`.
- **Frontend** (`wtnadmin/`): 4 telas implementadas — `pages/gap-analysis/` (matriz + condução),
  `pages/gap-dashboard/` (indicadores + lacunas), `pages/gap-catalog/` (catálogo + adoção), `pages/gap-baselines/`
  (congelar/aprovar/listar/comparar). Rotas registradas em `app.routes.ts` com `permissionGuard('view_gap')`.
  Links no shell. Métodos genéricos `get/post/put/patch` adicionados ao `ApiService`. 69 testes frontend passando.
- **Pendente**: validação E2E manual, alembic upgrade no postgres real.

#### Módulo 3 — Statement of Applicability / SoA (Feature 005 — implementada)
Cláusula 6.1.3 d). Spec/plano em `specs/005-soa-declaracao-aplicabilidade/`. Declaração de
Aplicabilidade dos 93 controles do Anexo A, **consolidando a avaliação corrente do Gap Analysis**
(Módulo 2) num **Documento Controlado** versionado e exportável em PDF.
- **Backend** (`wtnapp/`): `models/soa_model.py` (`Soa` único por org, `SoaItem`, `SoaItemEvent`
  append-only; todos `tenant_id`+RLS); `services/soa_consolidation_service.py` (consolidação aditiva/
  idempotente da avaliação corrente do Gap + `compute_divergence` por valor vivo); `services/
  soa_export_service.py` (PDF via **reportlab** a partir do `content_snapshot` da versão); router
  `soa.py` (`GET /soa`, `consolidate`, `PUT items/{id}`, `items/{id}/reconcile`, `divergences`,
  `submit-review`, `approve`, `versions`, `versions/{id}/export`). Versão imutável reusa
  `controlled_document_service` + `document_versions` (novo `DocType.soa`); assinatura avançada
  **opcional** na aprovação (selo SHA-256 no snapshot). Mapeamento de status Gap→SoA e enums
  (`SoaImplementationStatus`, `SoaInclusionReason`, `GAP_TO_SOA_STATUS`) em `settings.py`. Permissões
  `view_soa`/`manage_soa`/`approve_soa`. Acesso por classificação aplicado na exportação.
- **Testes backend** (24 testes, todos passando): `test_soa.py`, `test_soa_consolidation.py`,
  `test_soa_divergence.py`, `test_soa_version.py`, `test_soa_export.py`, `test_tenant_isolation_soa.py`.
- **Migration**: `wtnapp/alembic/versions/f8a9b0c1d207_soa_module.py` (3 tabelas + RLS + gatilho
  append-only; **idempotente**). `down_revision="e7f8a9b0c106"`. Validada no PostgreSQL real
  (upgrade/downgrade/roundtrip + idempotência com `create_all`).
- **Frontend** (`wtnadmin/`): `pages/soa/` (matriz dos 93 controles por tema, editar, consolidar,
  divergência + reconciliar) e `pages/soa-versions/` (revisar/aprovar + assinatura opcional, listar
  versões, exportar PDF). Rotas com `permissionGuard('view_soa')`, links no shell, `getBlob` no
  `ApiService`. 81 testes frontend passando (todo o admin).
- **E2E validado** (browser, Postgres real): consolidar→matriz, edição/validação, divergência/
  reconciliação, gate de incompletude, aprovação assinada e exportação de PDF. Seed de cenário em
  `scripts/seed_soa_demo.py`; serviços via `.claude/launch.json` (backend :8000 + frontend :4200).

##### Evolução — SoA Normativa dirigida pelo Tratamento de Riscos (Feature 013 — implementada)
Promove o Pré-SoA à Declaração de Aplicabilidade **normativa (6.1.3 d)** dirigida pelo Plano de
Tratamento de Riscos (Feature 012). Spec/plano em `specs/013-soa-normativa-risco/`. **Evolução
in-place** (não cria módulo novo).
- **Backend** (`wtnapp/`): consolidação passa a ter **passo dirigido por risco** consumindo o insumo
  read-only `risk_treatment_service.soa_feed` (vínculo controle←risco): controles do feed "1ª-mão"
  viram Aplicável + razão `risk_treatment` + **riscos estruturados** (coluna nova `soa_item.risk_links`
  JSON; texto legado `risks_treated` coexiste). Aditivo/idempotente; razões manuais nunca removidas;
  drift vira **divergência por fonte** (`compute_risk_divergence`, `DivergenceField.source` `gap`|`risk`),
  reconciliável por `source` (remover a única razão ⇒ item aplicável-**incompleto**, sem auto-flip).
  **Gate duro = rótulo da versão**: o snapshot grava `soa_kind` (`SoaKind` `normative` se
  `RiskPlan.current_version_id` vigente, senão `pre_soa`) + `risk_plan_version_number`; aprovação
  bloqueada só por completude (`_incomplete_refs`). `GET /soa` expõe `readiness` (kind/risk_plan_approved/
  pending/out-of-scope). PDF (`soa_export_service`) enriquecido (rótulo + razões tipadas + riscos
  estruturados + origem). Enums novos `SoaKind`/`SoaDivergenceSource` + `SOA_KIND_LABELS` em
  `settings.py`. **Sem novas permissões, sem novas dependências, sem router novo.** Não altera Risco
  (012)/Gap (004) — só consome.
- **Migration**: `wtnapp/alembic/versions/d3e4f5a6b217_soa_risk_normative.py` (add column
  `soa_item.risk_links`, idempotente). `down_revision="c2d3e4f5a116"` (head, Feature 012).
- **Testes backend**: `test_soa_risk_consolidation.py`, `test_soa_risk_divergence.py`,
  `test_soa_gate_normative.py` + extensões a `test_soa_export.py` e `test_tenant_isolation_soa.py`
  (consolidação nunca agrega feed de outro tenant). Fixtures `link_risk_to_control`/`approve_risk_plan`.
- **Frontend** (`wtnadmin/`): `pages/soa` ganha banner **Pré-SoA × SoA normativa** (readiness + pendências
  + notice fora-Anexo-A), chips de razão incl. **Risco**, badge de **origem**, riscos estruturados e
  **divergência/reconciliação por fonte** (gap/risk); `pages/soa-versions` exibe o **rótulo `kind`** por
  versão e o estado de readiness. Tipos em `core/models.ts` estendidos (`SoaRiskLink`, `SoaReadiness`,
  `SoaKind`, `source`/`source_value` na divergência). Sem rotas novas.
- **Pendente**: E2E browser + `alembic upgrade head` no Postgres real.

#### Dashboard de Conformidade (Feature 006 — implementada)
Home da organização — capacidade **transversal de leitura/agregação**. Spec/plano em
`specs/006-compliance-dashboard/`. **Sem novo modelo de domínio, sem migration.**
- **Backend** (`wtnapp/`): endpoint único `GET /dashboard` (`routers/dashboard.py`) que compõe, via
  `services/dashboard_service.py`, os módulos existentes — Contexto (Cláusula 4), Gap Analysis e SoA
  — em KPIs + cards (status normalizado, progresso, responsável/prazo do item de menor prazo futuro,
  alerta de revisão vencida, atalho de próxima ação). Reusa `gap_metrics_service`,
  `controlled_document_service.review_overdue` + baselines, modelos de contexto/gap/soa,
  `document_versions`. DTOs em `schemas/dashboard_schema.py` (`DashboardCardStatus`:
  `not_started`/`draft`/`in_review`/`in_force`/`needs_review`/`error`). Nova permissão
  `view_dashboard` (todos os papéis exceto Colaborador convidado). **Gating de card** por permissão
  de módulo (`view_context`/`view_gap`/`view_soa`); **fail-open por card** (falha em um módulo não
  derruba os demais); isolamento de tenant fail-closed via `get_org_context`. **Auditoria**: sucesso
  não loga (home); tentativas não autorizadas já logadas pelas dependencies centrais. KPI de Anexo A
  conta os **93 controles** (dimensão `annex_a`); `critical_gaps` = gaps com `priority == critical`.
  Série de aderência (P2) derivada das baselines aprovadas do Gap (≥2). Registrado em `main.py`.
- **Frontend** (`wtnadmin/`): `pages/dashboard/` é a home (`/app` → `dashboard`); **uma** chamada a
  `GET /dashboard` (substitui o `forkJoin` de 3 endpoints), KPIs + cards + sparkline de evolução;
  `view_dashboard` espelhado em `core/permissions.ts`. Parte da Revisão de UX (design do Claude
  Design em `docs/design/`).
- **Testes**: `wtnapp/test/test_dashboard.py` (agregação/KPIs/estados/RBAC/gating/fail-open/overdue/
  série) + `test_tenant_isolation_dashboard.py` (11 no total) e `dashboard.spec.ts` (frontend, 88 no
  admin). **Pendente**: E2E manual no browser (login + Postgres real).

#### Orientação de Avaliação por Item — Gap (Feature 007 — implementada)
Enriquece a matriz do Gap (Módulo 2) com orientação por item. Spec/plano em `specs/007-gap-item-guidance/`.
- **Conteúdo de plataforma** (sem `tenant_id`): novos campos de orientação em `gap_seed_item`
  (`referencia`, `como_avaliar`[JSON lista], `evidencias_esperadas`[JSON lista], `nota`; `objective`
  já existia). Legenda global em `gap_legend_entry` (4 Status + 4 Prioridade). Trilha append-only em
  `gap_guidance_event` (SQLite+PG triggers). Conteúdo PT-BR **original** dos 100 itens em
  `data/iso27001_seed.py` (IP: sem reproduzir texto normativo ISO).
- **Leitura**: `GET /gap/guidance` (`view_gap`) devolve itens + legenda; a matriz resolve a orientação
  pelo vínculo `gap_catalog_item.seed_item_id → gap_seed_item` (já existente). **Edição**:
  `PUT /gap/guidance/items|legend` + `GET /gap/guidance/events` (`require_super_admin`, sem contexto
  de org) com trilha + audit. `services/gap_guidance_service.py` + `routers/gap_guidance.py` (em
  `main.py`). `load_seed` semeia a legenda e preenche orientação **só quando vazia** (preserva edição
  do admin). Migration `a9b0c1d2e308` (`down_revision="f8a9b0c1d207"`), idempotente, **sem RLS**
  (tabelas de plataforma — mesma exceção do seed da Feature 004).
- **Frontend**: seção "Orientação de avaliação" (read-only) no painel da matriz + legenda recolhível
  (`pages/gap-analysis/`); área administrativa `pages/gap-guidance-admin/` (rota com `superAdminGuard`,
  link no shell só p/ Super Admin). Distingue "evidências esperadas" (orientação) de "evidência
  existente" (`evidence_ref` da org). Painel preparado para a futura feature de evidências anexadas.
- **Testes**: `test_gap_guidance.py` + `test_gap_guidance_rbac.py` (10) e
  `gap-analysis.spec.ts`/`gap-guidance-admin.spec.ts` (104 no admin). **Pendente**: E2E browser +
  `alembic upgrade` no Postgres real.

#### Módulo 3 — Gestão de Ativos / Processos / Escopo (Feature 011 — implementada)
Inventário tenant-scoped de ativos, processos e elementos de escopo do SGSI — base dos próximos
módulos (ameaças → vulnerabilidades → riscos → tratamento → SoA definitivo → evidências). Spec/plano
em `specs/011-asset-process-scope/`.
- **Backend** (`wtnapp/`): domínio `asset_*` com 4 tabelas (`asset_items`, `asset_relationships`,
  `asset_gap_links`, `asset_item_events`), todas `tenant_id`+RLS; trilha de item append-only (triggers
  SQLite+PG). Router `routers/assets.py` (`/assets`): CRUD + arquivamento lógico, `summary`/`dashboard`,
  `context-sources`, relacionamentos, `gap-links`, `history`. Serviços `services/asset_service.py`
  (geração de código por tipo imutável, criticidade `max(C,I,A)` com override+divergência, derivação de
  revisão, validações condicionais de escopo, diffing+eventos com justificativa nas mudanças críticas)
  e `services/asset_metrics_service.py` (KPIs + distribuições, exclui arquivados). Enums + `ASSET_CODE_
  PREFIXES`/`ASSET_REVIEW_DUE_SOON_DAYS` em `settings.py`. Permissões `view_asset`/`manage_asset`.
  **Sem cifragem de campo** (clarificação): proteção por RBAC + isolamento + "sem PII bruta". O módulo
  Gap **não** é alterado (exibição reversa deferida). Registrado em `main.py`.
- **Frontend** (`wtnadmin/`): `pages/assets/` (lista + cards + filtros/busca + criar + "criar a partir
  do contexto"), `pages/asset-detail/` (dados/CIA/escopo/responsáveis/relacionamentos/gaps/placeholders
  de módulos futuros/histórico/edição/arquivamento) e `pages/assets-dashboard/` (distribuições). Rotas
  `assets`/`assets/:id`/`assets-dashboard` com `permissionGuard('view_asset')`; links no shell;
  `view_asset`/`manage_asset` espelhados em `core/permissions.ts`.
- **Testes**: `test_assets.py`, `test_tenant_isolation_assets.py`, `test_asset_relationships.py`,
  `test_asset_gap_links.py`, `test_asset_history.py`, `test_asset_metrics.py`,
  `test_asset_context_sources.py` (35 testes, todos passando) e `assets.spec.ts`/`asset-detail.spec.ts`/
  `assets-dashboard.spec.ts` (154 no admin). **Pendente**: E2E browser + `alembic upgrade` no Postgres real.
- **Migration**: `wtnapp/alembic/versions/b1c2d3e4f015_asset_process_scope_module.py`
  (`down_revision="a6b7c8d9e014"`, idempotente, RLS + triggers append-only).

#### Módulo de Riscos — Avaliação (6.1.2) e Tratamento (6.1.3) (Feature 012 — implementada)
Módulo de Risco do MVP (entre Ativos e SoA definitiva), **um módulo de engenharia** que a esteira
exibe como **três fases**: Ameaças/Vulnerabilidades → Avaliação → Tratamento. Spec/plano em
`specs/012-risk-management/`.
- **Backend** (`wtnapp/`): domínio `risk_*` — **12 tabelas** (2 semente de plataforma sem `tenant_id`:
  `threat_seed_item`/`vulnerability_seed_item`; **10 tenant-scoped** com RLS: `risk_methodology`,
  `org_threat`, `org_vulnerability`, `asset_threat_link`, `asset_vulnerability_link`, `risk`,
  `risk_asset_link`, `risk_treatment_control`, `risk_plan`, `risk_events`), trilha `risk_events`
  append-only (triggers SQLite+PG). **Metodologia** configurável por org (`risk_methodology_service`,
  default 5x5 in-code — gate suave): escalas, matriz prob×impacto→nível, critério de aceitação por
  nível, mapa CIA→impacto; recálculo em massa ao alterar. **Catálogos** semente+cópia editável da org
  (`risk_catalog_service`, adoção idempotente; seed PT-BR original em `data/iso27005_seed.py`) com
  vínculos a ativos e a gaps. **Registro de risco** (`risk_service`): cenário (ameaça+vuln+0..n ativos),
  código `RSK-####`, impacto derivado da CIA `max(C,I,A)` com override justificado, nível pela matriz,
  marcação acima/abaixo do critério, heat map. **Tratamento** (`risk_treatment_service`): opção
  (mitigar/aceitar/transferir/evitar), controles do **catálogo de Gap da org** (resp.+prazo) ou custom,
  re-pontuação residual, aceitação (justificativa+dono), **Plano de Tratamento** como Documento
  Controlado (`controlled_document_service` + `document_versions`, novo `DocType.risk_treatment_plan`,
  **gate duro**: aprovar exige riscos avaliados; assinatura avançada opcional). **Insumo da SoA** exposto
  read-only via `GET /risk/soa-feed` (vínculo controle←risco + razão "tratamento de risco") — o módulo
  **não escreve na SoA**. Métricas/heat map em `risk_metrics_service`; card de readiness na esteira
  (`dashboard_service._risk_card`, `DashboardModuleId.risk`). Router `risk.py` (`/risk`, 26 endpoints) em
  `main.py`. Permissões `view_risk`/`manage_risk`/`approve_risk_plan`. Enums + `RISK_CODE_PREFIX` +
  `DEFAULT_RISK_METHODOLOGY` em `settings.py`. **Não altera o modelo de Ativos** (só consome/exibe nos
  placeholders).
- **Frontend** (`wtnadmin/`): `pages/risk-methodology`, `risk-catalog` (Fase 1), `risks` (Fase 2 —
  lista+filtros+busca+heat map+criar), `risk-detail` (avaliação+tratamento+controles+aceitação+
  histórico), `risk-treatment-plan` (Fase 3 — submeter/aprovar/assinar/versões+SoA-feed), `risk-dashboard`.
  Rotas com `permissionGuard('view_risk')`; grupo "Gestão de Riscos" no shell; `pages/asset-detail`
  estendida para preencher os placeholders (ameaças/vulnerabilidades/riscos/controles via
  `GET /risk/assets/{id}/links`). `view_risk`/`manage_risk`/`approve_risk_plan` em `core/permissions.ts`.
- **Testes**: backend `test_risk_assessment.py`, `test_risk_catalog.py`, `test_risk_treatment.py`,
  `test_risk_plan.py`, `test_risk_methodology.py`, `test_risk_history.py`, `test_risk_metrics.py`,
  `test_tenant_isolation_risk.py` (36 testes, todos passando; suíte backend completa verde) e
  `risks/risk-detail/risk-catalog/risk-methodology/risk-treatment-plan/risk-dashboard.spec.ts`
  (171 no admin, todos passando).
- **Migration**: `wtnapp/alembic/versions/c2d3e4f5a116_risk_management_module.py`
  (`down_revision="b1c2d3e4f015"`, idempotente, RLS nas 10 tenant + triggers append-only). **Pendente**:
  E2E browser + `alembic upgrade` no Postgres real + `scripts/seed_risk_demo.py`. **Nota**: existe um bug
  **pré-existente** (módulo Gap) que faz `alembic upgrade head` falhar a partir de DB zerado
  (`gap_seed_item.referencia` em migration de backfill) — independente deste módulo.

#### Módulo 5a — Repositório Transversal de Evidências + Auditoria Interna (Feature 014 — implementada)
Etapa final da esteira (Evidências/Auditoria/PDCA). Spec/plano em `specs/014-cross-evidence-internal-audit/`.
Generaliza o módulo de evidências do Gap (008) e adiciona auditoria interna (9.2). **Backend + frontend
completos e testados (US1–US8; backend 361 testes, admin 197); migração aplicada e validada no
PostgreSQL real.** Prepara a base para a Feature 5b (NC/ações corretivas 10.2, análise crítica 9.3,
PDCA 10.1) **sem implementá-la**. Pendente apenas o roteiro E2E manual no browser (`quickstart.md`).
- **Fase 1 — Repositório transversal de evidências** (`wtnapp/`): domínio unificado `evidence_*`
  (4 tabelas: `evidence`, `evidence_version`, `evidence_link`, `evidence_event`; todas `tenant_id`+RLS;
  versão/evento append-only). A evidência é objeto de 1ª classe vinculável a **1..N** artefatos via
  `evidence_link` **polimórfico** (`SgsiArtifactType`: `soa_item`/`gap_item`/`risk`/`asset`/`audit_finding`,
  extensível p/ 5b) apontando para **linhas de artefato tenant-scoped**. Reusa `utils/evidence_storage`
  (upload + SHA-256 + cifragem **Fernet** em repouso), `classification_access` (acesso ao conteúdo por
  classificação) e auditoria. Serviço `services/evidence_service.py`; router `routers/evidence.py`
  (`/evidence`: repositório central pesquisável/filtrável, upload+vínculo, download, versões, inativação,
  histórico, link/unlink). **Unificação do 008**: `routers/gap_evidence.py` virou **adaptador** sobre o
  store unificado (mesmos paths/DTOs/permissões `view_gap`/`manage_gap`/audit); o modelo `GapEvidence` foi
  **removido** e os dados migrados.
- **Fase 2 — Auditoria interna (9.2)** (`wtnapp/`): domínio `internal_audit_*` (5 tabelas:
  `internal_audit_program`/`internal_audit`/`internal_audit_checklist_item`/`internal_audit_finding`/
  `internal_audit_event` append-only). Programa → auditoria (código `AUD-####`, máquina de estados
  planned→in_progress→completed/cancel) → checklist (manual + importação opcional do escopo SoA/Gap, com
  atualização de resultado) → **constatações** (5 tipos; NC maior/menor ⇒ `promotable=true` +
  `nonconformity_ref` **reservado p/ 5b**; evidência anexada via `target_type=audit_finding`).
  **Relatório** como Documento Controlado (reusa `controlled_document_service`+`document_versions`, novo
  `DocType.internal_audit_report`; **gate duro**: aprovar exige auditoria `completed` + zero itens de
  checklist `pendente`; assinatura avançada opcional SHA-256; **PDF** via `internal_audit_export_service`/
  reportlab). Serviços `internal_audit_service`/`_report_service`/`_export_service`; router
  `routers/internal_audit.py` (`/internal-audit`, 20 endpoints).
- **Transversal**: `routers/traceability.py` (`GET /traceability/timeline`, read-only, **RBAC composto**:
  view do módulo do alvo + `view_evidence`; constatações só com `view_internal_audit`); dashboard do
  módulo (`audit_metrics_service` + `GET /internal-audit/dashboard`); card de readiness **Evidências &
  Auditoria Interna** na esteira (`dashboard_service` + `DashboardModuleId.internal_audit`).
- **RBAC**: 5 permissões novas — `view_evidence`/`manage_evidence`, `view_internal_audit`/
  `manage_internal_audit`/`approve_audit_report` (nome de auditoria interna distinto de um futuro
  `view_audit` de leitura de audit logs). Enums + `DocType.internal_audit_report` + `AUDIT_CODE_PREFIX`
  em `settings.py`. **Sem novas dependências.**
- **Frontend** (`wtnadmin/`): `shared/evidence-panel` (lista/upload/download/**substituir**/**histórico**/
  inativar, gated por classificação/`manage_evidence`) embutido em `pages/soa`, `pages/risk-detail`,
  `pages/asset-detail` (o `pages/gap-analysis` mantém o painel próprio do 008, que já consome o store
  unificado); `pages/evidence-repository` (repositório central pesquisável/filtrável);
  `shared/traceability-timeline` (linha do tempo read-only) nas mesmas telas de artefato;
  `pages/internal-audit` (programas+auditorias), `pages/internal-audit-detail` (condução: checklist +
  constatações + relatório assinável/PDF) e `pages/internal-audit-dashboard` (cards do módulo). Rotas com
  `permissionGuard('view_evidence')`/`view_internal_audit` + grupo "Evidências & Auditoria" no shell;
  tipos e métodos de API em `core/models.ts`/`core/api.service.ts`; 5 permissões espelhadas em
  `core/permissions.ts`.
- **Testes backend** (361 verdes): `test_evidence_repository.py`,
  `test_tenant_isolation_evidence.py`, `test_evidence_migration_008.py`, `test_internal_audit_lifecycle.py`,
  `test_internal_audit_findings.py`, `test_internal_audit_report.py`, `test_tenant_isolation_internal_audit.py`,
  `test_traceability_timeline.py`, `test_audit_metrics.py` (+ 008/dashboard atualizados à unificação).
  **Testes frontend** (197 verdes): specs de `evidence-panel`, `evidence-repository`,
  `traceability-timeline`, `internal-audit`, `internal-audit-detail`, `internal-audit-dashboard`.
- **Migrations**: `f6a7b8c9d014_cross_evidence_repository.py` (cria `evidence_*` + RLS + triggers, migra
  dados do 008 e dropa tabelas legadas; **merge** dos dois heads anteriores `a9b0c1d2e308`+`d3e4f5a6b217`,
  idempotente) e `a7b8c9d0e015_internal_audit_module.py` (`down_revision="f6a7b8c9d014"`, 5 tabelas + RLS +
  trigger) + `b8c9d0e1f016_internal_audit_rename_current_version.py` (auto-correção idempotente:
  renomeia `internal_audit.current_report_version_id`→`current_version_id` em bancos que criaram a
  tabela via `create_all()` antes do rename; no-op em bancos novos). Head único `b8c9d0e1f016`.
  **`alembic upgrade head` aplicado e validado no PostgreSQL real**
  (a migração do 008 exigiu ordenação por causa da FK circular `evidence.current_version_id↔evidence_version`
  e do drop das tabelas legadas — resolvido). **Pendente**: apenas o E2E manual no browser.

### Schema management
Alembic migrations (`wtnapp/alembic/`) **e** `create_all()` no startup. Ao mudar tabelas,
atualizar o modelo SQLAlchemy **e** adicionar migration; não remover `create_all()`.

**Migrations DEVEM ser idempotentes** — `alembic upgrade head` precisa rodar com sucesso mesmo
quando as tabelas **já existem** (porque o `create_all()` do startup pode tê-las criado antes da
migration rodar). Regra obrigatória para toda migration nova:
- `op.create_table(...)`/`op.create_index(...)`: envolver em `if not _table_exists(conn, "<tabela>")`
  (helper `_table_exists(conn, name) -> sa.inspect(conn).has_table(name)`).
- `op.add_column(...)` em tabela existente: guardar com checagem de coluna
  (`name in [c["name"] for c in sa.inspect(conn).get_columns("<tabela>")]`), pois `create_all()` já
  cria a coluna nova em DB zerado, mas **não** a adiciona em tabela preexistente.
- Funções/triggers (PG): `CREATE OR REPLACE FUNCTION` + `DROP TRIGGER IF EXISTS` antes de `CREATE TRIGGER`.
- RLS policies (PG): `DROP POLICY IF EXISTS ...` antes de `CREATE POLICY`; `ENABLE ROW LEVEL SECURITY`
  é idempotente.
- SQLite (testes): `CREATE TRIGGER IF NOT EXISTS`.
- Seed/carga de dados: idempotente (rodar 2× não duplica).
Referência: migrations `d6e7f8a9b005` (003) e `e7f8a9b0c106` (004) já seguem esse padrão.

## Backend Key Conventions

**Router pattern:**
```python
from wtnapp.database.database import get_db

router = APIRouter(prefix="/my-domain", tags=["my-domain"])
db_dependency = Annotated[Session, Depends(get_db)]
```

**RBAC pattern:**
```python
from wtnapp.helpers.permissions import require_permission
manage_dep = Annotated[dict, Depends(require_permission("manage_something"))]
```

**Tenant scope pattern:**
```python
from wtnapp.helpers.tenant_scope import scoped_query
# scoped_query(db, Model, user) já filtra por tenant_id do usuário
```

**Audit pattern:**
```python
AuditService.log_from_request(
    db=db, request=request, operation="CREATE",
    entity_type="risk", entity_id=str(obj.id),
    details={"key": "value"}, user_id=user.get("user_id"),
)
```

**DB write pattern:** `db.add(obj)` → `db.commit()` → `db.refresh(obj)` (só ao retornar o objeto).

**Pydantic v2:** `.model_dump()`; ORM schemas com `class Config: from_attributes = True`.

**Async:** handlers podem ser `async def` mas usam SQLAlchemy síncrono — intencional. Não
introduzir `AsyncSession`.

**Language:** comentários e strings de usuário misturam Português e Inglês. Preserve o idioma
do arquivo que está editando.

---

## Admin Frontend Architecture (`wtnadmin/`)

### Stack
- **Angular 21** com standalone components (sem NgModules)
- **PrimeNG 21** (`@primeuix/themes`, preset Material)
- **Signals** (`signal()`, `computed()`) para estado
- **Vitest** (nativo via `@angular/build:unit-test`)
- **esbuild** (via `@angular/build:application`)

### Key conventions
- `input()` / `output()` functions, NUNCA `@Input()` / `@Output()`
- `inject()`, NUNCA injeção via construtor
- Control flow nativo: `@if`, `@for`, `@switch`
- `ChangeDetectionStrategy.OnPush`
- NÃO declarar `standalone: true` (é o default)
- NÃO usar sufixo `Component` no nome da classe
- Reactive Forms com `NonNullableFormBuilder`

### Structure
```
wtnadmin/src/app/
  app.ts              # Root component
  app.config.ts       # Bootstrap providers (router, PrimeNG theme)
  app.routes.ts       # Route definitions
  core/               # Singleton services, app-wide utilities
  pages/              # Feature modules (lazy-loaded routes)
  shared/             # Reusable components, directives, pipes
```

### Path aliases (tsconfig.json)
- `@app/*` → `./src/app/*`
- `@environment/*` → `./src/environments/*`

---

## What to Avoid (Global)

- Não executar query de domínio sem escopo de tenant.
- Não inventar repository layer no backend.
- Não adicionar middleware sem requisito explícito.
- Não usar `pydantic-settings`; configuração em `settings.py` com `load_dotenv()`.
- Não introduzir `AsyncSession`.
- Não esquecer de registrar novos routers em `main.py`.
- Não usar NgModules nem `@Input()`/`@Output()` decorators no Angular.
- Não editar/apagar audit logs ou histórico de evidências (append-only).

## Testing

### Backend
- Framework: pytest + FastAPI `TestClient`
- SQLite in-memory com override único e centralizado de `get_db`
- `conftest.py` isola infra real (`REDIS_URL=""`, audit em sink SQLite)
- **Teste de isolamento de tenant é obrigatório** por feature
- Helpers async: `@pytest.mark.asyncio`

### Admin Frontend
- Framework: Vitest (nativo) + Angular TestBed
- `ng test --no-watch` (ou `npm test`)
- `describe`/`it`/`expect` (globals Vitest, sem Jasmine)
- DOM: `happy-dom`

---

## Fluxo de trabalho com Spec Kit

1. `/speckit.constitution` — ratifica/ajusta os princípios (já adaptados em `.specify/memory/`).
2. `/speckit.specify` — descreve **o QUÊ** de cada feature (agnóstico de stack).
3. `/speckit.plan` — decide **o COMO** (stack, modelo de dados, estratégia de tenant), guiado
   pela constitution.
4. `/speckit.tasks` → `/speckit.implement`.

A **primeira feature deve ser a fundação multi-tenant** (organizações + auth + RBAC +
isolamento + auditoria). Ver `docs/00-fundacao-multi-tenant.md` (índice dos prompts de
specify em `docs/README.md`).

<!-- SPECKIT START -->
## Plano ativo (Spec Kit)

**Feature 014 — Repositório Transversal de Evidências + Auditoria Interna (9.2)**
(`014-cross-evidence-internal-audit`) — **implementada** (US1–US8 backend+frontend; backend 361 testes,
admin 197; migração aplicada e validada no PostgreSQL real; resta só o E2E manual no browser). Ver a
seção do módulo "Módulo 5a" acima. Feature **5a** da etapa final da esteira (Evidências/Auditoria/PDCA).
Generaliza o módulo de evidências do Gap (008) e adiciona auditoria interna; **prepara a base para a
Feature 5b** (NC/ações corretivas 10.2, análise crítica 9.3, PDCA 10.1) sem implementá-la.
- Plano: `specs/014-cross-evidence-internal-audit/plan.md` · Spec: `.../spec.md` · Research:
  `.../research.md` · Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` ·
  Quickstart: `.../quickstart.md`
- Escopo: **Fase 1** — store **unificado** `evidence_*` (evidência 1ª-classe vinculável a **1..N**
  artefatos via `evidence_link` polimórfico → `soa_item`/`gap_item`/`risk`/`asset`/`audit_finding`,
  extensível p/ 5b); reusa `utils/evidence_storage` (upload+SHA-256+Fernet), versões imutáveis,
  inativação lógica, custódia append-only, auditoria e `classification_access`; **migra** o 008 e
  mantém os endpoints do Gap via adaptador; repositório central pesquisável + painel reutilizável.
  **Fase 2** — domínio `internal_audit_*` (programa→auditoria→checklist→constatação) com constatações
  **promovíveis** (`nonconformity_ref` reservado p/ 5b) e **relatório** como Documento Controlado
  (novo `DocType.internal_audit_report`, assinatura opcional, PDF). Transversal: timeline read-only +
  dashboard do módulo + card de readiness na esteira.
- Decisões-chave (clarify 2026-06-30): (1) repositório **unificado** + evidência reutilizável 1..N +
  **migração** do 008; (2) constatação pertence à **auditoria**, vínculo a item de checklist
  **opcional**; (3) checklist **manual** + importação **opcional** do escopo SoA/Gap; (4) vínculos
  apontam para **linhas de artefato tenant-scoped** (SoA/Gap/risco/ativo), sem códigos abstratos;
  (5) proteção em repouso = **storage + acesso por classificação** (cifragem Fernet **herdada** do
  `evidence_storage`, sem novo esquema de aplicação).
- Arquitetura: domínios novos `evidence_*` (4 tabelas) + `internal_audit_*` (5 tabelas), todas
  `tenant_id`+RLS; trilhas append-only (`evidence_version`/`evidence_event`/`internal_audit_event`).
  Routers novos `evidence`/`internal_audit`/`traceability` em `main.py`; serviços `evidence_service`,
  `internal_audit_service`/`_report_service`/`_export_service`, `traceability_service`,
  `audit_metrics_service`. Reusa `controlled_document_service`+`document_versions`, `signature_service`,
  reportlab, `dashboard_service`. **5 permissões novas** (`view_evidence`/`manage_evidence`,
  `view_internal_audit`/`manage_internal_audit`/`approve_audit_report`). Enums novos +
  `DocType.internal_audit_report` + `AUDIT_CODE_PREFIX` em `settings.py`. Migration **merge** dos dois
  heads atuais (`a9b0c1d2e308` + `d3e4f5a6b217`), idempotente, com migração de dados do 008. **Sem
  novas dependências.** Frontend: `pages/evidence-repository`, `pages/internal-audit`,
  `pages/internal-audit-detail`, `pages/internal-audit-dashboard`, `shared/evidence-panel`
  (`permissionGuard`). Consome SoA/Gap/Risco/Ativo **read-only** (vínculos); não os altera.

**Feature 013 — SoA Normativa dirigida pelo Tratamento de Riscos** (`013-soa-normativa-risco`) —
**planejada** (spec + clarify + plano prontos; implementação pendente). **Evolução in-place** do módulo
de SoA (Feature 005), promovendo o Pré-SoA à Declaração de Aplicabilidade **normativa (6.1.3 d)**
dirigida pelo Plano de Tratamento de Riscos (Feature 012). **Não cria módulo novo.**
- Plano: `specs/013-soa-normativa-risco/plan.md` · Spec: `.../spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi-delta.yaml` · Quickstart: `.../quickstart.md`
- Escopo: consolidação **dirigida primariamente pelo risco** consumindo o insumo read-only
  `GET /risk/soa-feed` (vínculo controle←risco, razão `risk_treatment` + riscos tratados) — aditiva/
  idempotente, **1ª-mão** (aplica risco só a item que nunca carregou vínculo; drift vira divergência);
  **razões manuais** (legal/contratual/melhor prática) sempre preservadas; **status de implementação**
  segue o Gap; **divergência/reconciliação por fonte** (Gap **e** risco); **gate duro = rótulo da versão**
  (`SoaKind`: `pre_soa` vs. `normative` conforme exista `RiskPlan.current_version_id` vigente; aprovação
  bloqueada só por completude, FR-009a); **PDF enriquecido** (razão tipada + riscos estruturados + origem
  + rótulo). **Sem novas permissões** (`view_soa`/`manage_soa`/`approve_soa`), **sem dependências novas**.
- Decisões-chave (clarify 2026-06-29): (1) consolidação/divergência leem o **insumo vivo** do `soa-feed`;
  o **snapshot do Plano aprovado** só decide o rótulo no gate; (2) razão `risk_treatment` e `risk_links`
  geridos pela consolidação/reconciliação, **razões manuais nunca removidas**; (3) gate: aprovação sempre
  permitida, versão **rotulada** `pre_soa` vs. `normative` (= existe versão aprovada **vigente** do Plano,
  `current_version_id != null`); (4) riscos tratados = **referência estruturada** (`risk_links`: id+`RSK-####`),
  texto legado `risks_treated` coexiste; (5) consolidação para item **existente** = aditivo + sinaliza
  divergência (espelha o Gap); (6) feed aponta controle **fora do Anexo A** ⇒ **notice**, não cria/descarta;
  (7) reconciliar removendo a **única** razão (`risk_treatment`) ⇒ item **aplicável-incompleto** (bloqueia
  aprovação), sem auto-flip.
- Arquitetura: **1 mudança de schema** — coluna `risk_links` (JSON) em `soa_item`; rótulo/riscos da versão
  vivem no `content_snapshot` (sem coluna nova). Estende `soa_consolidation_service` (passo risco,
  `compute_risk_divergence`, reconcile risco), `routers/soa.py` (readiness do gate, divergência por fonte,
  rótulo no snapshot), `soa_export_service` (PDF), `soa_schema`, `settings.py` (`SoaKind`/`SoaDivergenceSource`).
  Migration `down_revision="c2d3e4f5a116"` (head atual, Feature 012), idempotente. Frontend: evolui
  `pages/soa` + `pages/soa-versions` (sem rotas novas). Consome Risco (012) e Gap (004) **read-only** — não
  os altera. Prepara o terreno para Evidências/Auditoria/PDCA (Módulo 5).

**Feature 012 — Módulo de Gestão de Riscos** (`012-risk-management`) — **planejada**
(spec + clarify + plano prontos; implementação pendente). Módulo de Risco do MVP (entre Ativos e SoA
definitiva), cobrindo **três fases num módulo**: Ameaças/Vulnerabilidades → Avaliação (6.1.2) →
Tratamento (6.1.3).
- Plano: `specs/012-risk-management/plan.md` · Spec: `.../spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: **metodologia de risco** configurável por org (default 5x5: escalas prob/impacto, matriz,
  critério de aceitação por nível, dono = membro); **catálogos** de ameaças e vulnerabilidades no padrão
  semente-de-plataforma + cópia editável por org (adoção aditiva/idempotente, base ISO 27005 PT-BR
  original), com vínculo a **ativos** e a **gaps**; **registro de risco** como cenário (0..n ativos +
  ameaça + vulnerabilidade) com **impacto derivado da CIA** (`max(C,I,A)`, override justificado), nível
  pela matriz, marcação acima/abaixo do critério e **heat map 5x5**; **tratamento** (mitigar/aceitar/
  transferir/evitar) com **controles do catálogo de Gap da org** (resp.+prazo), **re-pontuação residual**,
  **aceitação** (justificativa + dono) e **Plano de Tratamento** versionável (Documento Controlado,
  assinatura avançada opcional); **insumo da SoA** exposto como vínculo controle←risco **read-only** (sem
  escrever na SoA); preenchimento dos **placeholders do detalhe do ativo**; **histórico append-only** por
  risco; **dashboard do módulo** + card de **readiness na esteira**.
- Decisões-chave (clarify 2026-06-26): (1) impacto = `max(C,I,A)` mapeado p/ escala de 5 níveis por
  tabela configurável, override justificado; por-dimensão (C/I/D) deferido; (2) SoA = **expor vínculo
  controle←risco read-only**, o módulo **não grava na SoA** (finalização é feature futura); (3) cenário:
  ameaça+vulnerabilidade obrigatórias, **ativos opcionais** (sem ativos ⇒ impacto manual); (4) aceitação
  registrada por usuário `manage_risk` atribuída ao membro-dono (sem login/assinatura separados do dono);
  (5) metodologia é pré-requisito **suave** (default 5x5); gates duros só na **aprovação do plano** (exige
  riscos avaliados); apenas qualitativo 5x5 (sem quantitativo/Monte Carlo); residual = re-pontuação simples.
- Arquitetura: domínio novo `risk_*` — **12 tabelas** (2 semente de plataforma `threat_seed_item`/
  `vulnerability_seed_item` **sem `tenant_id`**; **10 tenant-scoped**: `risk_methodology`, `org_threat`,
  `org_vulnerability`, `asset_threat_link`, `asset_vulnerability_link`, `risk`, `risk_asset_link`,
  `risk_treatment_control`, `risk_plan`, `risk_events`) com RLS nas 10 + triggers append-only (`risk_events`).
  Router `risk.py` (`/risk`) em `main.py`; serviços `risk_methodology_service`/`risk_service`/
  `risk_catalog_service`/`risk_treatment_service`/`risk_metrics_service`; seed `data/iso27005_seed.py`.
  Reusa `controlled_document_service`+`document_versions` (novo `DocType.risk_treatment_plan`) e
  `signature_service` (assinatura opcional). Estende `dashboard_service` (`_risk_card`) e a tela
  `pages/asset-detail` (preencher placeholders) — **sem alterar o modelo de Ativos**. Novas permissões
  `view_risk`/`manage_risk`/`approve_risk_plan`; enums + `RISK_CODE_PREFIX` (`RSK-####`) +
  `DEFAULT_RISK_METHODOLOGY` em `settings.py`. Migration `c2d3e4f5a116`
  (`down_revision="b1c2d3e4f015"`, idempotente). Frontend: `pages/risk-methodology`, `risk-catalog`,
  `risks`, `risk-detail`, `risk-treatment-plan`, `risk-dashboard` (`permissionGuard('view_risk')`).
  **Sem novas dependências** (PDF deferido).

**Feature 011 — Gestão de Ativos / Processos / Escopo** (`011-asset-process-scope`) — **planejada**
(spec + clarify + plano prontos; implementação pendente). Módulo 3 do MVP.
- Plano: `specs/011-asset-process-scope/plan.md` · Spec: `.../spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: inventário tenant-scoped de ativos/sistemas/bases/processos/fornecedores/pessoas/infra/
  documentos/serviços do SGSI — base dos próximos módulos (ameaças → vulnerabilidades → riscos →
  tratamento → SoA definitivo → evidências). CRUD + arquivamento lógico; classificação CIA (4 níveis)
  + criticidade (`max(C,I,A)` com override registrado); escopo dentro/fora/em análise com validações
  condicionais; relacionamentos flexíveis entre itens; vínculo a gaps do **catálogo da própria org**;
  "criar item a partir do contexto"; histórico append-only por item; revisão periódica derivada;
  lista+filtros+busca, cards de resumo e dashboard; placeholders no detalhe p/ módulos futuros.
- Decisões-chave (clarify 2026-06-26 + research): (1) responsável/dono/custodiante = referência a
  **membros da org**; (2) integração Gap = vínculo + "Gaps relacionados" no item, **exibição reversa
  na tela do Gap deferida** (módulo Gap não é alterado); (3) **sem cifragem de campo** no MVP — RBAC +
  isolamento + "sem PII bruta" (guarda indicadores, não o dado pessoal); (4) código interno = **prefixo
  por tipo + sequência por tipo**, imutável (ex.: ATV-0001). 3 conceitos de status distintos
  (`record_status` manual, `scope_status` manual, `review_status` **derivado** de `next_review_at`).
- Arquitetura: domínio novo `asset_*` (4 tabelas: `asset_items`, `asset_relationships`,
  `asset_gap_links`, `asset_item_events`), todas com `tenant_id` + RLS; histórico append-only (triggers
  SQLite+PG). Router `assets.py` (`/assets`) em `main.py`; serviços `asset_service` + `asset_metrics_
  service`; enums + `ASSET_CODE_PREFIXES`/`ASSET_REVIEW_DUE_SOON_DAYS` em `settings.py`. Novas
  permissões `view_asset`/`manage_asset`. Migration `b1c2d3e4f015` (`down_revision="a6b7c8d9e014"`,
  idempotente). Frontend: `pages/assets`, `pages/asset-detail`, `pages/assets-dashboard`
  (`permissionGuard('view_asset')`). **Sem novas dependências.**

**Feature 007 — Orientação de Avaliação por Item (Gap Analysis)** (`007-gap-item-guidance`) —
**implementada** (10 testes backend dedicados + suíte completa verde; 104 testes frontend; E2E
browser + `alembic upgrade` no Postgres pendentes — fluxo do usuário)
- Plano: `specs/007-gap-item-guidance/plan.md` · Spec: `.../spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: orientação por item da matriz do Gap (referência/objetivo/como avaliar/evidências esperadas/
  nota) + legenda global de Status/Prioridade. **Conteúdo de plataforma compartilhado** (no
  catálogo-base `gap_seed_item`, sem `tenant_id`), **somente leitura** para a org (resolvido pelo
  vínculo `gap_catalog_item.seed_item_id → gap_seed_item`, que já existe), **editável só pelo Super
  Admin** (`require_super_admin`) com **trilha append-only** + audit. Conteúdo PT-BR **original** dos
  100 itens (IP: proibido reproduzir texto normativo ISO).
- Decisões-chave: `objetivo` já existe no seed (`objective`) e já é autorado; campos novos no seed
  (`referencia`/`como_avaliar`[JSON]/`evidencias_esperadas`[JSON]/`nota`); `como_avaliar`/`evidencias`
  = **listas de strings**; `load_seed` preenche orientação **só quando vazia** (não sobrescreve
  edição do admin); legenda em tabela `gap_legend_entry`; trilha `gap_guidance_event` (ambas
  platform-level, sem `tenant_id` — mesma exceção do seed, Feature 004). Migration
  `down_revision="f8a9b0c1d207"`. Leitura via `GET /gap/guidance` (view_gap); edição via
  `PUT /gap/guidance/items|legend` (Super Admin). MVP cobre os 100 itens.
- Prepara o terreno para a feature seguinte (evidências anexadas por item) — ver
  `docs/feature-gap-guidance-and-evidence.md`.

**Feature 006 — Dashboard de Conformidade** (`006-compliance-dashboard`) — **implementada**
(11 testes backend dedicados + suíte completa verde; 88 testes frontend; E2E browser pendente —
roda no fluxo Postgres do usuário). Endpoint `GET /dashboard`, sem migration.
- Plano: `specs/006-compliance-dashboard/plan.md`
- Spec: `specs/006-compliance-dashboard/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: home da organização — **camada de leitura/agregação** sobre Contexto (002), Gap (004) e
  SoA (005), com cards (status, progresso, responsável, prazo, alerta de revisão vencida, atalho de
  próxima ação). **Sem novo modelo de domínio, sem migration.** Tela-âncora da Revisão de UX (design
  já implementado em `wtnadmin/` a partir do handoff do Claude Design em `docs/design/`).
- Decisões-chave (clarify 2026-06-21): (1) agregação via **endpoint único `GET /dashboard`** no
  backend (não composição no frontend) — habilita `view_dashboard` server-side + teste único de
  isolamento; (2) atalho de próxima ação navega para a **rota do módulo + seção em foco** (sem
  reescrever rotas internas); (3) audit log **apenas** de tentativas não autorizadas (leituras da
  home não são logadas). Nova peça de RBAC: permissão `view_dashboard` (todos os papéis exceto
  Colaborador convidado; elevação por tenant deferida — não há override de permissão por org).
- Reuso: `gap_metrics_service`, `soa`/consolidação, `context/overview`, `document_versions`
  (`review_overdue` + baselines p/ série P2), `form_assignments`, `tenant_scope`+RLS, RBAC,
  auditoria central. Novos arquivos: `routers/dashboard.py`, `services/dashboard_service.py`,
  `schemas/dashboard_schema.py` (+ registro em `main.py`). **Nota**: a home atual (composição no
  frontend) tinha 2 bugs latentes que o endpoint corrige — path `/gap-assessment/` (real é
  `/gap/assessment/`) e rótulos de status `under_review`/`approved` (backend usa `in_review`/`in_force`).

**Backlog do MVP (transversal) — Revisão de UX / Design System** — planejado. A UI atual está crua
(PrimeNG Material sem customização; topbar plana com 12+ links; sem tokens/identidade). Direção
**enterprise sóbrio**, **manter PrimeNG + tema customizado**, **claro + escuro**, escopo **design
system + telas-chave**. O design será feito no **Claude Design** (prompt pronto). Brief + inventário
de telas + nova navegação (sidebar agrupada por módulo) em `docs/feature-ux-revamp.md`.

**Backlog do MVP (transversais) — Dashboard de Conformidade + Motor de Rastreabilidade/Timeline** —
planejados (sequência: Dashboard → Rastreabilidade → Plano de Ação #4 → Evidências #5). São **camada
de leitura/agregação** sobre o que já existe (`gap_metrics_service`, summary da SoA, overview de
contexto, `document_versions`, `audit_logs`, baselines do Gap) — sem novo modelo de domínio, salvo
**uma peça nova**: endpoint de **leitura** de `audit_logs` (`GET /audit`, paginado, tenant-scoped,
nova permissão `view_audit`). O **Dashboard** é a home da org e a **tela-âncora da Revisão de UX**.
**Fora de escopo** do motor de timeline: upload de arquivos de evidência + tags (crítica/informativa/
pendente) — isso é o **Módulo 5**, que depois aparece na mesma timeline. Escopo + prompts
`/speckit.specify` prontos em `docs/feature-dashboard-rastreabilidade.md`.

**Feature 005 — Statement of Applicability (SoA)** (`005-soa-declaracao-aplicabilidade`) — implementada e validada (24 testes backend + 81 frontend; migration validada no PG; E2E browser cenários A–F)
- Plano: `specs/005-soa-declaracao-aplicabilidade/plan.md`
- Spec: `specs/005-soa-declaracao-aplicabilidade/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo (Módulo 3, cláusula 6.1.3 d): Declaração de Aplicabilidade dos 93 controles do Anexo A —
  aplicabilidade + justificativa de inclusão tipada/exclusão + riscos tratados + status de
  implementação, **consolidando a avaliação corrente do Gap Analysis** num **Documento Controlado**
  versionado e **exportável em PDF**. Insumo do Plano de Ação (Módulo 4).
- Decisões-chave (clarify): insumo = avaliação **corrente** do Gap (não baseline); mapeamento de
  status Gap→SoA (Atende→Implementado · Parcial→Em andamento · Não atende→Não iniciado · N/A→Não
  aplicável · Não avaliado→vazio); divergência derivada do **valor vivo** do Gap (sem snapshot),
  reconciliação explícita; aprovação do Admin com **assinatura avançada opcional** (reusa Motor 003).
- Reuso: `controlled_document_service`+`document_versions` (novo `DocType.soa`), `signature_service`
  (003), `tenant_scope`+RLS, RBAC (`view_soa`/`manage_soa`/`approve_soa`), auditoria, classificação
  (Módulo 1). Nova dependência: `reportlab` (PDF server-side, pure-Python). Ver plano.

**Feature 004 — Gap Analysis ISO/IEC 27001:2022** (`004-gap-analysis`) — implementada (38 testes backend + 69 frontend; commit `3939a15`)
- Plano: `specs/004-gap-analysis/plan.md`
- Spec: `specs/004-gap-analysis/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: avaliação de aderência em 2 dimensões (Cláusulas 4–10 + 93 controles do Anexo A) →
  indicadores/lacunas → **baseline versionada** (Documento Controlado) → condução atribuível/assinável
  (reusa Motor 003). Insumo do SoA (Módulo 3) e Plano de Ação (Módulo 4).
- Decisões-chave (clarify): aderência ponderada (Atende=100%/Parcial=50%/Não atende=0%, exclui N/A e
  Não preenchido); atribuição inteira por padrão + opção por tema do Anexo A; seed **opt-in
  versionado e aditivo**; baseline congelada por **aprovação do Admin** (assinatura opcional).
- Decisão arquitetural: catálogo-base (`gap_seed_item`) é **compartilhado pela plataforma** (sem
  `tenant_id`, somente leitura) + **cópia editável por org** (com `tenant_id`+RLS). Ver Complexity
  Tracking no plano.

**Feature 003 — Motor de Workflow de Preenchimento (atribuível e assinável)** (`003-workflow-preenchimento`) — implementada (37 testes backend + 40 testes frontend, todos passando)
- Plano: `specs/003-workflow-preenchimento/plan.md`
- Spec: `specs/003-workflow-preenchimento/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml` · Quickstart: `.../quickstart.md`
- Escopo: capacidade **transversal** — template parametrizável → atribuição (membro ou link
  tokenizado) → preenchimento (assumir/salvar/enviar) → **assinatura avançada** (Lei 14.063/2020) →
  versão imutável, com trilha append-only/wizard. Diagnóstico é o 1º consumidor; Gap Analysis (004) usa.
- Decisões-chave (clarify): snapshot do template na atribuição; política de assinatura configurável por
  org (única padrão / contra-assinatura opcional); identidade do externo via vínculo + **OTP por
  e-mail** (fail-closed); campos obrigatórios validados no envio. Reusa convite/token, Documento
  Controlado/versões, auditoria, e-mail, RBAC e RLS.

**Feature 002 — Diagnóstico e Contexto da Organização** (`002-diagnostico-contexto`) — implementada (ver seção do módulo acima); pendente E2E manual + PostgreSQL real
- Plano: `specs/002-diagnostico-contexto/plan.md`
- Spec: `specs/002-diagnostico-contexto/spec.md` · Research: `.../research.md` ·
  Data model: `.../data-model.md` · Contracts: `.../contracts/openapi.yaml`
- Escopo: Cláusula 4 do SGSI — Análise de Contexto (4.1, PESTEL/SWOT + impacto), Mapa de Partes
  Interessadas (4.2, Poder×Interesse/Mendelow) e Declaração de Escopo (4.3), como **documentos
  controlados versionados** (1 em vigor + rascunho paralelo).
- Decisões-chave: dados de trabalho relacionais + snapshot de versão imutável (append-only);
  1 conjunto por organização; aprovação só pelo Admin da organização (`approve_context_document`);
  classificação como rótulo + política de acesso por classificação configurável (RBAC-default);
  sugestões heurísticas (sem IA); reusa `tenant_scope`/RBAC/auditoria da fundação.

**Feature 001 — Fundação Multi-Tenant** (`001-fundacao-multi-tenant`) — implementada (ver seção do módulo acima)
- shared-DB + `tenant_id` com escopo central (`helpers/tenant_scope.py`) + RLS; JWT HS512 + `jti`
  em Redis (fail-open) + `password_changed_at`; Argon2id; contexto de org via `X-Org-Context`;
  cross-tenant ⇒ 404 genérico.
<!-- SPECKIT END -->

