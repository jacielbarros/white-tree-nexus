# Phase 1 Data Model — NC/Ações Corretivas + Análise Crítica + PDCA (5b)

Todas as tabelas são **dados da organização** e carregam `tenant_id` (FK `organizations.id`) + RLS no
PostgreSQL. Trilhas (`nonconformity_event`, `improvement_event`) são **append-only** (triggers
SQLite + PG, padrão das features anteriores).

## Enums (em `settings.py`)

### Reuso / extensão
- `SgsiArtifactType` — **estender**: `nonconformity`, `corrective_action` (a 5a já anunciou a extensão).
- `DocType` — **adicionar**: `management_review`.
- `DocStatus`, `AuditOutcome`, `Classification` — reuso.

### Novos
- `NCOrigin`: `audit_finding`, `external_audit`, `incident`, `management_review`, `other`.
- `NCSeverity`: `maior`, `menor`, `observacao`.
- `NCStatus`: `open`, `in_progress`, `in_verification`, `closed` (+ `cancelled`).
- `CorrectiveActionStatus`: `planned`, `in_progress`, `done`, `cancelled`.
- `VerificationResult`: `effective`, `ineffective`.
- `ImprovementOrigin`: `audit`, `nonconformity`, `management_review`, `suggestion`.
- `ImprovementStatus`: `proposed`, `in_progress`, `implemented`, `rejected`.
- `NC_CODE_PREFIX = "NC-"`, `IMPROVEMENT_CODE_PREFIX = "IMP-"`.

---

## Fase 1 — Domínio `nonconformity_*`

### `nonconformity`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK `organizations.id` | RLS |
| `code` | String(20) | `NC-####` por tenant; imutável |
| `origin` | Enum `NCOrigin` | obrigatório |
| `source_finding_id` | UUID FK `internal_audit_finding.id` nullable | preenchido na promoção |
| `title` | String(255) | |
| `description` | Text | sem PII bruta |
| `severity` | Enum `NCSeverity` | Maior/Menor/Observação |
| `target_type` | Enum `SgsiArtifactType` nullable | `soa_item`/`gap_item`/`risk`/`asset` (vínculo primário) |
| `target_id` | UUID nullable | linha tenant-scoped |
| `root_cause` | Text nullable | análise de causa raiz |
| `root_cause_method` | String(120) nullable | ex.: 5 Porquês / Ishikawa |
| `status` | Enum `NCStatus` | default `open` |
| `opened_by`/`opened_at` | | |
| `closed_by`/`closed_at` | nullable | preenchidos no encerramento |
| `created_at`/`updated_at` | | |

Índices: `tenant_id`, `status`, `severity`, `source_finding_id`, `(target_type,target_id)`; unique
`(tenant_id, code)`.

### `corrective_action`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `nonconformity_id` | UUID FK `nonconformity.id` | obrigatório |
| `description` | Text | |
| `responsible_member_id` | UUID FK `users.id` | membro ativo do tenant |
| `due_date` | Date nullable | prazo |
| `status` | Enum `CorrectiveActionStatus` | default `planned` |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `nonconformity_id`, `status`. **Prazo vencido** = `due_date < hoje` e
`status ∉ {done, cancelled}` (derivado).

### `nonconformity_verification`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `nonconformity_id` | UUID FK `nonconformity.id` | obrigatório |
| `result` | Enum `VerificationResult` | eficaz/ineficaz |
| `notes` | Text nullable | |
| `verified_by` | UUID FK `users.id` | |
| `verified_at` | DateTime(tz) | |

A **verificação mais recente** governa o gate; histórico preservado (append-only por convenção +
trilha em `nonconformity_event`).

### `nonconformity_event` (append-only)
`tenant_id`, `nonconformity_id` nullable, `entity_type` (`nonconformity`/`corrective_action`/
`verification`), `entity_id` nullable, `event_type` (`created`/`updated`/`status_changed`/`promoted`/
`action_added`/`verified`/`closed`/`inactivated`), `outcome`, `actor_id`, `occurred_at`, `details`
JSON (sanitizado). Trigger append-only.

### Estados / transições (NC)
```
open ──start──▶ in_progress ──send-verify──▶ in_verification ──close──▶ closed
  └───────────────── cancel ─────────────────▶ cancelled
```
**Gate de encerramento (FR-007)**: `close` exige `status=in_verification`, uma verificação mais recente
com `result=effective` e **zero ações corretivas em estado não terminal** (todas em `done`/`cancelled`).
Sem campo `mandatory`/`obrigatória` — a completude usa o `status` da ação. Transições inválidas ⇒ 409.

### Contrato de promoção (FR-002/003)
`promote(finding_id)`:
1. `finding = scoped_query(InternalAuditFinding)`; se `nonconformity_ref` já setado ⇒ retorna a NC
   existente (idempotente).
