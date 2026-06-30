# Phase 0 Research — NC/Ações Corretivas (10.2) + Análise Crítica (9.3) + PDCA (10.1)

Todas as decisões resolvem o Technical Context. As 5 ambiguidades de alto impacto foram fechadas no
`/speckit.clarify`; nenhum `NEEDS CLARIFICATION` remanescente.

## D1 — Promoção de constatação → NC (contrato com a 5a)

- **Decisão**: `POST /nonconformities/promote {finding_id}` lê a `InternalAuditFinding` (scoped no
  tenant), exige `promotable=true` e `nonconformity_ref IS NULL`, cria a NC semeando severidade
  (`nc_maior`→Maior, `nc_menor`→Menor), título/descrição e vínculo (target_type/target_id) da
  constatação, e **escreve** `internal_audit_finding.nonconformity_ref = nc.id`. **Idempotente**: se a
  constatação já tem `nonconformity_ref`, retorna a NC existente (não duplica). A constatação
  **permanece ativa**.
- **Rationale**: usa exatamente o gancho que a 5a deixou pronto (`promotable` + `nonconformity_ref`);
  é a única escrita desta feature num módulo consumido (documentada em Complexity Tracking). Preserva a
  rastreabilidade bidirecional auditoria↔NC sob append-only (a constatação não é apagada).
- **Alternativas rejeitadas**: encerrar/arquivar a constatação na promoção (clarify Q1=A descartou);
  N→1 (deferido).

## D2 — Análise Crítica como coleção de Documentos Controlados

- **Decisão**: `management_review` é uma **coleção** (uma linha por reunião), cada uma com
  `current_version_id` + `draft_status`, reusando `controlled_document_service.approve_document` com
  novo `DocType.management_review`. `snapshot_factory` consolida entradas (status de ações anteriores,
  mudanças, desempenho do SGSI, resultados de auditoria, riscos, NCs/ações) + saídas/decisões.
  Assinatura avançada opcional via `signature_service`; PDF via `management_review_export_service`
  (reusa o padrão `soa_export_service`/reportlab). **Gate duro**: aprovar exige entradas/saídas
  obrigatórias preenchidas.
- **Rationale**: reuniões são eventos distintos no tempo (clarify Q2=A) — coleção, não singleton.
  Reuso total do ciclo de Documento Controlado; zero dependência nova.
- **Alternativas rejeitadas**: singleton por org com versões = reuniões (não reflete a 9.3); coleção
  sem versionamento por ata (perde revisões da mesma ata).

## D3 — Modelo de NC, ação corretiva e verificação

- **Decisão**: `nonconformity` (código `NC-####`, origem, severidade Maior/Menor/Observação, vínculo
  **primário opcional** a `soa_item`/`gap_item`/`risk`/`asset`, `source_finding_id`, causa raiz,
  status) + `corrective_action` (responsável=membro, prazo, status) + `nonconformity_verification`
  (verificador, data, resultado eficaz/ineficaz) + `nonconformity_event` (trilha append-only).
  **Máquina de estados** da NC: `open → in_progress → in_verification → closed` (+ reabrir/cancelar
  conforme política). **Gate de encerramento**: `closed` exige verificação mais recente **eficaz** e
  **zero ações corretivas em estado não terminal** (todas `done`/`cancelled`) — sem campo `obrigatória`.
- **Rationale**: cobre 10.2 (causa raiz + ação verificável). Severidade/vínculo conforme clarify
  Q3/Q4.
- **Prazo vencido**: derivado (`due_date < hoje` e ação não concluída), não material — calculado na
  leitura/serviço.

## D4 — Evidências por extensão da taxonomia da 5a (sem novo esquema)

- **Decisão**: estender `SgsiArtifactType` com `nonconformity` e `corrective_action` e registrar esses
  alvos em `evidence_service._TARGET_MODELS`. Os endpoints `/evidence` (5a) passam a aceitar esses
  alvos automaticamente — **nada** muda no router/modelo de evidência.
- **Rationale**: é literalmente o ponto de extensão que a 5a previu (docstring do enum). Reuso total
  de upload/hash/cifragem/custódia/classificação.

## D5 — Melhorias + visão de ciclo PDCA (read-only)

- **Decisão**: `improvement` (código `IMP-####`, origem auditoria/NC/análise crítica/sugestão,
  `source_ref` opcional, status, vínculo de realimentação **read-only** a `soa_item`/`risk`/contexto)
  + `improvement_event`. `pdca_service` monta a **visão de ciclo** agregando auditorias/NCs/Atas/
  melhorias por artefato, reusando `traceability_service` da 5a — **somente leitura**, **sem
  write-back** (clarify Q5=A).
- **Rationale**: fecha o loop de forma auditável sem acoplar/escrever nos módulos consumidos
  (constituição: "não altera os módulos consumidos").

## D6 — Dashboard + readiness na esteira

- **Decisão**: `nc_metrics_service` produz contagens (NCs por status/severidade, ações com prazo
  vencido, melhorias por status); `GET /nonconformities/dashboard`. `dashboard_service` ganha o card de
  readiness do **Act/PDCA**, **substituindo o placeholder `action_plan`** que a 5a deixou (Módulo 5b);
  o card reflete o fechamento do ciclo (ex.: NCs abertas vs. encerradas, Ata aprovada).
- **Rationale**: a 5a já reservou `DashboardModuleId.action_plan` como placeholder de 5b — agora vira
  card real.

## D7 — Permissões e papéis

- **Decisão**: `view_nonconformity`/`manage_nonconformity` (NC + ações + verificação + promoção +
  melhorias + visão PDCA); `view_management_review`/`manage_management_review`/`approve_management_review`
  (análise crítica). Concessão espelha o padrão dos módulos: super_admin/org_admin/consultant gerenciam;
  aprovação da Ata só super_admin/org_admin; gestor/dono de controle/auditor interno visualizam.
- **Rationale**: separa claramente a aprovação formal da Ata (direção) do tratamento operacional de NCs.

## D8 — Migration

- **Decisão**: `<rev>_nonconformity_pdca_module.py`, `down_revision="b8c9d0e1f016"` (head atual). Cria
  as **7 tabelas** + RLS + triggers append-only (`nonconformity_event`, `improvement_event`),
  idempotente (guardas `_table_exists`). **Não** altera tabelas da 5a (o `internal_audit_finding.
  nonconformity_ref` já existe). Head único após a migration.
- **Rationale**: aditiva; a única interação com a 5a é em runtime (a escrita do ponteiro), não no
  schema.
