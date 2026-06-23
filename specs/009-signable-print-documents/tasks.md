# Tasks: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

**Input**: Design documents from `/specs/009-signable-print-documents/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Obrigatorios pela constitution. Cada user story inclui testes de happy path, falhas
principais e isolamento de tenant quando aplicavel.

**Organization**: Tasks agrupadas por user story para permitir implementacao e teste independentes.

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Add printable document enums and `DOCUMENT_STORAGE_DIR`, `DOCUMENT_PREVIEW_TTL_MINUTES`, `DOCUMENT_MAX_PDF_BYTES`, `DOCUMENT_RENDER_TIMEOUT_SECONDS` settings in `wtnapp/settings.py`
- [x] T002 [P] Add `manage_print_templates` permission to backend RBAC roles in `wtnapp/helpers/permissions.py`
- [x] T003 [P] Mirror `manage_print_templates` in the frontend permission matrix in `wtnadmin/src/app/core/permissions.ts`
- [x] T004 [P] Add TypeScript interfaces for printable documents, templates, previews and signatures in `wtnadmin/src/app/core/models.ts`
- [x] T005 [P] Add document storage environment notes to the required env section in `AGENTS.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Central models, migration, storage, renderer and router skeleton required before any
user story can be implemented.

**CRITICAL**: Nenhuma user story comeca antes desta fase terminar.

- [x] T006 Create `PrintTemplate`, `PrintTemplateVersion`, `DocumentPreview`, `SignedDocument`, `SignedDocumentSnapshot`, `DocumentSignature` and `DocumentAccessEvent` ORM models in `wtnapp/models/print_document_model.py`
- [x] T007 Register print document ORM models for `create_all()` and Alembic metadata in `wtnapp/models/__init__.py`
- [x] T008 Create idempotent Alembic migration with tables, indexes, constraints, RLS and append-only triggers in `wtnapp/alembic/versions/`
- [x] T009 Create idempotent default template seed definitions for `context_report`, `gap_report` and `soa_report` in `wtnapp/data/print_template_seed.py`
- [x] T010 Create Pydantic request/response schemas for templates, previews, signed documents and verification in `wtnapp/schemas/print_document_schema.py`
- [x] T011 Create encrypted local PDF storage helper with hash calculation and storage-key redaction in `wtnapp/utils/document_storage.py`
- [x] T012 Create controlled template selection and validation service skeleton in `wtnapp/services/print_template_service.py`
- [x] T013 Create artifact snapshot service skeleton for Contexto, Gap and SoA in `wtnapp/services/print_snapshot_service.py`
- [x] T014 Create ReportLab renderer service skeleton for preview and signed PDFs in `wtnapp/services/print_render_service.py`
- [x] T015 Create generic document signature service skeleton in `wtnapp/services/document_signature_service.py`
- [x] T016 Create `/print-documents` router skeleton with RBAC dependencies and tenant context in `wtnapp/routers/print_documents.py`
- [x] T017 Register the print documents router in `wtnapp/main.py`
- [x] T018 Add print document API method placeholders in `wtnadmin/src/app/core/api.service.ts`

**Checkpoint**: Foundation ready. User stories can start.

---

## Phase 3: User Story 1 - Pre-visualizar Documento Controlado (Priority: P1) MVP

**Goal**: Authorized users can generate and download preliminary previews for Contexto consolidated
report, Gap Analysis and SoA without creating a signed document.

**Independent Test**: Generate preview for each supported document type, download the preliminary PDF,
verify tenant identification/classification/template/status, and confirm no signed document exists.

### Tests for User Story 1 (MANDATORY)

- [x] T019 [P] [US1] Add backend happy-path preview tests for `context_report`, `gap_report` and `soa_report` in `wtnapp/test/test_print_document_preview.py`
- [x] T020 [P] [US1] Add preview/download tenant isolation tests with 404/403, Super Admin explicit-context/no-context cases and denied audit assertions in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [x] T021 [P] [US1] Add insufficient source data, missing required template variable, optional missing variable warning, storage-failure, missing encryption key, classification-denied preliminary download, suspended-organization and preliminary watermark tests in `wtnapp/test/test_print_document_preview_failures.py`
- [x] T022 [P] [US1] Add frontend preview component tests for loading, empty/error states and PDF download action in `wtnadmin/src/app/shared/document-preview/document-preview.spec.ts`

### Implementation for User Story 1