2. exige `finding.promotable=true` (senão 422).
3. cria NC: `origin=audit_finding`, `source_finding_id=finding.id`, severidade `nc_maior→maior`/
   `nc_menor→menor`, título/descrição/target copiados.
4. `finding.nonconformity_ref = nc.id` (**única escrita na 5a**); evento `promoted`.

---

## Fase 2 — Domínio `management_review_*`

### `management_review` (coleção; Documento Controlado)
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `title` | String(255) | |
| `review_date` | Date | data da reunião |
| `inputs` | JSON | entradas estruturadas por categoria (ações anteriores, mudanças, desempenho, auditoria, riscos, NCs) |
| `outputs` | JSON | saídas/decisões (melhorias, mudanças no SGSI, recursos) |
| `current_version_id` | UUID nullable | ponteiro p/ versão em vigor (contrato `controlled_document_service`) |
| `draft_status` | Enum `DocStatus` | `draft`/`in_review` |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `review_date`. Versões imutáveis em `document_versions` (`document_type=
management_review`, `content_snapshot` = inputs+outputs+meta; assinatura opcional). **Gate duro**:
aprovar exige entradas/saídas obrigatórias preenchidas + `draft_status=in_review`.

---

## Fase 3 — Domínio `improvement_*`

### `improvement`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `code` | String(20) | `IMP-####` por tenant; imutável |
| `title` | String(255) | |
| `description` | Text | |
| `origin` | Enum `ImprovementOrigin` | auditoria/NC/análise crítica/sugestão |
| `source_ref` | UUID nullable | id do finding/NC/review de origem |
| `status` | Enum `ImprovementStatus` | default `proposed` |
| `target_type` | Enum `SgsiArtifactType` nullable | artefato realimentado (read-only) |
| `target_id` | UUID nullable | linha tenant-scoped |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `status`, `origin`, `(target_type,target_id)`; unique `(tenant_id, code)`.

### `improvement_event` (append-only)
`tenant_id`, `improvement_id` nullable, `event_type`, `outcome`, `actor_id`, `occurred_at`, `details`.
Trigger append-only.

### Visão de ciclo PDCA (read-only)
`pdca_service` agrega, por artefato e cronologicamente: constatações (5a) → NCs → ações/verificação →
melhorias → artefato realimentado, reusando `traceability_service`. **Somente metadados**; **sem
write-back** nos módulos consumidos. **RBAC composto** (espelha a timeline da 5a): exige
`view_nonconformity`; entradas de constatação só com `view_internal_audit`, de análise crítica só com
`view_management_review` (senão omitidas, sem revelar contagem); sempre tenant-scoped (fail-closed).

---

## Permissões (helpers/permissions.py)

| Permissão | super_admin | org_admin | consultant | manager/control_owner/internal_auditor | client | guest |
|-----------|:--:|:--:|:--:|:--:|:--:|:--:|
| `view_nonconformity` | ✔ | ✔ | ✔ | ✔ | ✔ | – |
| `manage_nonconformity` | ✔ | ✔ | ✔ | – | – | – |
| `view_management_review` | ✔ | ✔ | ✔ | ✔ | ✔ | – |
| `manage_management_review` | ✔ | ✔ | ✔ | – | – | – |
| `approve_management_review` | ✔ | ✔ | – | – | – | – |

Evidências em NC/ação seguem o `classification_access` da 5a (conteúdo confidencial/restrito exige
permissão elevada).

## DTOs principais
- **NC**: `NonConformityRequest/Summary/Detail` (com `readiness`: can_close, overdue_actions,
  has_effective_verification), `PromoteRequest` (`finding_id`), `CorrectiveActionRequest/Summary`,
  `VerificationRequest/Summary`, `NCTransitionRequest`, `NCFilter` (status/severity/responsible/overdue).
- **Análise Crítica**: `ManagementReviewRequest/Summary/Detail`, `ReviewApproveRequest` (sign/
  classification), `ReviewVersionSummary`.
- **Melhoria**: `ImprovementRequest/Summary`, `PdcaCycleEntry`.
- **Dashboard**: `NcDashboard` (nc_by_status, nc_by_severity, overdue_actions, improvements_by_status).

## Validações-chave
- Alvo do vínculo (NC/melhoria) e `responsible_member_id` validados por `scoped_query` no tenant.
- Promoção: idempotente; só `promotable`; só constatação do próprio tenant.
- Encerrar NC: gate (verificação mais recente `effective` + zero ações em estado não terminal).
- Aprovar Ata: gate de completude + `draft_status=in_review`.
- Códigos `NC-####`/`IMP-####` por sequência do tenant; imutáveis.
- Remoção é **lógica**; trilhas append-only; sem PII bruta.
