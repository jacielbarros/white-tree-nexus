# Tasks: Preview Interativo e Posicionamento Visual de Assinatura em PDF

**Input**: Design documents from `/specs/010-interactive-pdf-signature/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Mandatory for this feature because it touches tenant-scoped documents, signed custody metadata, audit logs and PDF access. Backend tests must cover happy paths, tenant isolation, invalid/stale previews, invalid coordinates, blocked areas and immutable signed output. Frontend tests must cover inline PDF review, zoom/page navigation, coordinate conversion, placement confirmation and signing flow states.

**Organization**: Tasks are grouped by user story so each increment can be implemented and validated independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files or has no dependency on incomplete tasks.
- **[Story]**: User story label for traceability. Setup, Foundational and Polish tasks do not use story labels.
- Every task includes concrete repository paths.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare dependencies, shared constants and type surfaces used by the PDF viewer and signing flow.

- [X] T001 Add `pdfjs-dist` dependency to `wtnadmin/package.json` and `wtnadmin/package-lock.json`
- [X] T002 [P] Add signature method, placement origin and coordinate-system constants to `wtnapp/settings.py`
- [X] T003 [P] Add document preview layout, placement and signature method interfaces to `wtnadmin/src/app/core/models.ts`
- [X] T004 [P] Create the shared viewer shell files `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.ts` and `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.spec.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish the tenant-scoped data model, schemas, validation primitives and shared render/template behavior required by every user story.

**CRITICAL**: No user story starts before this phase is complete.

- [X] T005 Extend `DocumentPreview`, `DocumentSignature`, `DocumentSignaturePlacement` and `SignedDocumentSignaturePlacement` ORM support in `wtnapp/models/print_document_model.py`
- [X] T006 Create an idempotent Alembic migration for Feature 010, including tenant-scoped indexes and RLS policy reconciliation for new placement tables, in `wtnapp/alembic/versions/e4f5a6b7c812_interactive_pdf_signature.py`
- [X] T007 Extend preview layout, placement, sign and signed placement schemas in `wtnapp/schemas/print_document_schema.py`
- [X] T008 Implement shared placement hash, revision and snapshot helper functions in `wtnapp/services/document_signature_service.py`
- [X] T009 Implement PDF page metrics extraction and default placement construction in `wtnapp/services/print_render_service.py`
- [X] T010 Implement signature appearance policy resolution and blocked-area defaults in `wtnapp/services/print_template_service.py`
- [X] T011 [P] Add reusable preview/signature placement test helpers to `wtnapp/test/print_document_helpers.py`

**Checkpoint**: Database, schemas and shared services are ready for inline preview, placement and signing stories.

---

## Phase 3: User Story 1 - Visualizar PDF de preview inline (Priority: P1)

**Goal**: Authorized users can open a generated Contexto, Gap Analysis or SoA PDF preview directly in the application, navigate pages, zoom, and clearly see that it is a non-signed preview.

**Independent Test**: Generate a Feature 009 preview, open it inline through the shared viewer, navigate/zoom, and verify that expired/stale/classification-denied previews are blocked without leaking PDF content or storage details.

### Tests for User Story 1 (MANDATORY)

- [X] T012 [P] [US1] Add backend tests for inline PDF and layout happy path, expired preview, stale preview, suspended organization and classification denial in `wtnapp/test/test_print_document_interactive_preview.py`
- [X] T013 [P] [US1] Add tenant isolation tests for inline PDF and layout endpoints returning 404/403 plus audit in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [X] T014 [P] [US1] Add frontend viewer tests for PDF load, page navigation, zoom, preview status and load failure in `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.spec.ts`
- [X] T015 [P] [US1] Add frontend integration tests for opening inline preview from the existing document preview surface in `wtnadmin/src/app/shared/document-preview/document-preview.spec.ts`

### Implementation for User Story 1

- [X] T016 [US1] Implement `GET /print-documents/previews/{preview_id}/inline-pdf` with tenant scope, RBAC, organization-status fail-closed checks, classification checks and sanitized audit in `wtnapp/routers/print_documents.py`
- [X] T017 [US1] Implement `GET /print-documents/previews/{preview_id}/layout` with page metrics, default placement, blocked areas and stale/expired/suspended-organization checks in `wtnapp/routers/print_documents.py`
- [X] T018 [US1] Implement PDF.js loading, worker setup, page navigation, zoom and preview/non-signed status in `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.ts`
- [X] T019 [US1] Add inline PDF and layout API methods to `wtnadmin/src/app/core/api.service.ts`
- [X] T020 [US1] Integrate the shared inline viewer into `wtnadmin/src/app/shared/document-preview/document-preview.ts`
- [X] T021 [US1] Verify Contexto, Gap Analysis and SoA call the shared preview flow in `wtnadmin/src/app/pages/context-overview/context-overview.ts`, `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts` and `wtnadmin/src/app/pages/soa/soa.ts`

