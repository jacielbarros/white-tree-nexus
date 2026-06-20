---
description: "Task list for feature 003 — Motor de Workflow de Preenchimento (atribuível e assinável)"
---

# Tasks: Motor de Workflow de Preenchimento (atribuível e assinável)

**Input**: Design documents from `/specs/003-workflow-preenchimento/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/openapi.yaml](contracts/openapi.yaml),
[quickstart.md](quickstart.md). **Roda sobre as features 001 (fundação) e 002 (contexto)** —
reusa auth, `tenant_scope`+RLS, RBAC, auditoria, e-mail, mecânica de token de convite e o padrão
de Documento Controlado/versões imutáveis.

**Tests**: ⚠️ **OVERRIDE da constitution:** testes NÃO são opcionais — toda story inclui **teste de
isolamento de tenant** + casos de falha principais (Princípio VI).

**Organization**: por user story (US1–US5). Backend `wtnapp/`, frontend `wtnadmin/src/app/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizável (arquivos diferentes, sem dependências pendentes)
- **[Story]**: US1–US5. Setup/Foundational/Polish sem label.

---

## Phase 1: Setup

- [X] T001 Estender `wtnapp/helpers/permissions.py`: adicionar `assign_form`, `fill_form`, `sign_form`
  e `view_form` à matriz papel→permissão (org_admin/consultant: assign+view+sign; demais papéis de
  acesso ao contexto: view; `fill_form`/`sign_form` também verificados por *ownership* no router).
- [X] T002 [P] Adicionar enums em `wtnapp/settings.py`: `FormKind`, `FormFieldType`,
  `AssignmentStatus`, `AssignmentEventType`, `SignerRole`, `TemplateStatus`, e estender `DocType`
  com `form_response`.
- [X] T003 [P] Estender `wtnapp/test/conftest.py` com fixtures do módulo (seed de org + usuários
  `org_admin`/`consultant`/`client` e helper de header `X-Org-Context`, reusando os da 002 se possível).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: núcleo do motor (template, atribuição, eventos, máquina de estados) de que US1–US5 dependem.
**⚠️ Nenhuma user story começa antes desta fase.**

- [X] T004 [P] Models `FormTemplate` e `FormAssignment` em `wtnapp/models/form_template_model.py` e
  `wtnapp/models/form_assignment_model.py` (+migration+RLS): `FormAssignment` com `fields_snapshot`
  (JSON), respondente membro **ou** `respondent_token_hash`+`respondent_email` (CHECK exatamente-um),
  `status`, `answers`, prazos e marcas de tempo, `current_version_id`.
- [X] T005 [P] Model `FormAssignmentEvent` em `wtnapp/models/form_assignment_event_model.py`
  (+migration+RLS+**gatilho append-only** bloqueando UPDATE/DELETE, análogo a `audit_logs`).
- [X] T006 [P] Schemas em `wtnapp/schemas/form_template_schema.py` e
  `wtnapp/schemas/form_assignment_schema.py` (response com `id: UUID`; validação do `schema`/snapshot).
- [X] T007 `form_workflow_service` em `wtnapp/services/form_workflow_service.py`: **máquina de estados**
  (transições válidas; transição inválida ⇒ 409), congelamento do **snapshot** do template na
  atribuição, validação de **campos obrigatórios** no envio, e gravação de `FormAssignmentEvent` +
  `AuditService.log_from_request` em cada transição.
- [X] T008 [P] Estender `wtnapp/services/notification_service.py` com `send_form_assignment_email` e
  `send_form_reminder_email` (reusa `utils/email.py`, best-effort).
- [X] T009 `wtnapp/main.py`: pontos de registro dos novos routers (`form_templates`, `form_assignments`,
  `form_respond`, `form_signature_policy`).

**Checkpoint**: motor (template + atribuição + eventos + máquina de estados) pronto — user stories podem começar.

---

## Phase 3: User Story 1 — Atribuir e preencher (membro) (Priority: P1) 🎯 MVP

**Goal**: consultor monta template, atribui a um membro; o membro assume, preenche (salva/retoma) e envia.

**Independent Test**: criar template → atribuir a membro (status `pendente` + e-mail) → assumir
(`em_preenchimento`) → salvar parcial + retomar sem perda → enviar (`preenchido`); sem obrigatório ⇒
422; A não acessa dados de B.

### Tests (MANDATORY) ⚠️

- [X] T010 [P] [US1] **Teste de isolamento de tenant**: template/atribuição/evento de A inacessíveis a
  B (404 + audit) em `wtnapp/test/test_tenant_isolation_forms.py`.
- [X] T011 [P] [US1] Testes do ciclo membro (criar template, atribuir, assumir muda status e registra
  quem/quando, salvar parcial + retomar sem perda, enviar; **enviar sem obrigatório ⇒ 422**) em
  `wtnapp/test/test_form_assignment_lifecycle.py`.

### Implementation

- [X] T012 [US1] Router `wtnapp/routers/form_templates.py` (CRUD de template; `assign_form` p/ escrita,
  `view_form` p/ leitura) + audit; registrar em `main.py`.
