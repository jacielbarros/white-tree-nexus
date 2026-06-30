# Phase 0 Research — Repositório Transversal de Evidências + Auditoria Interna (5a)

Todas as decisões abaixo resolvem o Technical Context. Nenhum `NEEDS CLARIFICATION` remanescente
(as 5 ambiguidades de alto impacto já foram fechadas no `/speckit.clarify`).

## D1 — Store de evidências: unificado com vínculo polimórfico 1..N

- **Decisão**: criar um domínio `evidence_*` transversal (4 tabelas: `evidence`, `evidence_version`,
  `evidence_link`, `evidence_event`). A evidência é objeto de 1ª classe do tenant, **sem FK direta** a
  um artefato; os vínculos vivem em `evidence_link` (polimórfico: `target_type` + `target_id`), 1..N
  por evidência.
- **Rationale**: a clarify (Q1) escolheu repositório unificado reutilizável. Separar o vínculo da
  evidência habilita "repositório central pesquisável", reuso da mesma evidência em vários artefatos
  e extensão para alvos da 5b sem redesenho.
- **Alternativas rejeitadas**: (a) manter `gap_evidence` e criar tabelas paralelas por artefato —
  duplicação e múltiplas trilhas de custódia, contra o Core Principle IV; (b) FK única de evidência →
  artefato (1:1) — impede reuso e repositório central de verdade.

## D2 — Migração da Feature 008 (sem quebrar)

- **Decisão**: a migration nova **copia** `gap_evidence` → `evidence`, `gap_evidence_version` →
  `evidence_version`, `gap_evidence_event` → `evidence_event`, e cria uma linha `evidence_link`
  (`target_type=gap_item`, `target_id=assessment_item_id`) por evidência. Em seguida **dropa** as
  tabelas `gap_evidence*`. O router `gap_evidence.py` é **adaptado** para delegar ao
  `evidence_service` filtrando por `target_type=gap_item`, **preservando os mesmos paths e contratos**
  (`/gap/assessment/items/{item_id}/evidences...`). A UI do Gap não muda.
- **Rationale**: preserva 100% do histórico/hash/autoria e a experiência do 008 (FR-014, SC-011),
  enquanto unifica a base. O contrato público do Gap permanece estável (backward-compat por padrão).
- **Idempotência/reversibilidade**: criação de tabelas guardada por `_table_exists`; cópia idempotente
  (não duplica se `evidence` já populada para o id); `downgrade` recria `gap_evidence*` e copia de
  volta. Em DB zerado (`create_all` já criou `evidence*` e **não** `gap_evidence*`), os passos de
  cópia/drop viram no-op (guardas de existência).
- **Alternativas rejeitadas**: manter as duas bases em paralelo (viola unificação da Q1; duas trilhas
  de custódia).

## D3 — Cifragem em repouso (reconcilia clarify Q5)

- **Decisão**: reusar `utils/evidence_storage.py`, que **já cifra** o conteúdo com Fernet
  (`FIELD_ENCRYPTION_KEY`, fail-closed) e calcula SHA-256. **Não** introduzir um segundo esquema de
  cifragem de aplicação.
- **Rationale**: a clarify Q5 (storage + acesso por classificação, sem *novo* esquema de cifragem de
  aplicação) é satisfeita reusando a cifragem já existente — isso é estritamente mais seguro que
  "sem cifragem" e evita regressão do 008 e tensão com o Core Principle V. O controle de acesso ao
  **conteúdo** continua por RBAC + `classification_access` (confidencial/restrito exige permissão
  elevada).
- **Nota**: registramos a nuance explicitamente para o usuário — a interpretação operacional de Q5 é
  "sem cifragem *adicional*", não "desligar a cifragem do storage".

## D4 — Taxonomia de alvo canônica (`SgsiArtifactType`)

- **Decisão**: um enum único `SgsiArtifactType` compartilhado por `evidence_link` e pelos vínculos de
  checklist/constatação: `soa_item`, `gap_item`, `risk`, `asset`, `audit_finding` (extensível;
  5b adiciona `nonconformity`, `corrective_action`). Os alvos apontam para **linhas tenant-scoped já
  existentes** (clarify Q4): controle do Anexo A = `soa_item`; cláusula/controle = `gap_catalog_item`
  (item de avaliação do Gap); `risk`; `asset`.
- **Rationale**: taxonomia única evita divergência entre vínculo de evidência e de constatação, mantém
  tudo tenant-scoped e navegável; nada de códigos normativos abstratos de plataforma.
- **Validação de alvo**: a existência do alvo é verificada por `scoped_query` no tenant antes de criar
  o vínculo; alvo inexistente/cross-tenant ⇒ 404 genérico + audit.