- [x] T023 [US1] Implement deterministic Contexto consolidated, Gap Analysis and SoA snapshot builders with artifact fingerprints in `wtnapp/services/print_snapshot_service.py`
- [x] T024 [US1] Implement default template resolution, active template validation and required/optional variable resolution in `wtnapp/services/print_template_service.py`
- [x] T025 [US1] Implement ReportLab preliminary PDF rendering with visible "Nao assinado / Preview" marking, optional missing variables rendered as "Nao informado", render timeout handling and no signature seal in `wtnapp/services/print_render_service.py`
- [x] T026 [US1] Implement encrypted write/read/delete-expired-preview behavior for preliminary PDFs in `wtnapp/utils/document_storage.py`
- [x] T027 [US1] Implement `POST /print-documents/previews`, `GET /print-documents/previews/{preview_id}` and `GET /print-documents/previews/{preview_id}/pdf` with minimum data validation, suspended-organization guard, module view permission and classification read enforcement in `wtnapp/routers/print_documents.py`
- [x] T028 [US1] Add preview creation, preliminary download and denied-access audit logging without PDF content or storage keys in `wtnapp/routers/print_documents.py`
- [x] T029 [P] [US1] Implement frontend API methods for preview metadata and preliminary PDF blob downloads in `wtnadmin/src/app/core/api.service.ts`
- [x] T030 [P] [US1] Create reusable document preview UI component with Signals and OnPush in `wtnadmin/src/app/shared/document-preview/document-preview.ts`
- [x] T031 [US1] Add "Pre-visualizar relatorio" action for Contexto consolidated report in `wtnadmin/src/app/pages/context-overview/context-overview.ts`
- [x] T032 [US1] Add "Gerar documento" preview action for Gap Analysis in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [x] T033 [US1] Add "Pre-visualizar/baixar preliminar" action for SoA in `wtnadmin/src/app/pages/soa/soa.ts`
- [x] T034 [US1] Ensure preview UI shows classification, template version, expiry, status and clear preliminary state in `wtnadmin/src/app/shared/document-preview/document-preview.ts`

**Checkpoint**: US1 independently functional with preview and preliminary PDF download.

---

## Phase 4: User Story 2 - Assinar e Congelar Documento (Priority: P1)

**Goal**: Authorized approvers can sign a valid preview and generate immutable signed PDFs with hash,
template version, signer metadata and custody trail.

**Independent Test**: Generate a preview, sign it, download final PDF, then mutate source artifact or
template and verify the signed PDF and metadata remain unchanged.

### Tests for User Story 2 (MANDATORY)

- [x] T035 [P] [US2] Add backend signing happy-path and immutable PDF tests in `wtnapp/test/test_print_document_signing.py`
- [x] T036 [P] [US2] Add stale preview, expired preview, permission denied, suspended-organization, renderer timeout and storage fail-closed tests in `wtnapp/test/test_print_document_signing_failures.py`
- [x] T037 [P] [US2] Add cross-tenant sign/final PDF download denial tests plus Super Admin explicit-context signing audit tests in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [x] T038 [P] [US2] Add frontend sign-flow tests for permission-gated button, confirmation and signed result state in `wtnadmin/src/app/shared/document-preview/document-preview-sign.spec.ts`

### Implementation for User Story 2

- [x] T039 [US2] Implement document-type to permission mapping for `approve_context_document`, `approve_gap_baseline` and `approve_soa` in `wtnapp/services/document_signature_service.py`
- [x] T040 [US2] Implement stale/expired preview validation against current artifact fingerprint and template hash in `wtnapp/services/document_signature_service.py`
- [x] T041 [US2] Implement signed document transaction that creates `SignedDocument`, `SignedDocumentSnapshot` and `DocumentSignature` records in `wtnapp/services/document_signature_service.py`
- [x] T042 [US2] Implement final signed PDF rendering with identifier, status, signer metadata, date/time, classification and hash in `wtnapp/services/print_render_service.py`
- [x] T043 [US2] Implement encrypted final PDF storage, SHA-256 verification and size validation in `wtnapp/utils/document_storage.py`
- [x] T044 [US2] Implement `POST /print-documents/previews/{preview_id}/sign` in `wtnapp/routers/print_documents.py`
- [x] T045 [US2] Mark signed previews and derive next signed document version number per tenant/source in `wtnapp/services/document_signature_service.py`
- [x] T046 [US2] Add signature, final PDF generation, download denial and failed-signature audit events in `wtnapp/routers/print_documents.py`
- [x] T047 [P] [US2] Implement frontend API methods for sign preview and final signed PDF download in `wtnadmin/src/app/core/api.service.ts`
- [x] T048 [US2] Add sign confirmation, success state and signed PDF download action to `wtnadmin/src/app/shared/document-preview/document-preview.ts`
- [x] T049 [US2] Gate sign actions by module approval permissions in `wtnadmin/src/app/shared/document-preview/document-preview.ts`
- [x] T050 [US2] Wire signed preview flow into Contexto, Gap and SoA pages in `wtnadmin/src/app/pages/context-overview/context-overview.ts`, `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts` and `wtnadmin/src/app/pages/soa/soa.ts`