- [X] T013 [US1] Router `wtnapp/routers/form_assignments.py` (`POST` criar/atribuir → congela snapshot
  + dispara e-mail; `GET` lista/detalhe; `POST .../claim`; `PUT .../answers`; `POST .../submit`) com
  `tenant_scope` + `require_permission` + **ownership** + audit; registrar em `main.py`.
- [X] T014 [P] [US1] Frontend `pages/form-templates/form-templates.ts` (CRUD de template + auto-chave),
  `pages/form-assignments/form-assignments.ts` (criar/atribuir + lista + wizard + assinar + devolver/cancelar),
  `pages/form-fill/form-fill.ts` (assumir/preencher/salvar/enviar) — Signals, OnPush, FormsModule.

**Checkpoint**: US1 funcional e isolamento verificado — MVP do motor.

---

## Phase 4: User Story 2 — Preenchedor externo via link tokenizado (Priority: P2)

**Goal**: respondente sem conta preenche e envia por link com token (só hash persistido), vendo só a sua atribuição.

**Independent Test**: atribuir a e-mail externo gera link; resolver por token vê só a atribuição;
preencher/enviar; token expirado/inválido ⇒ 404/410; isolamento.

### Tests (MANDATORY) ⚠️

- [X] T015 [P] [US2] Testes do token (atribuir externo gera link só-hash; resolver por token expõe só a
  atribuição; preencher/enviar; expirado/inválido ⇒ 404/410; nenhum outro dado acessível) em
  `wtnapp/test/test_form_respond_token.py`.

### Implementation

- [X] T016 [US2] Geração/validação de token no `form_workflow_service` (reusa o hashing de
  `invitations` — só hash em `respondent_token_hash`, com `token_expires_at`).
- [X] T017 [US2] Router `wtnapp/routers/form_respond.py` (`GET /forms/respond/{token}`,
  `PUT .../answers`, `POST .../submit`) — público, rate-limited (slowapi), escopado a 1 atribuição +
  audit; registrar em `main.py`.
- [X] T018 [P] [US2] Frontend `pages/form-respond/form-respond.ts` — rota pública `/respond/:token`,
  máquina de estados (loading→claim→fill→sign_otp→done), OTP e assinatura avançada; sem authGuard.

**Checkpoint**: US1–US2 independentes.

---

## Phase 5: User Story 3 — Assinatura eletrônica avançada (Priority: P3)

**Goal**: assinar (nível avançada) gera versão imutável + selo de integridade; externo confirma OTP;
política de assinatura configurável por org.

**Independent Test**: assinar `preenchido` ⇒ `assinado` + `FormSignature` + versão imutável + selo;
`verify` confere e detecta adulteração; UPDATE/DELETE da versão bloqueado; OTP errado/expirado ⇒ 401;
política dupla exige contra-assinatura.

### Tests (MANDATORY) ⚠️

- [X] T019 [P] [US3] Testes de assinatura (membro assina ⇒ `FormSignature` + versão imutável +
  `content_hash`; `verify` confere e adulteração é detectada; **append-only** bloqueia UPDATE/DELETE;
  política dupla ⇒ exige contra-assinatura do atribuidor p/ `concluído`) em
  `wtnapp/test/test_form_signature.py`.
- [X] T020 [P] [US3] Teste OTP do externo (`request-otp` + `sign` com OTP correto assina; OTP
  errado/expirado ⇒ 401) em `wtnapp/test/test_form_respond_token.py` (estende).

### Implementation

- [X] T021 [US3] Models `FormSignature` + `FormSignaturePolicy` + tabela transiente de OTP
  (`form_signature_otp`, só hash + TTL) em `wtnapp/models/form_signature_model.py` e
  `form_signature_policy_model.py` (+migration+RLS+**gatilho append-only** em `form_signatures`).
- [X] T022 [US3] `signature_service` em `wtnapp/services/signature_service.py`: canonicalização das
  respostas + **SHA-256**; cria `FormSignature` + `document_version` (`DocType.form_response` via
  `controlled_document_service`); OTP (gerar/enviar via `notification_service`/verificar) p/ externo
  (fail-closed); aplica a política (única/dupla) e transiciona `assinado`/`concluído`.
- [X] T023 [US3] Endpoints de assinatura: `POST /form-assignments/{id}/sign` (membro),
  `POST /forms/respond/{token}/otp` + `.../sign` (externo), `GET /form-assignments/{id}/verify`,
  e `GET`/`PUT /form-signature-policy` — nos routers correspondentes + audit.
- [X] T024 [P] [US3] Assinatura do membro em `form-assignments` (`sign()`); OTP+assinatura externa em
  `form-respond` (`requestOtp()`/`signWithOtp()`); política via `ApiService.getSignaturePolicy/updateSignaturePolicy`.

**Checkpoint**: US1–US3 independentes; formulários viram documentos assinados/imutáveis.

---

