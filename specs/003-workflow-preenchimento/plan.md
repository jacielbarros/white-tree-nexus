# Implementation Plan: Motor de Workflow de Preenchimento (atribuível e assinável)

**Branch**: `003-workflow-preenchimento` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-workflow-preenchimento/spec.md`

## Summary

Capacidade **transversal** sobre a fundação multi-tenant (001) e o módulo de contexto (002): um
**motor genérico** que envolve qualquer formulário de fase num workflow **atribuir → preencher →
assinar → congelar**. Abordagem técnica: um **template parametrizável** por organização cujo
**snapshot** de campos é congelado em cada **atribuição** (clarify Q1); uma **máquina de estados**
(`rascunho → pendente → em_preenchimento → preenchido → assinado → concluído`, + `devolvido`/
`cancelado`) implementada num **service** que, a cada transição, grava um **evento append-only** e
auditoria; respondente **membro** (sessão autenticada) **ou externo** por **link tokenizado**
(reusa a mecânica de `invitations` — só o hash do token é persistido); **assinatura eletrônica
avançada** (Lei 14.063/2020) que canonicaliza as respostas → **SHA-256** → grava `FormSignature` +
congela uma **versão imutável** via `controlled_document_service`/`document_versions`; o externo
confirma um **OTP por e-mail** no ato (clarify Q3, fail-closed); a **política de assinatura** é
configurável por organização (única por padrão; contra-assinatura do atribuidor opcional — clarify
Q2); campos podem ser **obrigatórios** e o envio valida a completude (clarify Q4). O **Diagnóstico**
(002) é o **1º consumidor**: um adaptador materializa o preenchimento assinado no `diagnostics.sections`
existente, preservando o motor de sugestões. Reutiliza `tenant_scope`/RLS, `permissions`,
`audit_service`, `notification_service`/`utils.email` e o padrão **Documento Controlado SGSI**.

## Technical Context

**Language/Version**: Python 3.13 (backend) / TypeScript 5.9 + Angular 21 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy (síncrono), Pydantic v2, Alembic, python-jose,
slowapi, Redis · PrimeNG 21, Angular Signals (tudo já presente das features 001/002)

**Storage**: PostgreSQL (Alembic + `create_all()` no startup); RLS + gatilhos append-only nas novas tabelas

**Testing**: pytest + FastAPI TestClient (SQLite in-memory, override central de `get_db`) ·
Vitest + Angular TestBed. **Teste de isolamento de tenant obrigatório.**

**Target Platform**: Web (API REST + SPA Angular)

**Project Type**: Web application (monorepo `wtnapp/` + `wtnadmin/`) — estende as features 001/002

**Tenant Isolation Strategy**: Inalterada — shared-DB + `tenant_id` com escopo central não-contornável
(`tenant_scope`) + RLS nas novas tabelas. **Nuance**: o acesso de **preenchedor/portador de token**
é por *ownership* da atribuição (designado ou token válido), além do RBAC; o link tokenizado dá acesso
**somente** à sua atribuição. Cross-tenant ⇒ 404/403 + audit (fail-closed).

**Performance Goals**: criar/atribuir e salvar parcial p95 < 500 ms; emissão de assinatura + snapshot
p95 < 1 s; verificação de integridade p95 < 300 ms.

**Constraints**: sem `AsyncSession`; sem middleware novo (reusa CORS/rate-limit/tenant-scope);
e-mail é **best-effort** (fail-soft), mas o **OTP de assinatura externa** é **fail-closed** (gate de
segurança); rate limiting nos endpoints de token/OTP (reusa `slowapi`).

**Scale/Scope**: por organização — dezenas de templates, centenas de atribuições ao longo do tempo;
~3 routers backend (templates, assignments, respond-by-token) + adaptador do diagnóstico; ~3–4 telas
Angular (templates/autoria, atribuições + wizard, preenchimento, rota pública de resposta).

## Constitution Check

*GATE: Passou antes da Phase 0. Re-checado após a Phase 1 — ver "Post-Design".*

**Segurança (Core Principles I–V):**

- [x] **Isolamento de tenant**: novas tabelas (`form_templates`, `form_assignments`,
  `form_assignment_events`, `form_signatures`, `form_signature_policies`) têm `tenant_id`; queries via
  `tenant_scope`; RLS habilitada; acesso por token é escopado a 1 atribuição; cross-tenant ⇒ 404/403 +
  audit. (Princípio I — fail-closed.)
- [x] **RBAC**: novas permissões `assign_form`/`fill_form`/`sign_form`/`view_form` via
  `require_permission`; preencher/assinar exigem também *ownership* (designado ou token). (Princípio II)
- [x] **Auditoria**: atribuir/notificar/assumir/salvar/enviar/devolver/cancelar/assinar/concluir e
  tentativa cross-tenant chamam `AuditService.log_from_request()`; sem PII/segredos (token, OTP e
  respostas nunca em audit). (Princípio III)
- [x] **Integridade e versionamento**: assinatura congela **versão imutável** (snapshot + selo
  SHA-256) via `document_versions` (append-only); eventos e assinaturas também append-only (gatilho).
  (Princípio IV — central nesta feature.)
- [x] **Dados sensíveis**: respostas (possível PII) vivem na atribuição/snapshot, **nunca** em
  audit/logs/erros; **token e OTP só em hash**; cifragem de campos sensíveis em repouso quando
  aplicável. (Princípio V)

**Arquitetura (Regras que não dobram):**

- [x] Backend: sem repository layer; SQLAlchemy síncrono; `get_db()` central; novos routers em
  `main.py`; config via `settings.py`; sem middleware novo.
- [x] Frontend: standalone; `input()`/`output()`; `inject()`; control flow nativo; `OnPush`; Signals;
  Reactive Forms (`NonNullableFormBuilder`).
- [x] Schema: modelos SQLAlchemy **+** migration Alembic; novas tabelas com `tenant_id`.

**Qualidade (Definition of Done):**

- [x] **Test-first**: happy path, falhas principais (token expirado, OTP inválido, transição inválida,
  campo obrigatório ausente) **e teste de isolamento de tenant** planejados antes da implementação.
- [x] Mensagens de erro não vazam stack/tabela nem existência de recurso de outro tenant.

**Resultado do gate**: ✅ PASS — sem violações. Complexity Tracking vazio.

## Project Structure

### Documentation (this feature)

```text
specs/003-workflow-preenchimento/
├── plan.md · research.md · data-model.md · quickstart.md · contracts/ · checklists/
└── tasks.md   # /speckit.tasks (não criado aqui)
```

### Source Code (adições às features 001/002)

```text
wtnapp/
├── models/         # form_template_model, form_assignment_model, form_assignment_event_model,
│                   #   form_signature_model, form_signature_policy_model  (todos com tenant_id)
├── schemas/        # form_template_schema, form_assignment_schema, form_signature_schema
├── routers/        # form_templates.py, form_assignments.py, form_respond.py (token público)
│                   #   → registrados em main.py
├── services/       # form_workflow_service.py (máquina de estados + eventos),
│                   #   signature_service.py (canonicalização + SHA-256 + OTP + versão imutável),
│                   #   diagnostic_intake.py (adaptador: assignment assinado → diagnostics.sections)
├── helpers/        # permissions.py (estende a matriz com assign/fill/sign/view_form)
├── utils/ | services/  # notification_service: e-mails de atribuição/lembrete/OTP (reusa utils.email)
└── test/           # test_form_template, test_form_assignment_lifecycle, test_form_respond_token,
                    #   test_form_signature, test_diagnostic_intake, test_tenant_isolation (estende)

