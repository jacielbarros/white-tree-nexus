# Quickstart: Preview Interativo e Posicionamento Visual de Assinatura em PDF

## Prerequisites

Feature 009 must already be migrated and functional.

Backend `.env` keeps the Feature 009 document storage settings:

```env
DOCUMENT_STORAGE_DIR=./document_store/
DOCUMENT_PREVIEW_TTL_MINUTES=60
DOCUMENT_MAX_PDF_BYTES=20971520
DOCUMENT_RENDER_TIMEOUT_SECONDS=30
FIELD_ENCRYPTION_KEY=<fernet-url-safe-32-byte-key>
```

Frontend adds a PDF viewer dependency during implementation:

```bash
cd wtnadmin
npm install pdfjs-dist
```

## Database

Run migrations twice to validate idempotency and reconciliation of existing tables:

```bash
alembic upgrade head
alembic upgrade head
```

Expected:

- Placement tables/columns exist.
- Append-only triggers protect placement history and signed placement snapshots.
- Existing Feature 009 tables are reconciled without duplicate objects.
- System remains at a single Alembic head.

Validation note (2026-06-23): `alembic heads` returned a single head
`e4f5a6b7c812`; `alembic upgrade head` applied the migration once and a second
`alembic upgrade head` completed with no pending changes.

## Backend Validation Flow

1. Generate a preview as in Feature 009.

2. Open inline PDF:

   ```bash
   curl -L http://localhost:8000/print-documents/previews/<preview_id>/inline-pdf \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>" \
     -o inline-preview.pdf
   ```

   Expected: HTTP 200, PDF bytes returned, audit event for inline view.

3. Fetch layout metadata:

   ```bash
   curl http://localhost:8000/print-documents/previews/<preview_id>/layout \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>"
   ```

   Expected: page metrics, default placement, blocked areas and latest placement if any.

4. Confirm a user placement:

   ```bash
   curl -X POST http://localhost:8000/print-documents/previews/<preview_id>/signature-placements \
     -H "Authorization: Bearer <token>" \
     -H "X-Org-Context: <tenant-a>" \
     -H "Content-Type: application/json" \
     -d '{
       "confirm_snapshot_hash": "<snapshot_hash>",
       "page_number": 1,
       "x_points": 360,
       "y_points": 36,
       "width_points": 180,
       "height_points": 54,
       "page_width_points": 595,
       "page_height_points": 842,
       "coordinate_system": "pdf_points_bottom_left",
       "origin": "user"
     }'
   ```

   Expected: HTTP 201 and a placement revision with hash.

5. Sign with confirmed placement:

   ```bash
   curl -X POST http://localhost:8000/print-documents/previews/<preview_id>/sign \
     -H "Authorization: Bearer <approver-token>" \
     -H "X-Org-Context: <tenant-a>" \
     -H "Content-Type: application/json" \
     -d '{
       "confirm_snapshot_hash": "<snapshot_hash>",
       "confirmed_placement_id": "<placement_id>"
     }'
   ```

   Expected: signed PDF includes visual seal in the confirmed position and metadata reports
   `signature_method=internal_electronic_signature`.

6. Sign with backend default placement:

   ```bash
   curl -X POST http://localhost:8000/print-documents/previews/<preview_id>/sign \
     -H "Authorization: Bearer <approver-token>" \
     -H "X-Org-Context: <tenant-a>" \
     -H "Content-Type: application/json" \
     -d '{
       "confirm_snapshot_hash": "<snapshot_hash>"
     }'
   ```

   Expected: backend validates the default placement, creates an auditable placement revision with
   origin `default` or `template`, signs the PDF and returns the frozen signed placement.

## Frontend Validation Flow

1. Open Contexto, Gap Analysis or SoA.
2. Click "Pre-visualizar".
3. Verify the PDF opens inline.
4. Navigate pages and zoom.
5. Drag or position the signature seal.
6. Confirm placement.
7. Sign the document.
8. Download the final PDF and verify the seal position.

## Negative Validation

- Try to confirm placement outside page bounds: expect 400 and no placement revision.
- Try to confirm placement over blocked area: expect 400 and clear message.
- Try to sign without confirmed placement when a valid default exists: expect signed document with a materialized default placement.
- Try to sign without confirmed placement when no valid default can be computed: expect 400.
- Try to sign with stale/expired preview: expect 409.
- Try cross-tenant layout, inline PDF, placement and sign: expect 404/403 + audit.
- Suspend organization and retry preview/layout/placement/sign/download: expect fail-closed.
- Manipulate page dimensions sent by frontend: backend rejects mismatch.

## Tests To Run

Backend:

```bash
pytest wtnapp/test/test_print_document_preview.py \
  wtnapp/test/test_print_document_signing.py \
  wtnapp/test/test_print_document_interactive_preview.py \
  wtnapp/test/test_print_document_signature_placement.py \
  wtnapp/test/test_print_document_signature_placement_failures.py \
  wtnapp/test/test_print_document_performance.py \
  wtnapp/test/test_tenant_isolation_print_documents.py
```

Frontend:

```bash
cd wtnadmin
npm test -- --watch=false
npm run build
```

## Acceptance Checklist

- Inline preview opens without requiring prior download.
- Preview download remains available and audited when permission/classification allow it.
- Zoom/scroll do not change persisted placement.
- Placement is persisted before signing.
- Signing without manual placement materializes and freezes a valid default placement.
- Signed document freezes the exact confirmed placement.
- Blocked areas are enforced by backend validation.
- Signature method is shown as internal electronic signature.
- PAdES/ICP-Brasil is not implied in MVP output.
- Cross-tenant access is blocked and audited.
