# Tasks: Anexos e Evidencias na Matriz do Gap Analysis

**Input**: Design documents from `/specs/008-gap-evidence-attachments/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/openapi.yaml, quickstart.md

**Tests**: Obrigatorios pela constitution da White Tree Nexus: teste de isolamento de tenant, casos de falha principais, RBAC, audit e UI.

**Organization**: Tasks agrupadas por user story para permitir implementacao e teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo se arquivos diferentes e sem dependencia de task incompleta.
- **[Story]**: US1, US2, US3 apenas nas fases de user story.
- Cada task inclui caminhos exatos de arquivo.

---

## Phase 1: Setup (Shared Infrastructure)

- [X] T001 Add `python-multipart` backend dependency in `requirements.txt`
- [X] T002 Add evidence storage settings and `GapEvidenceStatus`/`GapEvidenceEventType` enums in `wtnapp/settings.py`
- [X] T003 [P] Add reusable evidence TypeScript interfaces in `wtnadmin/src/app/core/models.ts`
- [X] T004 [P] Add evidence upload/download helper methods in `wtnadmin/src/app/core/api.service.ts`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared schema, storage, security, and model foundation required before any story endpoint/UI is implemented.

**CRITICAL**: Nenhuma user story comeca antes desta fase terminar.

### Tests for Foundation

- [X] T005 [P] Add storage unit tests for size, extension, SHA-256, Fernet encryption, and missing `FIELD_ENCRYPTION_KEY` in `wtnapp/test/test_gap_evidence_storage.py`
- [X] T006 [P] Add model invariant tests for version/event append-only triggers in `wtnapp/test/test_gap_evidence_model.py`
- [X] T007 [P] Add migration smoke test coverage for evidence tables, tenant_id columns, indexes, and RLS assumptions in `wtnapp/test/test_gap_evidence_migration.py`

### Implementation for Foundation

- [X] T008 Implement encrypted local evidence storage utility in `wtnapp/utils/evidence_storage.py`
- [X] T009 Create evidence ORM models with tenant_id, versioning fields, and append-only triggers in `wtnapp/models/gap_evidence_model.py`
- [X] T010 Register evidence ORM models in `wtnapp/models/__init__.py`
- [X] T011 Create Alembic migration for `gap_evidence`, `gap_evidence_version`, `gap_evidence_event`, indexes, RLS, and triggers in `wtnapp/alembic/versions/c1d2e3f4a509_gap_evidence_attachments.py`
- [X] T012 Create Pydantic schemas for evidence summaries, versions, events, history, and requests in `wtnapp/schemas/gap_evidence_schema.py`
- [X] T013 Add shared evidence response mappers and sanitized event helpers in `wtnapp/routers/gap_evidence.py`

**Checkpoint**: Storage, schema, models, migration, and DTOs are ready for story endpoints.

---

## Phase 3: User Story 1 - Anexar Evidencia a um Item do Gap (Priority: P1) MVP

**Goal**: A user with `manage_gap` attaches a valid file to a selected Gap Analysis item, with metadata, classification, hash, audit, and no automatic item status change.

**Independent Test**: With an authenticated organization and existing Gap item, upload a valid evidence file and verify it appears linked to the correct item and tenant with author, date, size, type, classification, and integrity metadata.

### Tests for User Story 1 (MANDATORY)

- [X] T014 [P] [US1] Add backend upload happy-path test for evidence, version 1, SHA-256, encrypted file, audit, and unchanged item status in `wtnapp/test/test_gap_evidence.py`
- [X] T015 [P] [US1] Add backend invalid upload tests for empty, oversized, disallowed extension, invalid classification, and missing encryption key in `wtnapp/test/test_gap_evidence.py`
- [X] T016 [P] [US1] Add backend RBAC test proving `view_gap` cannot upload and `manage_gap` can upload in `wtnapp/test/test_gap_evidence.py`
- [X] T017 [P] [US1] Add tenant isolation upload test preventing tenant B from attaching evidence to tenant A item in `wtnapp/test/test_tenant_isolation_gap_evidence.py`
- [X] T018 [P] [US1] Add frontend upload form test for required classification default `uso_interno`, FormData payload, and manage-only action in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`

### Implementation for User Story 1