## Phase 6: User Story 4 — Trilha, wizard, devolução e cancelamento (Priority: P4)

**Goal**: linha do tempo append-only por atribuição; atribuidor devolve (volta a `em_preenchimento`) ou cancela.

**Independent Test**: trilha completa e ordenada (sem conteúdo das respostas); devolver com motivo
(notifica) e reenviar; cancelar.

### Tests (MANDATORY) ⚠️

- [X] T025 [P] [US4] Testes (trilha completa/ordenada sem conteúdo; **devolver** `preenchido`→
  `em_preenchimento` com motivo + notificação; **cancelar**) em
  `wtnapp/test/test_form_assignment_lifecycle.py` (estende).

### Implementation

- [X] T026 [US4] Endpoints `POST .../return`, `POST .../cancel`, `POST .../remind`,
  `GET .../events` (trilha) e `GET .../signatures` no `form_assignments.py` + audit de cada transição.
- [X] T027 [P] [US4] Wizard/linha do tempo em `form-assignments` (section `.timeline`, eventos append-only);
  ações devolver (com motivo), cancelar e lembrar integradas na mesma tela.

**Checkpoint**: US1–US4 independentes; rastreabilidade completa.

---

## Phase 7: User Story 5 — Diagnóstico como primeiro consumidor (Priority: P5)

**Goal**: preenchimento `kind=diagnostic` assinado/concluído vira a fonte do diagnóstico vigente e
mantém as sugestões.

**Independent Test**: concluir assignment `kind=diagnostic` materializa `diagnostics.sections`; as
sugestões aparecem e só persistem sob aceite.

### Tests (MANDATORY) ⚠️

- [X] T028 [P] [US5] Teste (concluir `kind=diagnostic` materializa `diagnostics.sections`; isolamento)
  em `wtnapp/test/test_diagnostic_intake.py`.

### Implementation

- [X] T029 [US5] `diagnostic_intake` em `wtnapp/services/diagnostic_intake.py`: ao concluir
  `kind=diagnostic`, mapear `answers` → `diagnostics.sections`, tornando-o a fonte vigente.
- [X] T030 [P] [US5] Banner em `diagnostic.ts` com link para `/app/form-templates` (kind=diagnostic)
  e nota que o preenchimento assinado atualiza o diagnóstico automaticamente.

**Checkpoint**: motor completo (US1–US5) com o diagnóstico como 1º consumidor.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T031 [P] **Tenant isolation sweep**: `test_tenant_isolation_forms.py` cobre template, assignment
  e token. RLS habilitada via migration `d6e7f8a9b005`.
- [X] T032 [P] **Audit review**: `AuditService.log_from_request` em todas as transições; token, OTP e
  respostas nunca aparecem nos detalhes do log.
- [X] T033 [P] Migration `wtnapp/alembic/versions/d6e7f8a9b005_workflow_module.py` criada com
  upgrade/downgrade, triggers append-only e RLS para todas as novas tabelas.
- [X] T034 Validar `quickstart.md` end-to-end: paths corrigidos para os endpoints reais
  (cenários A–F revisados e alinhados com a implementação).
- [X] T035 [P] Atualizar docs: seção do módulo em `CLAUDE.md` (implementado) + nota em `docs/README.md`.
- [X] T036 [P] Testes unitários: `form-templates.spec.ts` (6 testes), `form-assignments.spec.ts`
  (8 testes), `form-respond.spec.ts` (7 testes) — 30 testes frontend, todos passando.
- [X] T037 [P] Rate limiting nos endpoints de token/OTP: `RATE_LIMIT_FORM_TOKEN` (20/min, padrão)
  e `RATE_LIMIT_FORM_OTP` (5/min) em `settings.py`; decoradores em todos os endpoints de
  `form_respond.py`; desabilitável via `RATE_LIMIT_ENABLED=false` nos testes.

---

## Dependências entre fases

- **Setup (P1)** → **Foundational (P2)** → user stories.
- **US1 (P1)** é o MVP; **US2–US5** dependem do motor (P2) e podem ser implementadas em ordem de
  prioridade. US3 (assinatura) depende de US1 (atribuição/preenchimento). US5 depende de US3 (assinado)
  e do módulo 002.
- **Polish (P8)** por último.

## Exemplos de paralelização

- Foundational: T004, T005, T006 em paralelo (arquivos diferentes); T007 depende de T004/T005.
- US1: T010 e T011 (testes) em paralelo; T014 (frontend) em paralelo com T012/T013 após contratos.
- US3: T019 e T020 (testes) em paralelo; T024 (frontend) em paralelo com T021–T023.

## Estratégia de implementação

1. **MVP = US1** (atribuir + preencher membro) sobre o motor da P2 — já entrega valor (delegar preenchimento).
2. Incrementos: US2 (externo/token) → US3 (assinatura+OTP+política) → US4 (trilha/devolução) →
   US5 (consumo do diagnóstico).
3. Test-first em cada story (isolamento de tenant obrigatório); migrations + RLS + gatilhos append-only
   acompanham cada modelo novo.
