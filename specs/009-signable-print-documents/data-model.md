# Data Model: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

## Enums

### PrintableDocumentType

- `context_report`
- `gap_report`
- `soa_report`
- `gap_baseline` (preparado para evolucao)
- `form_response` (preparado para evolucao)

### PrintTemplateScope

- `system`: template padrao da plataforma, sem dados de tenant, somente leitura para organizacoes.
- `tenant`: template customizado de uma organizacao, sempre com `tenant_id`.

### PrintTemplateStatus

- `draft`
- `active`
- `inactive`

### DocumentPreviewStatus

- `active`
- `expired`
- `stale`
- `signed`

### SignedDocumentStatus

- `signed`
- `obsolete`

### DocumentAccessEventType

- `preview_created`
- `preview_downloaded`
- `signed`
- `signed_downloaded`
- `verified`
- `template_created`
- `template_version_created`
- `template_activated`
- `template_deactivated`
- `access_denied`

## Entity: PrintTemplate

Template logico disponivel para um tipo documental.

**Fields**

- `id` UUID PK
- `tenant_id` UUID nullable FK `organizations.id`; obrigatorio quando `scope=tenant`
- `scope` `system|tenant`
- `document_type` PrintableDocumentType
- `name` string(160)
- `description` string(500) nullable
- `status` PrintTemplateStatus
- `default_classification` Classification
- `current_version_id` UUID nullable FK `print_template_versions.id`
- `created_by` UUID nullable FK `users.id`
- `created_at` datetime
- `updated_at` datetime

**Relationships**

- Has many `PrintTemplateVersion`
- `current_version_id` points to the version currently used for new previews

**Validation**

- `scope=system` requires `tenant_id IS NULL`.
- `scope=tenant` requires `tenant_id IS NOT NULL`.
- For tenant templates, unique `(tenant_id, document_type, name)`.
- For system templates, unique `(document_type, name)` where `tenant_id IS NULL`.
- System templates are editable only by platform seed/Super Admin flow; org users cannot mutate them.

## Entity: PrintTemplateVersion

Imutavel. Guarda a definicao renderizavel do template.

**Fields**

- `id` UUID PK
- `tenant_id` UUID nullable FK `organizations.id`; copied from template for tenant scope
- `template_id` UUID FK `print_templates.id`
- `version_number` integer
- `renderer` string(40), default `reportlab_v1`
- `layout_schema` JSON, controlled sections/tables/text blocks/styles
- `allowed_variables` JSON array/object
- `required_sections` JSON array
- `content_hash` string(64), SHA-256 canonical of layout/variables
- `created_by` UUID nullable FK `users.id`
- `created_at` datetime

**Relationships**

- Belongs to `PrintTemplate`
- Referenced by `DocumentPreview` and `SignedDocument`

**Validation**

- Unique `(template_id, version_number)`.
- Update/delete blocked by append-only trigger after creation.
- Activation updates only the parent `PrintTemplate.current_version_id`; it never mutates the
  `PrintTemplateVersion` row. The activation itself is recorded as an audit/event entry.
- Prior signed documents keep their original `template_version_id` reference.

## Entity: DocumentPreview

Snapshot temporario visualizado pelo usuario antes da assinatura.

**Fields**

- `id` UUID PK
- `tenant_id` UUID FK `organizations.id`
- `document_type` PrintableDocumentType
- `source_artifact_type` string(40)
- `source_artifact_id` UUID nullable
- `source_document_version_id` UUID nullable FK `document_versions.id`
- `template_version_id` UUID FK `print_template_versions.id`
- `classification` Classification
- `status` DocumentPreviewStatus
- `artifact_fingerprint` string(64)
- `template_hash` string(64)
- `snapshot_hash` string(64)
- `preview_pdf_hash` string(64)
- `preview_storage_key` string(500)
- `expires_at` datetime
- `created_by` UUID FK `users.id`
- `created_at` datetime

**Relationships**

- Belongs to tenant
- Belongs to template version
- May be signed into one `SignedDocument`

**Validation**

- Preview expires after `DOCUMENT_PREVIEW_TTL_MINUTES` (default 60).
- Preview generation validates minimum source data by document type and fails with sanitized
  `missing_fields`/`missing_sections` when required data is absent.
- Required template variables without values fail generation; optional missing variables render
  "Nao informado" and are listed as warnings in preview metadata.
- Signing requires `status=active`, `expires_at >= now`, artifact fingerprint unchanged and template hash
  unchanged.
- `preview_storage_key` is never returned to frontend or audit log.
- Preliminary PDF must include visible "Nao assinado / Preview" mark and must not include signature seal.

## Entity: SignedDocument

Documento PDF final assinado e imutavel.

