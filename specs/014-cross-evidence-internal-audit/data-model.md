# Phase 1 Data Model — Evidências Transversais + Auditoria Interna (5a)

Todas as tabelas abaixo são **dados da organização** e carregam `tenant_id` (FK `organizations.id`) +
RLS no PostgreSQL. Trilhas (`evidence_version`, `evidence_event`, `internal_audit_event`) são
**append-only** (triggers SQLite + PG, padrão da Feature 008).

## Enums (em `settings.py`)

### Reuso
- `Classification` (`publico`/`uso_interno`/`confidencial`/`restrito`) — default upload `uso_interno`.
- `DocStatus`, `AuditOutcome` — reuso.
- `DocType` — **adicionar** `internal_audit_report = "internal_audit_report"`.

### Novos
- `SgsiArtifactType` (taxonomia canônica de alvo): `soa_item`, `gap_item`, `risk`, `asset`,
  `audit_finding`. *(extensível — a 5b acrescenta `nonconformity`, `corrective_action`.)*
- `EvidenceStatus`: `active`, `inactive`.
- `EvidenceEventType`: `uploaded`, `content_viewed`, `downloaded`, `replaced`, `inactivated`,
  `linked`, `unlinked`, `access_denied`.
- `InternalAuditStatus`: `planned`, `in_progress`, `completed`, `cancelled`.
- `AuditChecklistResult`: `conforme`, `nao_conforme`, `nao_aplicavel`, `pendente` (default `pendente`).
- `AuditFindingType`: `conforme`, `nc_maior`, `nc_menor`, `oportunidade_melhoria`, `observacao`.
- `AuditFindingStatus`: `active`, `inactive`.
- Constante `AUDIT_CODE_PREFIX = "AUD-"` (código `AUD-####` por auditoria, por tenant).
- `PROMOTABLE_FINDING_TYPES = {nc_maior, nc_menor}` (deriva `promotable`).

---

## Fase 1 — Domínio `evidence_*`

### `evidence`
Registro lógico central da evidência (sem FK a artefato — vínculos em `evidence_link`).

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK `organizations.id` | obrigatório; indexado; RLS |
| `title` | String(255) | default = filename sanitizado |
| `description` | Text nullable | |
| `classification` | Enum `Classification` | corrente; default `uso_interno` |
| `status` | Enum `EvidenceStatus` | default `active` |
| `current_version_id` | UUID nullable | aponta para a versão corrente |
| `created_by` | UUID FK `users.id` | |
| `created_at`/`updated_at` | DateTime(tz) | |
| `inactivated_by`/`inactivated_at`/`inactivation_reason` | nullable | inativação lógica |

Índices: `tenant_id`, `status`, `current_version_id`, `created_at`.

### `evidence_version`
Versão imutável do arquivo (1:N de `evidence`). **Append-only.** Mesma forma do
`gap_evidence_version` (008): `version_number` (unique por `tenant_id`+`evidence_id`),
`original_filename`, `storage_key` (**nunca** exposto em API/audit), `content_hash` (SHA-256),
`hash_algorithm`, `encrypted`/`encryption_scheme` (`fernet`), `size_bytes`
(`0 < n ≤ EVIDENCE_MAX_FILE_BYTES`), `mime_type`, `extension`, `classification`, `uploaded_by`,
`uploaded_at`.

### `evidence_link` (polimórfico, 1..N)
Vínculo entre uma evidência e uma linha de artefato tenant-scoped.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | obrigatório; RLS |
| `evidence_id` | UUID FK `evidence.id` | obrigatório |
| `target_type` | Enum `SgsiArtifactType` | obrigatório |
| `target_id` | UUID | id da linha-alvo (validado por `scoped_query` no tenant) |
| `created_by` | UUID | |
| `created_at` | DateTime(tz) | |
| `active` | Boolean | default `true`; `false` = desvinculado (lógico) |

Índices/restrições: unique `(tenant_id, evidence_id, target_type, target_id)`; índice
`(tenant_id, target_type, target_id)` (lookup por artefato); índice `evidence_id`.

### `evidence_event` (custódia, append-only)
Mesma forma do `gap_evidence_event`, generalizada: `evidence_id` nullable, `version_id` nullable,
`link_id` nullable, `target_type`/`target_id` nullable (contexto), `event_type`
(Enum `EvidenceEventType`), `outcome` (`success`/`denied`), `actor_id`, `occurred_at`, `details` JSON
(**sanitizado**: sem conteúdo/path/token/PII/`storage_key`).