- [X] T019 [US1] Implement item-scoped upload endpoint `POST /gap/assessment/items/{item_id}/evidences` with `manage_gap`, scoped item lookup, storage write, version 1, audit, and sanitized errors in `wtnapp/routers/gap_evidence.py`
- [X] T020 [US1] Register `gap_evidence.router` in `wtnapp/main.py`
- [X] T021 [US1] Add frontend upload state, file input handling, description control, classification control, and submit logic in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T022 [US1] Render manage-only upload UI inside the selected item side panel in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T023 [US1] Refresh selected item evidence list after successful upload without changing assessment status in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T024 [US1] Show upload success and validation error messages without exposing backend internals in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`

**Checkpoint**: US1 is independently functional: a manager can attach evidence to an item and see it appear with correct metadata.

---

## Phase 4: User Story 2 - Consultar Evidencias Anexadas no Painel da Matriz (Priority: P2)

**Goal**: A user with `view_gap` selects an item and sees the separate "Evidencias anexadas" section with only active/current evidences for that item and tenant.

**Independent Test**: With evidences already attached to an item, open the matrix, select the item, and verify the side panel lists only evidences for that item and organization while keeping "Evidencias esperadas" separate.

### Tests for User Story 2 (MANDATORY)

- [X] T025 [P] [US2] Add backend list metadata test proving `GET /gap/assessment/items/{item_id}/evidences` returns active/current item evidence and does not create content audit in `wtnapp/test/test_gap_evidence.py`
- [X] T026 [P] [US2] Add backend classification download tests for `publico`/`uso_interno` with `view_gap` and `confidencial`/`restrito` requiring `manage_gap` in `wtnapp/test/test_gap_evidence.py`
- [X] T027 [P] [US2] Add tenant isolation list/download tests preventing tenant B from listing or downloading tenant A evidence in `wtnapp/test/test_tenant_isolation_gap_evidence.py`
- [X] T028 [P] [US2] Add frontend render tests for separate "Evidencias esperadas" and "Evidencias anexadas" sections, metadata rows, and empty state in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`
- [X] T029 [P] [US2] Add frontend download permission test showing/hiding download action based on `can_download` in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`

### Implementation for User Story 2

- [X] T030 [US2] Implement item-scoped list endpoint `GET /gap/assessment/items/{item_id}/evidences` with `view_gap`, scoped item lookup, active/current filtering, and `can_download` in `wtnapp/routers/gap_evidence.py`
- [X] T031 [US2] Implement item-scoped download endpoint `GET /gap/assessment/items/{item_id}/evidences/{evidence_id}/download` with classification gates, storage decrypt/read, audit, and generic cross-tenant errors in `wtnapp/routers/gap_evidence.py`
- [X] T032 [US2] Load evidence metadata whenever `selectedItem` changes in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T033 [US2] Render the "Evidencias anexadas" section below "Evidencias esperadas" with empty state, file metadata, classification, uploaded date, uploader, size, and hash preview in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T034 [US2] Implement evidence download action using Blob response and user-safe error messages in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T035 [US2] Ensure evidence metadata loads do not block or reset the existing item assessment form in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`

**Checkpoint**: US2 is independently functional: any viewer can consult metadata for active/current evidences in the side panel and download only what classification allows.

---

## Phase 5: User Story 3 - Preservar Cadeia de Custodia das Evidencias (Priority: P3)

**Goal**: A manager can replace or logically inactivate evidence while preserving immutable versions/events and audit trail; only `manage_gap` can see history, previous versions, and inactive evidence.

**Independent Test**: Attach evidence, replace it with a new version, inactivate it, and verify history preserves author, date, action, original item link, current version, and audit without exposing file content.

### Tests for User Story 3 (MANDATORY)