**Fields**

- `id` UUID PK
- `tenant_id` UUID FK `organizations.id`
- `document_type` PrintableDocumentType
- `source_artifact_type` string(40)
- `source_artifact_id` UUID nullable
- `source_document_version_id` UUID nullable FK `document_versions.id`
- `preview_id` UUID FK `document_previews.id`
- `template_version_id` UUID FK `print_template_versions.id`
- `version_number` integer
- `status` SignedDocumentStatus
- `classification` Classification
- `identifier` string(80), unique within tenant
- `pdf_hash` string(64)
- `snapshot_hash` string(64)
- `hash_algorithm` string(20), default `sha256`
- `pdf_storage_key` string(500)
- `size_bytes` integer
- `signed_by` UUID FK `users.id`
- `signed_at` datetime
- `created_at` datetime

**Relationships**

- Has one `SignedDocumentSnapshot`
- Has one or more `DocumentSignature`
- Belongs to template version and source artifact context

**Validation**

- Unique `(tenant_id, document_type, source_artifact_type, source_artifact_id, version_number)`.
- `pdf_storage_key` is never returned to frontend or audit log.
- Update/delete blocked by append-only trigger except status obsolescence if implemented as derived state.
- New signature for the same source generates next `version_number`; prior versions remain accessible and
  are shown as obsolete by derivation from newer version.

## Entity: SignedDocumentSnapshot

Conteudo canonico congelado usado na geracao do PDF final.

**Fields**

- `id` UUID PK
- `tenant_id` UUID FK `organizations.id`
- `signed_document_id` UUID FK `signed_documents.id`
- `artifact_fingerprint` string(64)
- `template_hash` string(64)
- `snapshot_hash` string(64)
- `rendered_variables` JSON
- `snapshot_json` JSON
- `created_at` datetime

**Validation**

- One snapshot per signed document.
- Update/delete blocked by append-only trigger.
- Snapshot may contain confidential data; never log or include in audit details.

## Entity: DocumentSignature

Assinatura eletronica interna da plataforma para documentos PDF controlados.

**Fields**

- `id` UUID PK
- `tenant_id` UUID FK `organizations.id`
- `signed_document_id` UUID FK `signed_documents.id`
- `signer_user_id` UUID FK `users.id`
- `signer_role` string(60)
- `signer_name` string(200)
- `signer_email` string(320) nullable
- `signed_at` datetime
- `content_hash` string(64), hash do snapshot assinado
- `pdf_hash` string(64), hash do PDF final
- `algorithm` string(20), default `sha256`
- `level` string(20), default `advanced`
- `auth_context` JSON, non-sensitive metadata only
- `ip` string(45) nullable
- `user_agent` string(500) nullable

**Validation**

- Update/delete blocked by append-only trigger.
- No OTP/token/session secret stored.
- `auth_context` may include auth method and request id, but not JWT, OTP, password or sensitive content.

## Entity: DocumentAccessEvent

Timeline append-only local para eventos relevantes, complementar ao `AuditService`.

**Fields**

- `id` UUID PK
- `tenant_id` UUID FK `organizations.id`
- `event_type` DocumentAccessEventType
- `entity_type` string(60)
- `entity_id` UUID nullable
- `actor_user_id` UUID nullable FK `users.id`
- `actor_role` string(60) nullable
- `outcome` `success|denied`
- `details` JSON nullable, sanitized
- `created_at` datetime

**Validation**

- Update/delete blocked by append-only trigger.
- Details never include PDF content, snapshot body, storage key, path, tokens or PII.

## Source Artifact Fingerprints

Each document type has a deterministic snapshot builder and fingerprint:

- `context_report`: diagnostic sections + context analysis + stakeholders + scope + current relevant
  version refs.
- `gap_report`: current gap assessment items + dashboard summary + guidance/expected evidences needed
  for the report.
- `soa_report`: SoA header + items + divergences + current relevant gap assessment reference.

The fingerprint is SHA-256 over canonical JSON (`sort_keys=True`, UTF-8, stable value formatting).

## State Transitions

### Preview

```text
active -> signed   (sign succeeds)
active -> stale    (artifact/template fingerprint changed)
active -> expired  (expires_at passed)
```

### Signed Document

```text
signed -> obsolete (derived when a newer signed version exists for same source)
```

Documents are not physically deleted in the MVP.

## Tenant Isolation Rules

- All tenant-scoped entities include `tenant_id`.
- All reads/writes use `scoped_query` or explicit tenant context helper.
- System templates are the only nullable-tenant records and contain no organization data.
- Storage paths are derived from opaque keys and tenant context; storage key/path never leaves backend.
- Cross-tenant access returns generic 404/403 and logs denied audit event.