**Checkpoint**: US1 is independently usable: users can view a preview inline without downloading it.

---

## Phase 4: User Story 2 - Posicionar selo visual de assinatura (Priority: P1)

**Goal**: Authorized signers can visually place a seal on a valid PDF page, confirm that placement before signing, and rely on backend validation to reject invalid, stale or blocked positions.

**Independent Test**: Open an active preview, position the seal on a valid page, confirm it, reload layout/history and verify the placement revision is persisted; then try invalid coordinates, mismatched page dimensions, blocked areas and cross-tenant access.

### Tests for User Story 2 (MANDATORY)

- [X] T022 [US2] Add backend tests for placement create/list happy path, append-only revisions, invalid bounds, invalid page and page-dimension mismatch in `wtnapp/test/test_print_document_signature_placement.py`
- [X] T023 [P] [US2] Add backend tests for blocked area validation, default placement validation, suspended organization and stale/expired preview rejection in `wtnapp/test/test_print_document_signature_placement_failures.py`
- [X] T024 [P] [US2] Add tenant isolation tests for placement history and placement creation in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [X] T025 [P] [US2] Add frontend viewer tests for drag/resize, zoom/scroll coordinate conversion and blocked-area display in `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.spec.ts`
- [X] T026 [P] [US2] Add document preview tests for confirm-placement success and validation error states in `wtnadmin/src/app/shared/document-preview/document-preview-sign.spec.ts`

### Implementation for User Story 2

- [X] T027 [US2] Implement append-only placement revision creation and retrieval in `wtnapp/services/document_signature_service.py`
- [X] T028 [US2] Implement coordinate, page metric, blocked-area and stale-preview validators in `wtnapp/services/document_signature_service.py`
- [X] T029 [US2] Implement `GET/POST /print-documents/previews/{preview_id}/signature-placements` with tenant scope, RBAC, organization-status fail-closed checks and audit in `wtnapp/routers/print_documents.py`
- [X] T030 [US2] Add placement list/create API methods to `wtnadmin/src/app/core/api.service.ts`
- [X] T031 [US2] Extend the PDF viewer with draggable/resizable seal overlay, page selection and canonical PDF coordinate conversion in `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.ts`
- [X] T032 [US2] Render blocked areas, default placement and placement validation feedback in `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.ts`
- [X] T033 [US2] Integrate latest placement, confirm-placement action and clear user-facing errors in `wtnadmin/src/app/shared/document-preview/document-preview.ts`

**Checkpoint**: US2 is independently usable with US1: users can place and confirm a seal, and invalid placement attempts fail safely.

---

## Phase 5: User Story 3 - Assinar com metadados preparados para assinatura digital futura (Priority: P2)

**Goal**: Signed PDFs use the confirmed or default visual placement, freeze the placement into immutable custody metadata, and clearly identify the MVP signature as an internal electronic signature rather than PAdES/ICP-Brasil.

**Independent Test**: Sign a preview with a confirmed placement, download the final PDF, verify the seal position and history metadata, then change the source artifact/template/policy and confirm the signed document remains unchanged.

### Tests for User Story 3 (MANDATORY)

- [X] T034 [US3] Add backend tests for signing with confirmed placement, omitted `confirmed_placement_id` default-placement materialization, and suspended organization rejection in `wtnapp/test/test_print_document_signing.py`
- [X] T035 [P] [US3] Add backend tests for frozen signed placement immutability after artifact, template or policy changes in `wtnapp/test/test_print_document_integrity.py`
- [X] T036 [US3] Add backend tests for signature method/provider metadata and no PAdES/ICP-Brasil claim in generated PDF labels in `wtnapp/test/test_print_document_signing.py`
- [X] T037 [P] [US3] Add tenant isolation tests for preview download, signed placement lookup and signed document download in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [X] T038 [P] [US3] Add frontend history and signing tests for method, hash, placement, signer and signed labels in `wtnadmin/src/app/shared/document-history/document-history.spec.ts`

### Implementation for User Story 3

- [X] T039 [US3] Implement signing with optional `confirmed_placement_id`, backend materialization of a valid default placement when omitted, and signed placement snapshot creation in `wtnapp/services/document_signature_service.py`
- [X] T040 [US3] Render the visual signature seal at canonical PDF coordinates in final signed PDFs in `wtnapp/services/print_render_service.py`
- [X] T041 [US3] Update sign request/response handling for optional `confirmed_placement_id`, organization-status fail-closed checks and signed placement lookup endpoint in `wtnapp/routers/print_documents.py`
- [X] T042 [US3] Expose signed placement and signature method response models in `wtnapp/schemas/print_document_schema.py`
- [X] T043 [US3] Add signed placement and signature method client models/API calls in `wtnadmin/src/app/core/models.ts` and `wtnadmin/src/app/core/api.service.ts`
- [X] T044 [US3] Update signed document history display with signature method, placement, signer, hash and date/time in `wtnadmin/src/app/shared/document-history/document-history.ts`
- [X] T045 [US3] Update the signing action to send the confirmed placement when present, allow backend default placement when absent, and show final signed download state in `wtnadmin/src/app/shared/document-preview/document-preview.ts`
- [X] T046 [US3] Ensure generated PDF labels distinguish internal electronic signature from PAdES/ICP-Brasil in `wtnapp/services/print_render_service.py`
- [X] T047 [US3] Add sanitized audit events for preview download, sign, final download and verification including method and placement hashes in `wtnapp/routers/print_documents.py`