**Checkpoint**: US2 independently functional after US1, with immutable signed PDF and permission checks.

---

## Phase 5: User Story 3 - Gerenciar Templates de Impressao (Priority: P2)

**Goal**: Org Admins can list system templates, create tenant templates, add immutable versions and
activate the version used by future previews.

**Independent Test**: Create and activate a tenant template for Gap Analysis, generate preview using
that template, sign a document, then activate a newer template and verify old signed document keeps the
original template version.

### Tests for User Story 3 (MANDATORY)

- [x] T051 [P] [US3] Add backend tests for system template seed idempotency, listing and active-version selection in `wtnapp/test/test_print_document_templates.py`
- [x] T052 [P] [US3] Add tenant template create/version/activate isolation tests, including Super Admin explicit-context template access, in `wtnapp/test/test_tenant_isolation_print_documents.py`
- [x] T053 [P] [US3] Add frontend template administration tests for create, version and activate flows in `wtnadmin/src/app/pages/print-templates/print-templates.spec.ts`

### Implementation for User Story 3

- [x] T054 [US3] Implement idempotent system template seed application for Contexto, Gap and SoA in `wtnapp/data/print_template_seed.py`
- [x] T055 [US3] Wire the idempotent template seed into the generated Feature 009 Alembic migration in `wtnapp/alembic/versions/`
- [x] T056 [US3] Implement tenant template create, immutable version creation, controlled-variable validation and activation without mutating `PrintTemplateVersion` rows in `wtnapp/services/print_template_service.py`
- [x] T057 [US3] Implement `GET /print-documents/templates`, `POST /print-documents/templates`, `POST /print-documents/templates/{template_id}/versions` and activate endpoint in `wtnapp/routers/print_documents.py`
- [x] T058 [US3] Add sanitized audit logging for template create, version create and activation in `wtnapp/routers/print_documents.py`
- [x] T059 [P] [US3] Implement frontend API methods for template list, create, version and activate in `wtnadmin/src/app/core/api.service.ts`
- [x] T060 [P] [US3] Create print template administration page with controlled section/variable form in `wtnadmin/src/app/pages/print-templates/print-templates.ts`
- [x] T061 [US3] Register `/app/print-templates` route with `manage_print_templates` guard in `wtnadmin/src/app/app.routes.ts`
- [x] T062 [US3] Add "Templates de impressao" navigation item for authorized users in `wtnadmin/src/app/pages/shell/shell.ts`
- [x] T063 [US3] Ensure preview generation can select tenant template versions without changing signed documents in `wtnapp/services/print_template_service.py`

**Checkpoint**: US3 functional with system defaults and tenant custom templates.

---

## Phase 6: User Story 4 - Consultar Historico e Verificar Integridade (Priority: P2)

**Goal**: Authorized users can list signed document history, download prior versions and verify
integrity without depending on the current artifact state.

**Independent Test**: Sign more than one Gap Analysis document, list history, download the older
version and verify hash/identifier after source artifact and template changes.

### Tests for User Story 4 (MANDATORY)

- [x] T064 [P] [US4] Add signed history, previous-version download, classification-restricted download and obsolete-state tests in `wtnapp/test/test_print_document_history.py`
- [x] T065 [P] [US4] Add integrity verification and tampered-storage failure tests in `wtnapp/test/test_print_document_integrity.py`
- [x] T066 [P] [US4] Add frontend history and verify action tests in `wtnadmin/src/app/shared/document-history/document-history.spec.ts`

### Implementation for User Story 4

- [x] T067 [US4] Implement `GET /print-documents/signed`, `GET /print-documents/signed/{document_id}`, final PDF download and verify endpoints with classification read enforcement in `wtnapp/routers/print_documents.py`
- [x] T068 [US4] Implement signed document history filtering by document type and source artifact in `wtnapp/services/document_signature_service.py`
- [x] T069 [US4] Implement PDF hash and snapshot hash integrity verification in `wtnapp/services/document_signature_service.py`
- [x] T070 [US4] Derive obsolete status for older signed documents without mutating append-only records in `wtnapp/services/document_signature_service.py`
- [x] T071 [US4] Add sanitized audit logging for history, final download and verify events in `wtnapp/routers/print_documents.py`
- [x] T072 [P] [US4] Implement frontend API methods for signed history, final download and verify in `wtnadmin/src/app/core/api.service.ts`
- [x] T073 [P] [US4] Create reusable signed document history component in `wtnadmin/src/app/shared/document-history/document-history.ts`
- [x] T074 [US4] Integrate signed document history into Contexto, Gap and SoA pages in `wtnadmin/src/app/pages/context-overview/context-overview.ts`, `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts` and `wtnadmin/src/app/pages/soa/soa.ts`