### Relacionamentos
- `evidence (1) → (N) evidence_version` · `evidence.current_version_id → evidence_version.id`
- `evidence (1) → (N) evidence_link` · `evidence (1) → (N) evidence_event`
- `evidence_link.target_(type,id)` → linha tenant-scoped (`soa_item`/`gap_catalog_item`/`risk`/`asset`/
  `internal_audit_finding`)

### Estados / transições (evidência)
```
active + version 1 ──replace──▶ active + version N (current_version_id → nova versão)
       └──inactivate──▶ inactive (oculta nas listas; histórico só p/ manage_evidence)
links:  linked/unlinked não alteram status da evidência
```
Regras: upload cria `evidence` + `evidence_version(1)` + ao menos 1 `evidence_link` + evento
`uploaded`+`linked`; replace cria versão N+1 (classificação obrigatória), atualiza
`current_version_id`/classificação corrente, evento `replaced`; inactivate marca `status=inactive` +
`inactivated_*` + evento `inactivated` (nunca apaga arquivo); link/unlink criam `evidence_link` /
marcam `active=false` + eventos `linked`/`unlinked`.

### Migração do 008 (ver research D2)
`gap_evidence`→`evidence`; `gap_evidence_version`→`evidence_version`; `gap_evidence_event`→
`evidence_event`; cria `evidence_link(target_type=gap_item, target_id=assessment_item_id, active=true)`
por evidência. Drop de `gap_evidence*`. `routers/gap_evidence.py` passa a delegar ao
`evidence_service` (mesmos paths/contratos).

---

## Fase 2 — Domínio `internal_audit_*`

### `internal_audit_program`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `name` | String(255) | obrigatório |
| `objective` | Text nullable | |
| `period_start`/`period_end` | Date nullable | ciclo |
| `created_by`/`created_at`/`updated_at` | | |

### `internal_audit`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `program_id` | UUID FK `internal_audit_program.id` | obrigatório |
| `code` | String(20) | `AUD-####` por tenant; imutável |
| `title` | String(255) | obrigatório |
| `scope` | Text | escopo |
| `criteria` | Text | critérios (ex.: ISO 27001, políticas internas) |
| `auditor_member_id` | UUID FK `users.id` | auditor interno (membro da org) |
| `period_start`/`period_end` | Date nullable | |
| `status` | Enum `InternalAuditStatus` | default `planned` |
| `current_report_version_id` | UUID nullable | ponteiro p/ versão em vigor do relatório |
| `draft_status` | Enum `DocStatus` | `draft`/`in_review` (ciclo do relatório) |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `program_id`, `status`; unique `(tenant_id, code)`.

### `internal_audit_checklist_item`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `audit_id` | UUID FK `internal_audit.id` | obrigatório |
| `target_type` | Enum `SgsiArtifactType` nullable | `soa_item`/`gap_item`/`risk` |
| `target_id` | UUID nullable | linha tenant-scoped |
| `criterion` | Text | pergunta/critério |
| `result` | Enum `AuditChecklistResult` | default `pendente` |
| `note` | Text nullable | sem PII |
| `order_index` | Integer | ordenação |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `audit_id`, `(target_type, target_id)`.

### `internal_audit_finding`
| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `tenant_id` | UUID FK | RLS |
| `audit_id` | UUID FK `internal_audit.id` | obrigatório |
| `checklist_item_id` | UUID FK `internal_audit_checklist_item.id` nullable | **opcional** (clarify Q2) |
| `finding_type` | Enum `AuditFindingType` | obrigatório |
| `title` | String(255) | |
| `description` | Text | achado (sem PII bruta) |
| `target_type` | Enum `SgsiArtifactType` nullable | `soa_item`/`gap_item`/`risk` |
| `target_id` | UUID nullable | linha tenant-scoped |
| `promotable` | Boolean | derivado: `finding_type ∈ {nc_maior, nc_menor}` |
| `nonconformity_ref` | UUID nullable | **reservado p/ 5b** (vazio nesta feature) |
| `status` | Enum `AuditFindingStatus` | `active` default; `inactive` = remoção lógica |
| `created_by`/`created_at`/`updated_at` | | |

Índices: `tenant_id`, `audit_id`, `finding_type`, `(target_type, target_id)`, `promotable`.
Evidências da constatação: via `evidence_link(target_type=audit_finding, target_id=finding.id)`.