**Checkpoint**: US3 is independently verifiable after US1+US2: signed PDFs preserve placement and signature method metadata.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate security, idempotency, performance and documentation after the selected user stories are complete.

- [X] T048 [P] Reconcile the OpenAPI contract with implemented request/response shapes in `specs/010-interactive-pdf-signature/contracts/openapi.yaml`
- [X] T049 [P] Refresh validation steps and any implementation-specific notes in `specs/010-interactive-pdf-signature/quickstart.md`
- [X] T050 Run `alembic upgrade head` twice and record idempotency expectations in `specs/010-interactive-pdf-signature/quickstart.md`
- [X] T051 Run backend tests for print documents and tenant isolation in `wtnapp/test/test_print_document_interactive_preview.py`, `wtnapp/test/test_print_document_signature_placement.py`, `wtnapp/test/test_print_document_signing.py` and `wtnapp/test/test_tenant_isolation_print_documents.py`
- [X] T052 Run frontend unit tests and production build through `wtnadmin/package.json`
- [X] T053 Audit all new log/error paths for sensitive data leakage in `wtnapp/routers/print_documents.py`, `wtnapp/services/document_signature_service.py` and `wtnapp/services/audit_service.py`
- [X] T054 Sweep tenant scope and RBAC coverage for new queries/endpoints in `wtnapp/routers/print_documents.py`, `wtnapp/helpers/tenant_scope.py` and `wtnapp/helpers/permissions.py`
- [ ] T055 Validate inline preview performance, large-page behavior and the end-to-end review/place/confirm/start-sign flow time target in `wtnapp/test/test_print_document_performance.py` and `wtnadmin/src/app/shared/pdf-signature-viewer/pdf-signature-viewer.ts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 - Setup**: No dependencies.
- **Phase 2 - Foundational**: Depends on Phase 1 and blocks every user story.
- **Phase 3 - US1**: Depends on Phase 2. Delivers inline preview as the first independently testable increment.
- **Phase 4 - US2**: Depends on Phase 2 and practically builds on the US1 viewer. It completes the P1 MVP together with US1.
- **Phase 5 - US3**: Depends on Phase 2 and requires a valid placement path from US2 for the confirmed-placement flow; default placement fallback may be validated after foundational policy support.
- **Phase 6 - Polish**: Depends on the completed story scope selected for release.

### User Story Completion Order

1. **US1 - Inline preview**: First visible value; can be demoed independently.
2. **US2 - Visual placement**: Same P1 priority; completes the MVP for interactive signing.
3. **US3 - Signed output metadata**: Adds immutable signed placement, method clarity and PAdES/ICP-Brasil preparation.

### Within Each User Story

- Write tests first and confirm they fail before implementation.
- Backend models/migrations/schemas before services.
- Services before routers.
- API client/types before frontend integration.
- UI component behavior before page-level integration.

---

## Parallel Execution Examples

### US1

```text
Task A: T012 backend inline/layout tests
Task B: T014 frontend viewer tests
Task C: T019 API service methods
```

### US2

```text
Task A: T022 placement backend tests
Task B: T025 viewer coordinate conversion tests
Task C: T030 API placement methods
```

### US3

```text
Task A: T035 immutability backend tests
Task B: T038 frontend history tests
Task C: T043 frontend models/API for signed placement
```

---

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to make inline preview real.
3. Complete US2 to make visual placement real.
4. Stop and validate the P1 MVP: preview inline, place seal, confirm placement, reject invalid placement and preserve tenant isolation.

### Incremental Delivery

1. Ship US1 after isolated backend/frontend tests pass.
2. Ship US2 after placement confirmation, blocked areas and coordinate conversion pass.
3. Ship US3 after signed PDF output, frozen placement and method metadata pass.
4. Run Phase 6 before merge.

### Team Notes

- Migrations must be idempotent and reconcile already-existing tables/columns.
- The visual seal is not a PAdES/ICP-Brasil digital signature in this MVP.
- Frontend zoom, scroll and viewport state must never be persisted as canonical placement data.
- Audit logs must never include PDF content, storage keys, internal paths, tokens or PII.
