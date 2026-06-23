# Quickstart: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

## Prerequisites

Backend `.env` additions for local validation:

```env
DOCUMENT_STORAGE_DIR=./document_store/
DOCUMENT_PREVIEW_TTL_MINUTES=60
DOCUMENT_MAX_PDF_BYTES=20971520
DOCUMENT_RENDER_TIMEOUT_SECONDS=30
FIELD_ENCRYPTION_KEY=<fernet-url-safe-32-byte-key>
```

`FIELD_ENCRYPTION_KEY` must be configured for PDF storage. If it is empty, preview/sign/download must
fail closed with a clear message and without creating partial signed documents.

## Database

```bash
alembic upgrade head
```

Expected:

- New print document tables exist.
- Append-only triggers exist for template versions, signed documents, snapshots, signatures and events.
- System templates for `context_report`, `gap_report` and `soa_report` are seeded idempotently.
- Running `alembic upgrade head` again does not duplicate templates or fail.

## Backend Validation Flow

1. Start backend:

   ```bash
   uvicorn wtnapp.main:app --reload
   ```

2. Generate a Contexto consolidated preview:

   ```bash
   curl -X POST http://localhost:8000/print-documents/previews \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>" \
     -H "Content-Type: application/json" \
     -d '{"document_type":"context_report","classification":"uso_interno"}'
   ```

3. Download preliminary PDF:

   ```bash
   curl -L http://localhost:8000/print-documents/previews/<preview_id>/pdf \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>" \
     -o context-preview.pdf
   ```

   Verify the PDF contains a clear "Nao assinado / Preview" mark and no signature seal.

4. Sign the preview with a user who has `approve_context_document`:

   ```bash
   curl -X POST http://localhost:8000/print-documents/previews/<preview_id>/sign \
     -H "Authorization: Bearer <approver-token>" \
     -H "X-Org-Context: <tenant-a>" \
     -H "Content-Type: application/json" \
     -d '{"confirm_snapshot_hash":"<hash-from-preview-response>"}'
   ```

5. Download final signed PDF:

   ```bash
   curl -L http://localhost:8000/print-documents/signed/<document_id>/pdf \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>" \
     -o context-signed.pdf
   ```

   Verify the PDF contains status signed, identifier, signer, signed timestamp and hash.

6. Verify integrity:

   ```bash
   curl -X POST http://localhost:8000/print-documents/signed/<document_id>/verify \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>"
   ```

   Expected: `valid=true`.

## Stale Preview Validation

1. Generate a Gap Analysis preview.
2. Update one Gap item or activate a new template version.
3. Try to sign the old preview.
4. Expected: HTTP 409, clear message requiring a new preview, audit event recorded.

## Data Sufficiency and Missing Variable Validation

1. Try to generate `context_report` before diagnostic, context analysis, stakeholders or scope records
   exist.
2. Expected: HTTP 422 with `missing_sections` identifying the missing source areas and no PDF file
   created.
3. Configure a tenant template with a required variable that is not available in the source artifact.
4. Expected: HTTP 422 with `missing_variables` identifying the required variables.
5. Configure an optional variable without a value.
6. Expected: preview succeeds, the PDF renders "Nao informado", and preview metadata includes a
   warning.

## Tenant Isolation Validation

1. Generate and sign a document in tenant A.
2. Using a user only from tenant B, attempt:
   - `GET /print-documents/previews/<tenant-a-preview>`
   - `GET /print-documents/signed/<tenant-a-document>`
   - `GET /print-documents/signed/<tenant-a-document>/pdf`
   - `POST /print-documents/signed/<tenant-a-document>/verify`
3. Expected: 404/403 without revealing existence, denied audit event recorded, no PDF bytes returned.
4. Using a Super Admin, attempt the same operations without `X-Org-Context`; expected: denied with no
   tenant data returned.
5. Using a Super Admin with explicit `X-Org-Context: <tenant-a>`, repeat allowed operations; expected:
   access is scoped to tenant A and audit records the explicit context.

## Classification Validation

1. Configure or simulate a classification policy where the active user cannot read `confidencial` or
   `restrito` documents.
2. Generate a preview or signed document with a restricted classification.
3. Attempt preliminary PDF download, final PDF download and history access as the restricted user.
4. Expected: access is denied without exposing the document, and the audit log records only sanitized
   metadata.

## Suspended Organization Validation

1. Suspend an organization or simulate `OrgStatus.suspended`.
2. Attempt preview, sign, history, verify, preliminary PDF download and final PDF download.
3. Expected: all operations fail closed with a clear suspended-organization message, no PDF bytes are
   returned, and audit logs contain no document content.

## Timing and Timeout Validation

1. Generate preview for Contexto, Gap and SoA with normal sample data.
2. Expected: each preview completes in <= 30 seconds under local test conditions.
3. Sign and download a final PDF.
4. Expected: signature + download completes in <= 2 minutes under local test conditions.
5. Force renderer timeout using a very low `DOCUMENT_RENDER_TIMEOUT_SECONDS`.
6. Expected: clear timeout response, no signed document and no partial PDF.

## Template Validation

1. As Org Admin, create a tenant template for `gap_report`.
2. Add a version with allowed variables and controlled sections.
3. Activate the version.
4. Generate a new Gap preview and verify it uses the tenant template version.
5. Sign a document.
6. Activate a newer template version.
7. Download the old signed PDF and verify it still references the original template version.

## Tests To Run

Backend:

```bash
pytest wtnapp/test/test_print_document_preview.py \
  wtnapp/test/test_print_document_signing.py \
  wtnapp/test/test_print_document_templates.py \
  wtnapp/test/test_tenant_isolation_print_documents.py \
  wtnapp/test/test_print_document_history.py \
  wtnapp/test/test_print_document_integrity.py \
  wtnapp/test/test_print_document_preview_failures.py \
  wtnapp/test/test_print_document_signing_failures.py \
  wtnapp/test/test_print_document_performance.py
```

Frontend:

```bash
cd wtnadmin
npm test -- --watch=false
npm run build
```

## Acceptance Checklist

- Preview available for Contexto consolidated report, Gap Analysis and SoA.
- Preliminary PDF is visibly "Nao assinado / Preview".
- Stale preview cannot be signed.
- Signed PDF remains immutable after artifact/template changes.
- History lists multiple signed versions.
- Integrity verification recomputes PDF hash and snapshot hash.
- Cross-tenant access is blocked and audited.
- Audit logs contain only non-sensitive metadata.