### `internal_audit_event` (trilha append-only)
`tenant_id`, `audit_id` nullable, `entity_type` (`program`/`audit`/`checklist_item`/`finding`/`report`),
`entity_id` nullable, `event_type` (ex.: `created`/`updated`/`status_changed`/`finding_added`/
`report_submitted`/`report_approved`/`report_signed`/`report_exported`/`inactivated`), `outcome`,
`actor_id`, `occurred_at`, `details` JSON (sanitizado).

### Relatório (Documento Controlado — reuso)
`InternalAudit.current_report_version_id` + `draft_status` espelham SoA/risk plan; versões em
`document_versions` com `document_type = internal_audit_report`, `content_snapshot` = escopo +
critérios + itens + constatações (tipos/vínculos/evidências referenciadas). Assinatura opcional via
`signature_service`. PDF via `internal_audit_export_service` a partir do snapshot.

### Estados / transições (auditoria)
```
planned ──start──▶ in_progress ──complete──▶ completed
   └──────────────cancel──────────────▶ cancelled  (de planned/in_progress)
```
Transições inválidas ⇒ 409 com mensagem clara. **Gate duro** do relatório: `submit-review`/`approve`
exigem `status=completed` **e** zero itens de checklist com `result=pendente`; `approve` exige
`draft_status=in_review` (reusa `controlled_document_service.approve_document`). *(Sem campo
`mandatory` na checklist — a completude usa o enum `AuditChecklistResult` existente.)*

---

## Permissões (helpers/permissions.py)

| Permissão | super_admin | org_admin | consultant | internal_auditor | manager/process/control_owner | client | guest |
|-----------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `view_evidence` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – |
| `manage_evidence` | ✔ | ✔ | ✔ | ✔ | – | – | – |
| `view_internal_audit` | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ | – |
| `manage_internal_audit` | ✔ | ✔ | ✔ | ✔ | – | – | – |
| `approve_audit_report` | ✔ | ✔ | – | – | – | – | – |

Acesso ao **conteúdo** de evidência: `publico`/`uso_interno` ⇒ `view_evidence`;
`confidencial`/`restrito` ⇒ `manage_evidence` (via `classification_access`, igual ao padrão 008).

**RBAC da timeline** (`GET /traceability/timeline`): exige a permissão de **visualização do módulo do
artefato-alvo** (`soa_item`→`view_soa`; `gap_item`→`view_gap`; `risk`→`view_risk`; `asset`→`view_asset`)
**e** `view_evidence`. Entradas de constatação só são incluídas se o usuário também tiver
`view_internal_audit`; caso contrário a timeline as **omite** (sem revelar contagem). Tudo via
`scoped_query`; alvo inexistente/cross-tenant ⇒ 404 genérico + audit.

## DTOs principais (schemas)
- **Evidence**: `EvidenceSummary` (sem `storage_key`; inclui `links[]`, `can_download`),
  `EvidenceHistory` (versões+eventos, só `manage_evidence`), `EvidenceUploadRequest`
  (multipart: `file`, `classification` obrigatório default `uso_interno`, `title?`, `description?`,
  `target_type`+`target_id` para o vínculo inicial), `EvidenceReplaceRequest`, `EvidenceLinkRequest`
  (`target_type`+`target_id`), `EvidenceRepositoryFilter` (texto/target_type/classification/autor/
  data/estado).
- **Internal Audit**: `ProgramRequest/Summary`, `AuditRequest/Summary` (inclui `status`, `readiness`),
  `ChecklistItemRequest/Summary`, `ChecklistImportRequest` (`source=soa|gap`, filtros), `FindingRequest/
  Summary` (inclui `promotable`, `nonconformity_ref`), `AuditReportVersionSummary`, `TimelineEntry`,
  `AuditDashboard` (contagens).

## Validações-chave
- Alvo do vínculo/checklist/constatação deve existir em `scoped_query(...)` do tenant; senão 404 + audit.
- `file` 1..`EVIDENCE_MAX_FILE_BYTES`; extensão/MIME na política; `FIELD_ENCRYPTION_KEY` presente
  (fail-closed).
- `classification` obrigatória no upload e na substituição.
- Histórico/versões/inativas exigem `manage_evidence`.
- `code` da auditoria gerado por sequência por tenant; imutável.
- `promotable` derivado de `finding_type` (não editável diretamente); `nonconformity_ref` não setável
  nesta feature.
- Aprovar relatório: gate de completude (auditoria `completed` + zero itens de checklist com
  `result=pendente`).
