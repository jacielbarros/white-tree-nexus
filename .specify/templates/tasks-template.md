---

description: "Task list template for feature implementation"
---

# Tasks: [FEATURE NAME]

**Input**: Design documents from `/specs/[###-feature-name]/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: ⚠️ **OVERRIDE da constitution (White Tree Nexus):** ao contrário do default do Spec Kit,
testes NÃO são opcionais aqui. Toda feature que toca dados de domínio DEVE incluir, no mínimo,
**teste de isolamento de tenant** + testes dos casos de falha principais. (Constitution,
Princípio VI + Definition of Done.)

**Organization**: Tasks são agrupadas por user story para implementação/teste independentes.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Pode rodar em paralelo (arquivos diferentes, sem dependências)
- **[Story]**: A qual user story a task pertence (US1, US2, ...)
- Inclua caminhos de arquivo exatos nas descrições

## Path Conventions (White Tree Nexus — web monorepo)

- Backend: `wtnapp/` (models, schemas, routers, services, helpers, test)
- Frontend: `wtnadmin/src/app/` (core, pages, shared)
- Ajuste conforme a Structure Decision do plan.md

<!--
  IMPORTANT: As tasks abaixo são EXEMPLOS. O /speckit.tasks deve substituí-las por tasks reais
  derivadas de spec.md (user stories + SEC-* requirements), plan.md, data-model.md e contracts/.
  NÃO manter as tasks de exemplo no tasks.md gerado.
-->

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Create project structure per implementation plan
- [ ] T002 Initialize project with framework dependencies
- [ ] T003 [P] Configure linting and formatting tools

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Infraestrutura central que DEVE estar pronta antes de QUALQUER user story.

**⚠️ CRITICAL**: Nenhuma user story começa antes desta fase terminar.

- [ ] T004 Setup database schema and migrations (modelos com `tenant_id`)
- [ ] T005 [P] Auth/RBAC: `require_permission(...)` disponível para esta feature
- [ ] T006 [P] Tenant scope: garantir que `helpers/tenant_scope.py` cobre as entidades desta feature
- [ ] T007 Create base models/entities que todas as stories dependem
- [ ] T008 Configure error handling e logging (sem vazar PII/dados sensíveis)

**Checkpoint**: Fundação pronta — user stories podem começar.

---

## Phase 3: User Story 1 - [Title] (Priority: P1) 🎯 MVP

**Goal**: [O que esta story entrega]

**Independent Test**: [Como verificar que funciona sozinha]

### Tests for User Story 1 (MANDATORY) ⚠️

> Escreva estes testes PRIMEIRO e garanta que FALHAM antes de implementar.

- [ ] T010 [P] [US1] **Tenant isolation test**: usuário do tenant A NÃO acessa [recurso] do
  tenant B (404/403 + audit) em `wtnapp/test/test_[name]_tenant_isolation.py`
- [ ] T011 [P] [US1] Contract/integration test do happy path em `wtnapp/test/test_[name].py`
- [ ] T012 [P] [US1] Test dos casos de falha principais (permissão negada, validação) 

### Implementation for User Story 1

- [ ] T013 [P] [US1] Create [Entity] model (com `tenant_id`) em `wtnapp/models/[entity]_model.py`
- [ ] T014 [US1] Implement service em `wtnapp/services/[service].py`
- [ ] T015 [US1] Implement endpoint em `wtnapp/routers/[domain].py` (escopado por tenant +
  `require_permission` + audit log) e registrar em `main.py`
- [ ] T016 [US1] Add validation, error handling (mensagens que não vazam internals) e audit log
- [ ] T017 [P] [US1] UI em `wtnadmin/src/app/pages/[feature]/` (signals, OnPush, Reactive Forms)

**Checkpoint**: User Story 1 funcional e testável independentemente, com isolamento verificado.

---

## Phase 4: User Story 2 - [Title] (Priority: P2)

**Goal**: [...]

### Tests for User Story 2 (MANDATORY) ⚠️

- [ ] T018 [P] [US2] Tenant isolation test
- [ ] T019 [P] [US2] Integration test do happy path + casos de falha

### Implementation for User Story 2

- [ ] T020 [P] [US2] Models / [ ] T021 [US2] Service / [ ] T022 [US2] Endpoint (tenant + RBAC + audit)

**Checkpoint**: US1 e US2 funcionam independentemente.

---

[Adicione mais fases de user story conforme necessário, seguindo o mesmo padrão]

---

## Phase N: Polish & Cross-Cutting Concerns

- [ ] TXXX [P] Documentation updates em docs/
- [ ] TXXX Code cleanup e refactoring
- [ ] TXXX **Audit review**: confirmar que toda operação sensível gera log e que nenhum
  log/erro/telemetria expõe PII, segredos ou conteúdo de evidência
- [ ] TXXX **Tenant isolation sweep**: revisar que nenhuma query nova escapou do `tenant_scope`
- [ ] TXXX Run quickstart.md validation

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: depende do Setup — BLOQUEIA todas as user stories
- **User Stories (Phase 3+)**: dependem da Foundational; podem ir em paralelo ou em ordem de
  prioridade (P1 → P2 → P3)
- **Polish (final)**: depende das stories desejadas

### Within Each User Story

- Tests (incl. **isolamento de tenant**) escritos e FALHANDO antes da implementação
- Models antes de services; services antes de endpoints; core antes de integração
- Story completa antes da próxima prioridade

### Parallel Opportunities

- Tasks [P] = arquivos diferentes, sem dependências
- Tests [P] de uma story podem rodar em paralelo
- Stories diferentes podem ser tocadas por devs diferentes após a Foundational

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup
2. Phase 2: Foundational (CRITICAL)
3. Phase 3: User Story 1 (incl. teste de isolamento)
4. **STOP e VALIDE**: testar US1 independentemente
5. Deploy/demo se pronto

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. US1 → testa → demo (MVP!) → US2 → testa → demo → ...
3. Cada story agrega valor sem quebrar as anteriores

---

## Notes

- [P] = arquivos diferentes, sem dependências
- [Story] mapeia task → user story (rastreabilidade)
- **Teste de isolamento de tenant é obrigatório** por feature de domínio (não é "polish")
- Verifique que os testes falham antes de implementar
- Commit após cada task ou grupo lógico
- Evite: tasks vagas, conflito no mesmo arquivo, dependências cross-story que quebram independência
