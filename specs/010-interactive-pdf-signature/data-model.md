# Data Model: Preview Interativo e Posicionamento Visual de Assinatura em PDF

## Entity: DocumentPreview

Existing Feature 009 entity. This feature extends it with layout metadata needed for visual review and
placement validation.

Inline viewer page/zoom/loading state remains client-side transient state and is not persisted as a
domain table. Opening the inline preview is represented by sanitized audit events; only stable layout
and placement metadata are persisted.

**New/extended fields**

- `pdf_page_metrics` JSON, required after preview generation
  - `page_number` integer, 1-based
  - `width_points` decimal
  - `height_points` decimal
  - `rotation` integer, default 0
- `signature_policy_hash` string(64), nullable
- `default_signature_placement` JSON, nullable

**Validation rules**

- Page metrics must match the generated preview PDF.
- Preview must be `active` and not expired to accept a new placement.
- If artifact fingerprint or template hash changes, placement cannot be used for signing.

## Entity: DocumentSignaturePlacement

Append-only record for a confirmed visual seal position on a preview.

**Fields**

- `id` UUID primary key
- `tenant_id` UUID FK Organization, required
- `preview_id` UUID FK DocumentPreview, required
- `document_type` string/enum, required
- `source_artifact_type` string, required
- `source_artifact_id` UUID nullable
- `placement_revision` integer, required
- `page_number` integer, 1-based, required
- `x_points` decimal, required
- `y_points` decimal, required
- `width_points` decimal, required
- `height_points` decimal, required
- `page_width_points` decimal, required
- `page_height_points` decimal, required
- `coordinate_system` string, default `pdf_points_bottom_left`
- `origin` enum: `default`, `user`, `template`
- `template_version_id` UUID FK PrintTemplateVersion, required
- `snapshot_hash` string(64), required
- `artifact_fingerprint` string(64), required
- `signature_policy_hash` string(64), nullable
- `placement_hash` string(64), required
- `created_by` UUID FK User, required
- `created_at` timestamptz, required

**Relationships**

- Belongs to Organization through `tenant_id`.
- Belongs to one DocumentPreview.
- May be referenced by one SignedDocumentSignaturePlacement after signing.

**Validation rules**

- `(tenant_id, preview_id, placement_revision)` unique.
- Coordinates must be finite and non-negative.
- `x + width <= page_width_points`.
- `y + height <= page_height_points`.
- `page_number` must exist in `DocumentPreview.pdf_page_metrics`.
- Page dimensions must match preview page metrics within a small tolerance.
- The seal rectangle must not intersect blocked/reserved areas from the active signature policy.
- Placement is append-only; changing a position creates a new revision.
- Active placement is the latest valid placement revision for the preview.

## Entity: SignedDocumentSignaturePlacement

Immutable snapshot of the exact placement used in a signed document.

**Fields**

- `id` UUID primary key
- `tenant_id` UUID FK Organization, required
- `signed_document_id` UUID FK SignedDocument, required
- `placement_id` UUID FK DocumentSignaturePlacement, required
- `page_number` integer, required
- `x_points` decimal, required
- `y_points` decimal, required
- `width_points` decimal, required
- `height_points` decimal, required
- `page_width_points` decimal, required
- `page_height_points` decimal, required
- `coordinate_system` string, required
- `origin` enum, required
- `placement_hash` string(64), required
- `created_at` timestamptz, required

**Validation rules**

- One placement snapshot per signed document.
- Append-only, no update/delete.
- Values are copied from the confirmed placement used at signature time.

## Entity: DocumentSignature

Existing Feature 009 entity. This feature extends it to distinguish current and future signature
methods.

**New/extended fields**

- `signature_method` enum
  - `internal_electronic_signature`
  - `pades`
  - `icp_brasil`
  - `external_certificate_provider`
- `signature_provider` string nullable
- `visual_signature_present` boolean, default true
- `provider_reference` string nullable, never used for secrets
- `provider_payload_hash` string(64) nullable

**Validation rules**

- MVP must use `internal_electronic_signature`.
- PDF labels must not describe internal signatures as PAdES/ICP-Brasil.
- Provider fields are metadata only in MVP; no external signing is performed.

## Entity: SignatureAppearancePolicy

Policy embedded in a template version layout schema or derived from system defaults. It defines how
the visual seal can be placed.

**Fields**

- `default_page` string or integer, e.g. `last`
- `default_anchor` string, e.g. `bottom_right`
- `default_margin_points` number
- `default_width_points` number
- `default_height_points` number
- `min_width_points` number
- `min_height_points` number
- `max_width_points` number
- `max_height_points` number
- `blocked_areas` array
  - `page` integer or `all`
  - `x_points`, `y_points`, `width_points`, `height_points`
  - `reason` string

**Validation rules**

- Blocked areas use the same canonical coordinate system.
- Default placement must be valid under the same rules as user placement.
- Policy changes affect only new previews; signed documents keep their frozen placement.

## State Transitions

### Preview and placement

```text
preview active
  -> placement revision confirmed
  -> placement revision confirmed again (new append-only revision)
  -> sign requested with confirmed placement
  -> signed document created + signed placement snapshot created
  -> preview signed
```

### Failure states

```text
preview active + placement invalid -> placement rejected, no signed document
preview expired/stale -> placement/sign blocked
organization suspended -> preview/view/placement/sign/download blocked
cross-tenant access -> 404/403 + audit
```