wtnadmin/src/app/pages/
├── form-templates/    # autoria do template (reusa o form-builder do diagnóstico, modo configuração)
├── form-assignments/  # consultor: criar/atribuir, lista, wizard/linha do tempo
├── form-fill/         # preenchedor membro: assumir, preencher (salvar/retomar), enviar, assinar
└── form-respond/      # rota pública tokenizada (preenchimento + OTP de assinatura do externo)
```

**Structure Decision**: estende o monorepo (`wtnapp/` + `wtnadmin/`), reusando auth, `tenant_scope`,
RBAC, auditoria, e-mail, mecânica de token de convite e o padrão de Documento Controlado/versões.

## Complexity Tracking

> Sem violações do Constitution Check. Tabela intencionalmente vazia.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |

## Phase 0 — Research

Concluída em [research.md](research.md): motor genérico com `kind`; snapshot do template na atribuição;
máquina de estados em service com eventos append-only; respondente externo por token (padrão
`invitations`, só hash); assinatura avançada (canonicalização + SHA-256 + versão imutável) com OTP por
e-mail para externo; política de assinatura configurável por org; obrigatoriedade de campos no envio;
diagnóstico como 1º consumidor via adaptador; reuso de e-mail/auditoria/RLS.

## Phase 1 — Design & Contracts

Concluída: [data-model.md](data-model.md) (entidades, máquina de estados, RLS, gatilhos append-only),
[contracts/openapi.yaml](contracts/openapi.yaml) + [contracts/README.md](contracts/README.md),
[quickstart.md](quickstart.md). `CLAUDE.md` atualizado (marcadores SPECKIT) para apontar este plano.

### Post-Design Constitution Re-Check

✅ PASS. Eventos/assinaturas/versões append-only; escopo central + RLS; acesso de token escopado a 1
atribuição; OTP/token só em hash; auditoria sem PII. Sem novas violações; Complexity Tracking vazio.

## Phase 2 — Próximo passo

`/speckit.tasks` para gerar `tasks.md`. **Não** gerado por este comando.
