# Phase 1 — Data Model: Motor de Workflow de Preenchimento

Todas as entidades carregam `tenant_id` (FK → `organizations.id`), com **RLS** (policy
`tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid`) e índice por `tenant_id`.
Tabelas append-only (`form_assignment_events`, `form_signatures`) recebem **gatilho** que bloqueia
UPDATE/DELETE (SQLite + PostgreSQL), análogo a `audit_logs`/`document_versions`.

## Enums (em `settings.py`)

- `FormKind`: `diagnostic` | `gap_analysis` | `generic`
- `FormFieldType`: `text` | `textarea` | `boolean` | `number` | `select`
- `AssignmentStatus`: `draft` | `pending` | `in_progress` | `submitted` | `returned` | `signed` |
  `completed` | `cancelled`
- `AssignmentEventType`: `assigned` | `notified` | `claimed` | `saved` | `submitted` | `returned` |
  `signed` | `countersigned` | `completed` | `cancelled` | `reminded` | `otp_requested`
- `SignerRole`: `filler` | `assigner`
- `TemplateStatus`: `draft` | `active` | `archived`
- `DocType` (estender o existente): + `form_response`

## 1. FormTemplate (`form_templates`)

Template parametrizável de campos, por organização.

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK organizations, index, RLS |
| kind | FormKind | a qual fase serve |
| title | str(200) | |
| schema | JSON | `[{ "secao", "campos": [{ "chave","rotulo","tipo","obrigatorio","opcoes?" }] }]` |
| status | TemplateStatus | default `draft` |
| created_by | UUID | autor |
| created_at / updated_at | datetime(tz) | |

**Regras**: `schema` validado (cada campo: chave única no template, tipo ∈ FormFieldType; `opcoes`
obrigatório se `tipo=select`). Editar o template **não** afeta atribuições existentes (R2 — snapshot).

## 2. FormAssignment (`form_assignments`)

Instância do workflow — uma atribuição de um template a um preenchedor.

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK organizations, index, RLS |
| template_id | UUID | FK form_templates (origem) |
| kind | FormKind | denormalizado |
| title | str(200) | |
| fields_snapshot | JSON | **cópia congelada** do `schema` no momento da atribuição (R2) |
| instructions | Text | nullable |
| status | AssignmentStatus | default `pending` (ou `draft` se criada sem atribuir) |
| respondent_user_id | UUID? | FK users — preenchedor **membro** |
| respondent_email | str(320)? | preenchedor **externo** |
| respondent_name | str(200)? | nome informado (externo) |
| respondent_token_hash | str(64)? | **hash** do token (externo); unique; nunca o token em claro |
| token_expires_at | datetime(tz)? | expiração do link |
| deadline_at | datetime(tz)? | prazo (sinalizador; FR-019) |
| answers | JSON | respostas atuais (`{ chave: valor }`) — possível PII |
| content_hash | str(64)? | selo SHA-256 no momento da assinatura |
| current_version_id | UUID? | FK document_versions (snapshot assinado) |
| assigned_by / assigned_at | UUID / datetime(tz) | quem atribuiu |
| claimed_at / submitted_at / signed_at / completed_at | datetime(tz)? | marcas de tempo |
| created_at / updated_at | datetime(tz) | |

**Constraints**: exatamente **um** de (`respondent_user_id`, `respondent_token_hash`) preenchido
(CHECK). `respondent_token_hash` unique. Acesso: tenant_scope **+** ownership (designado **ou** token).

### Máquina de estados (transições válidas)

```
draft ──(atribuir)──▶ pendente ──(assumir)──▶ em_preenchimento ──(enviar*)──▶ preenchido
                                   ▲                                              │
              (devolver, com motivo)└──────────────────────────────────────────┘ │
preenchido ──(assinar†)──▶ assinado ──(política: única → concluir | dupla → contra-assinar)──▶ concluído
qualquer não-final ──(cancelar)──▶ cancelado
```

- `*enviar` exige todos os campos **obrigatórios** do snapshot preenchidos (R7).
- `†assinar` exige status `preenchido`; para externo, exige **OTP verificado** (R5).
- `assinado → concluído`: automático se política = única; se exige contra-assinatura do atribuidor,
  passa por `assinado` (1 assinatura) e só vai a `concluído` após a 2ª (R6).
- Transição inválida ⇒ 409 (sem mutação).

## 3. FormAssignmentEvent (`form_assignment_events`) — append-only

Trilha por atribuição → alimenta o wizard/linha do tempo.

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK organizations, index, RLS |
| assignment_id | UUID | FK form_assignments, index |
| event | AssignmentEventType | |
| actor_user_id | UUID? | autor (membro) |
| actor_label | str(200)? | rótulo do externo (sem PII de conteúdo) |
| at | datetime(tz) | carimbo de tempo |
| note | str(500)? | ex.: motivo de devolução — **nunca** conteúdo de resposta |

**Gatilho append-only**: bloqueia UPDATE/DELETE.

## 4. FormSignature (`form_signatures`) — append-only

Assinatura avançada (1 ou 2 por atribuição, conforme política).

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK organizations, index, RLS |
| assignment_id | UUID | FK form_assignments, index |
| signer_user_id | UUID? | membro (sessão) |
| signer_role | SignerRole | `filler` ou `assigner` |
| signer_name / signer_email | str | identidade do signatário |
| signed_at | datetime(tz) | carimbo de tempo UTC |
| content_hash | str(64) | SHA-256 do conteúdo canônico assinado |
| algorithm | str(20) | `sha256` |
| level | str(20) | `advanced` |
| otp_verified | bool | externo: OTP confirmado |
| ip / user_agent | str? | metadados de origem |

**Gatilho append-only**: bloqueia UPDATE/DELETE. Verificação de integridade = recomputar SHA-256 do
conteúdo da versão imutável e comparar com `content_hash`.

## 5. FormSignaturePolicy (`form_signature_policies`) — 1 por organização

| Campo | Tipo | Notas |
|---|---|---|
| id | UUID | PK |
| tenant_id | UUID | FK organizations, **unique** (1 por org), RLS |
| require_assigner_countersignature | bool | default `false` (R6) |

## OTP de assinatura externa (transiente)

`form_signature_otp` (assignment_id, code_hash str(64), expires_at, attempts int) — **só hash** do
OTP, TTL curto, limite de tentativas. Verificado no `sign` externo; descartado após uso. Não é
auditado com o valor (apenas o evento `otp_requested`/`signed`).

## Reuso / versão imutável

- A assinatura cria um `document_version` (`DocType.form_response`, snapshot das `answers` + metadados
  do signatário + `content_hash`), reusando `controlled_document_service` e o gatilho append-only de
  `document_versions`. `FormAssignment.current_version_id` aponta para ele.

## Relacionamento com o Diagnóstico (002)

- `diagnostic_intake.py`: ao concluir um assignment `kind=diagnostic`, materializa `answers` em
  `diagnostics.sections` (formato `campos[]`), tornando-o a fonte do diagnóstico vigente. O
  `suggestion_service` continua lendo `diagnostics.sections` (sem alteração).

## Auditoria (sem PII)

Geram audit log (entity_type ∈ form_template/form_assignment/form_signature): criar/editar template,
atribuir, notificar, assumir, salvar, enviar, devolver, cancelar, assinar, contra-assinar, concluir,
e tentativa cross-tenant. **Nunca** gravar token, OTP ou conteúdo das respostas.