- **Alternativas rejeitadas**: enums separados por módulo (divergência); referência a código normativo
  abstrato (não tenant-scoped, não navegável — clarify Q4 rejeitou).

## D5 — Constatação no nível da auditoria; checklist manual + importação opcional

- **Decisão**: `internal_audit_finding` pertence à **auditoria** (`audit_id` obrigatório) e referencia
  um `checklist_item_id` **opcional** (clarify Q2). O checklist é **manual** com endpoint de
  **importação opcional** de controles/cláusulas do escopo SoA/Gap (clarify Q3) — nunca auto-populado.
- **Rationale**: flexibilidade para achados espontâneos sem item planejado; reduz acoplamento ao
  estado vivo da SoA/Gap.

## D6 — Constatação promovível para a 5b

- **Decisão**: `finding_type ∈ {nc_maior, nc_menor}` ⇒ `promotable = true` e coluna reservada
  `nonconformity_ref` (UUID nullable, **vazia** nesta feature). Demais tipos ⇒ não promovível.
- **Rationale**: prepara o gancho da 5b (FR-026) sem implementar a NC; o vínculo é um campo simples a
  ser preenchido depois.

## D7 — Relatório de auditoria como Documento Controlado

- **Decisão**: reusar `controlled_document_service` + `document_versions` com novo
  `DocType.internal_audit_report`. `InternalAudit` ganha `current_report_version_id` + `draft_status`
  (padrão SoA/risk plan). `snapshot_factory` consolida escopo, critérios, itens auditados e
  constatações (tipos + vínculos + evidências referenciadas). Assinatura avançada **opcional** na
  aprovação via `signature_service`. Export PDF reusa o padrão `soa_export_service` (reportlab) a
  partir do `content_snapshot`.
- **Gate duro (FR-029)**: aprovação bloqueada se a auditoria não estiver `completed` **ou** houver
  item de checklist com `result=pendente` (sem campo `mandatory` — usa o enum `AuditChecklistResult`);
  navegar/editar/rascunhar sob gates suaves.
- **Rationale**: máximo reuso, zero dependência nova, alinhado ao padrão de SoA (005) e Plano de Risco
  (012).

## D8 — Timeline e dashboard (read-only)

- **Decisão**: `traceability_service` agrega, por `target_type`+`target_id`, os `evidence_event` +
  `evidence_link` + `internal_audit_finding` que referenciam o alvo, em ordem cronológica, **somente
  metadados** (sem conteúdo/`storage_key`). `audit_metrics_service` produz contagens simples
  (evidências por status/classificação, auditorias por status, constatações por tipo). Card de
  readiness em `dashboard_service` (`DashboardModuleId.internal_audit`).
- **Rationale**: capacidade de leitura sobre trilhas append-only já existentes; sem motor de KPIs (9.1).

## D9 — Permissões e papéis

- **Decisão**: novas permissões — `view_evidence`, `manage_evidence`, `view_internal_audit`,
  `manage_internal_audit`, `approve_audit_report`. Concessão:
  - `view_evidence`/`view_internal_audit`: todos os papéis com acesso ao tenant exceto
    Colaborador convidado (espelha `view_gap`/`view_soa`).
  - `manage_evidence`: super_admin, org_admin, consultant, **internal_auditor** (anexar evidência a
    constatações).
  - `manage_internal_audit`: super_admin, org_admin, consultant, **internal_auditor**.
  - `approve_audit_report`: super_admin, org_admin (aprovação formal — espelha `approve_soa`).
- **Rationale**: nome `*_internal_audit` deliberadamente distinto de um futuro `view_audit` (leitura
  de audit logs) para evitar colisão (registrado na spec SEC-002). Acesso ao **conteúdo** de evidência
  confidencial/restrita continua barrado por `classification_access` independentemente de
  `view_evidence`.

## D10 — Migration: resolução dos dois heads

- **Decisão**: a revisão nova tem `down_revision = ("a9b0c1d2e308", "d3e4f5a6b217")` (merge dos heads
  atuais: Feature 007 gap_guidance + Feature 013 soa_risk_normative), tornando-se o **head único**.
  Idempotente conforme as regras do CLAUDE.md (guardas `_table_exists`/checagem de coluna; RLS com
  `DROP POLICY IF EXISTS`; triggers `CREATE OR REPLACE`/`IF NOT EXISTS`).
- **Rationale**: o repositório está com histórico ramificado; um merge limpo restaura `alembic upgrade
  head` determinístico. (O bug pré-existente do Gap que falha o upgrade a partir do zero é
  independente desta feature.)