**Checkpoint**: US4 functional with history, download and integrity verification.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T075 [P] Run backend print document tests listed in quickstart in `wtnapp/test/test_print_document_preview.py`, `wtnapp/test/test_print_document_signing.py`, `wtnapp/test/test_print_document_templates.py`, `wtnapp/test/test_print_document_history.py`, `wtnapp/test/test_print_document_integrity.py` and `wtnapp/test/test_tenant_isolation_print_documents.py`
- [x] T076 [P] Run frontend unit tests for print document UI and affected pages in `wtnadmin/src/app/shared/document-preview/document-preview.spec.ts`, `wtnadmin/src/app/shared/document-history/document-history.spec.ts`, `wtnadmin/src/app/pages/print-templates/print-templates.spec.ts`, `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`, `wtnadmin/src/app/pages/soa/soa.spec.ts` and `wtnadmin/src/app/pages/context-overview/context-overview.spec.ts`
- [x] T077 Verify `alembic upgrade head` is idempotent by running it twice against PostgreSQL and updating the generated Feature 009 migration if needed in `wtnapp/alembic/versions/`
- [x] T078 Run the quickstart validation flow and update any drift in `specs/009-signable-print-documents/quickstart.md`
- [x] T079 Audit all new `AuditService.log_from_request()` calls for no PDF content, snapshot JSON, storage key, path, token or PII leakage in `wtnapp/routers/print_documents.py`
- [x] T080 Sweep all print document queries for `scoped_query` or explicit tenant context enforcement in `wtnapp/routers/print_documents.py`, `wtnapp/services/print_template_service.py` and `wtnapp/services/document_signature_service.py`
- [x] T081 Run frontend production build and fix any type/template errors in `wtnadmin/src/app/core/models.ts`, `wtnadmin/src/app/core/api.service.ts` and print document components
- [x] T082 Add lightweight preview/sign timing and timeout smoke coverage for `DOCUMENT_RENDER_TIMEOUT_SECONDS` in `wtnapp/test/test_print_document_performance.py`
- [x] T083 Update feature completion notes and known operational settings in `specs/009-signable-print-documents/plan.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks all user stories.
- **US1 Preview (Phase 3)**: depends on Foundational and is the first demoable MVP.
- **US2 Signing (Phase 4)**: depends on US1 because signing requires a valid preview.
- **US3 Templates (Phase 5)**: depends on Foundational; can run after US1 if default templates exist.
- **US4 History/Verify (Phase 6)**: depends on US2 because it needs signed documents.
- **Polish (Phase 7)**: depends on selected user stories.

### User Story Dependency Graph

```text
Setup -> Foundational -> US1 -> US2 -> US4 -> Polish
                         |
                         +-> US3 -> Polish
```

### Within Each User Story

- Tests, including tenant isolation where applicable, are written first and should fail before implementation.
- Models and migrations precede services.
- Services precede routers.
- Routers and API service precede UI integration.
- Audit and tenant isolation checks are part of each story, not deferred polish.

## Parallel Execution Examples

### US1 Preview

```bash
Task A: T019 backend preview happy-path tests
Task B: T020 tenant isolation tests
Task C: T022 frontend preview component tests
Task D: T023 snapshot builders
Task E: T030 shared preview UI
```

### US2 Signing

```bash
Task A: T035 signing happy-path tests
Task B: T036 signing failure tests
Task C: T038 frontend sign-flow tests
Task D: T042 final PDF renderer
Task E: T047 frontend API sign/download methods
```

### US3 Templates

```bash
Task A: T051 backend template tests
Task B: T053 frontend template admin tests
Task C: T054 seed definitions
Task D: T060 template admin page
```

### US4 History & Verification

```bash
Task A: T064 history tests
Task B: T065 integrity tests
Task C: T066 frontend history tests
Task D: T073 history component
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to deliver preview and preliminary PDF download.
3. Stop and validate preview for Contexto, Gap and SoA.
4. Complete US2 to reach the operational MVP with immutable signed PDFs.

### Incremental Delivery

1. US1 delivers safe preview without signing.
2. US2 adds formal signature, immutable PDF and custody.
3. US3 adds tenant template customization while preserving signed documents.
4. US4 adds audit-facing history and integrity verification.

## Format Validation

- All tasks use `- [ ] T###` checklist format.
- All user story tasks include `[US1]`, `[US2]`, `[US3]` or `[US4]`.
- `[P]` marks tasks that can run in parallel because they target different files or independent tests.
- Every task references at least one concrete file path.