- [X] T036 [P] [US3] Add backend replacement test proving required classification, new version number, current_version_id update, previous version preservation, event, and audit in `wtnapp/test/test_gap_evidence.py`
- [X] T037 [P] [US3] Add backend inactivation test proving logical removal hides evidence from list and preserves history for `manage_gap` in `wtnapp/test/test_gap_evidence.py`
- [X] T038 [P] [US3] Add backend history permission test proving users without `manage_gap` cannot see versions, inactive evidence, or events in `wtnapp/test/test_gap_evidence.py`
- [X] T039 [P] [US3] Add tenant isolation tests for replace, inactivate, and history endpoints in `wtnapp/test/test_tenant_isolation_gap_evidence.py`
- [X] T040 [P] [US3] Add audit sanitization test proving events/audit omit file content, `storage_key`, and path values in `wtnapp/test/test_gap_evidence.py`
- [X] T041 [P] [US3] Add frontend history/replace/inactivate visibility tests for `manage_gap` vs `view_gap` in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts`

### Implementation for User Story 3

- [X] T042 [US3] Implement replacement endpoint `POST /gap/assessment/items/{item_id}/evidences/{evidence_id}/versions` with `manage_gap`, required classification, new encrypted version, current pointer/classification update, event, and audit in `wtnapp/routers/gap_evidence.py`
- [X] T043 [US3] Implement logical inactivation endpoint `DELETE /gap/assessment/items/{item_id}/evidences/{evidence_id}` with `manage_gap`, status update, event, and audit in `wtnapp/routers/gap_evidence.py`
- [X] T044 [US3] Implement history endpoint `GET /gap/assessment/items/{item_id}/evidences/{evidence_id}/history` with `manage_gap` and sanitized versions/events in `wtnapp/routers/gap_evidence.py`
- [X] T045 [US3] Add frontend replace evidence dialog/state with current classification pre-filled and FormData submission in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T046 [US3] Add frontend inactivate evidence action with optional reason and list refresh in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T047 [US3] Add frontend history view for versions/events visible only when `canManage()` is true in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`
- [X] T048 [US3] Ensure inactive evidences and previous versions never render in the default viewer list in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`

**Checkpoint**: US3 is independently functional: managers can preserve custody/versioning without exposing history to regular viewers.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T049 [P] Update implementation notes and evidence validation commands in `specs/008-gap-evidence-attachments/quickstart.md`
- [X] T050 [P] Add `EVIDENCE_STORAGE_DIR`, `EVIDENCE_MAX_FILE_BYTES`, `EVIDENCE_ALLOWED_EXTENSIONS`, and `FIELD_ENCRYPTION_KEY` notes to `AGENTS.md`
- [X] T051 [P] Run backend evidence test suite and record failures/fixes in `specs/008-gap-evidence-attachments/quickstart.md`
- [X] T052 [P] Run frontend gap-analysis tests and record failures/fixes in `specs/008-gap-evidence-attachments/quickstart.md`
- [X] T053 Run `alembic upgrade head` twice against the development database to validate migration idempotence in `wtnapp/alembic/versions/c1d2e3f4a509_gap_evidence_attachments.py`
- [X] T054 Run audit review for all evidence operations and confirm no audit/error path exposes content, `storage_key`, file paths, tokens, or PII in `wtnapp/routers/gap_evidence.py`
- [X] T055 Run tenant isolation sweep for all evidence queries and confirm every domain query uses `scoped_query` or explicit `tenant_id == ctx.tenant_id` guards in `wtnapp/routers/gap_evidence.py`
- [X] T056 Run responsive UI check for the Gap side panel so evidence metadata, buttons, and form controls do not overflow in `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks all user stories.
- **US1 (Phase 3)**: depends on Foundational; MVP scope.
- **US2 (Phase 4)**: depends on US1 because list/download needs persisted evidence.
- **US3 (Phase 5)**: depends on US1 and US2 because history/versioning extends existing evidence records and list behavior.
- **Polish (Phase 6)**: depends on completed user stories.

### User Story Dependencies

- **US1**: independent MVP after foundation.
- **US2**: can be validated with seeded/uploaded evidence from US1.
- **US3**: requires existing evidence from US1 and list/download behavior from US2.

### Within Each User Story

- Tests first and failing before implementation.
- Backend behavior before frontend integration.
- Models/storage before routers.
- Routers before UI API calls.
- UI rendering after API contract behavior exists.

---

## Parallel Opportunities

- Foundation tests T005, T006, T007 can run in parallel.
- US1 tests T014, T015, T016, T017, T018 can be written in parallel.
- US2 tests T025, T026, T027, T028, T029 can be written in parallel.
- US3 tests T036, T037, T038, T039, T040, T041 can be written in parallel.
- Frontend-only tasks can run in parallel with backend tests after endpoint contracts are stable.
- Polish tasks T049, T050, T051, T052 can run in parallel after implementation.

### Parallel Example: US1

```text
Task A: T014 + T015 in wtnapp/test/test_gap_evidence.py
Task B: T017 in wtnapp/test/test_tenant_isolation_gap_evidence.py
Task C: T018 in wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts
```

### Parallel Example: US2

```text
Task A: T025 + T026 in wtnapp/test/test_gap_evidence.py
Task B: T027 in wtnapp/test/test_tenant_isolation_gap_evidence.py
Task C: T028 + T029 in wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts
```

### Parallel Example: US3

```text
Task A: T036 + T037 + T038 + T040 in wtnapp/test/test_gap_evidence.py
Task B: T039 in wtnapp/test/test_tenant_isolation_gap_evidence.py
Task C: T041 in wtnadmin/src/app/pages/gap-analysis/gap-analysis.spec.ts
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete US1 tests and implementation.
3. Validate: `pytest wtnapp/test/test_gap_evidence.py wtnapp/test/test_tenant_isolation_gap_evidence.py`.
4. Validate upload in the matrix side panel.
5. Stop and demo attach flow before moving to list/download/history polish.

### Incremental Delivery

1. Setup + Foundational: encrypted storage, models, migration, DTOs.
2. US1: upload evidence with metadata and audit.
3. US2: list/download evidence in the matrix panel with classification rules.
4. US3: replacement, inactivation, history, and custody chain.
5. Polish: migration idempotence, audit sweep, tenant sweep, frontend responsive pass.

### Suggested Commit Boundaries

- Commit 1: setup, settings, storage utility, models, migration, schemas.
- Commit 2: US1 backend + frontend upload flow.
- Commit 3: US2 list/download + frontend panel.
- Commit 4: US3 history/versioning/inactivation.
- Commit 5: polish, docs, validation fixes.
