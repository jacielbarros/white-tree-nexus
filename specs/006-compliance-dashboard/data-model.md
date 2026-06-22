# Phase 1 — Data Model: Dashboard de Conformidade

> **Não há entidade de domínio nova, nem tabela, nem migration.** Esta feature é uma camada de
> **leitura/agregação**. O que segue são os **DTOs de resposta** (Pydantic, `schemas/dashboard_schema.py`)
> e as **fontes** de cada campo. Todas as leituras são escopadas por `tenant_id` do `OrgContext`.

---

## Enums de apresentação (novos, só no schema — não persistidos)

### `DashboardCardStatus`
| Valor | Significado | Derivação |
|-------|-------------|-----------|
| `not_started` | módulo sem dados/artefato | sem `GapAssessment`/`Soa`/análise de contexto, ou sem itens |
| `draft` | rascunho em andamento | `draft_status = draft` e ainda sem versão vigente |
| `in_review` | enviado para revisão | `draft_status = in_review` |
| `in_force` | aprovado e vigente | `current_version_id` presente e **não** vencido |
| `needs_review` | aprovado, porém análise crítica vencida | `current_version_id` presente e `review_overdue` |
| `error` | falha ao agregar este módulo | exceção capturada na montagem do card (fail-open por card) |

### `DashboardModuleId`
`context` · `gap` · `soa` · `action_plan` (placeholder) · `evidence` (placeholder)

---

## DTOs de resposta

### `DashboardResponse` (raiz)
| Campo | Tipo | Fonte / Regra |
|-------|------|---------------|
| `organization_id` | UUID | `ctx.tenant_id` |
| `organization_name` | str | `Organization.legal_name`/`display_name` (já carregado no contexto) |
| `kpis` | `DashboardKpis` | agregação (ver abaixo) |
| `cards` | `list[ModuleCard]` | um por módulo **que o usuário pode ver** (gating por permissão) |
| `adherence_trend` | `list[AdherencePoint] \| null` | P2 — baselines do Gap; `null` se < 2 |
| `generated_at` | datetime (UTC) | momento da agregação |

### `DashboardKpis`
| Campo | Tipo | Fonte / Regra |
|-------|------|---------------|
| `overall_adherence` | float \| null | `gap_metrics_service.compute_dashboard(...)["overall_adherence"]` (0–1) |
| `controls_evaluated` | int | soma de `status_distribution` exceto `not_filled` |
| `controls_total` | int | nº de itens do assessment se existir; **senão 93** (controles do Anexo A) |
| `critical_gaps` | int | nº de itens com **`priority == critical`** entre os gaps aplicáveis (`partial`/`not_meet` via `list_gaps`); **não** é a contagem de `not_meet` |
| `modules_approved` | int | nº de cards com status `in_force` |
| `modules_total` | int | nº de cards reais (exclui placeholders) |

### `ModuleCard`
| Campo | Tipo | Fonte / Regra |
|-------|------|---------------|
| `id` | `DashboardModuleId` | fixo por módulo |
| `title` | str | rótulo do módulo (PT) |
| `status` | `DashboardCardStatus` | ver enum (D4 da research) |
| `progress_pct` | float \| null | completude/aderência conforme módulo (0–100); `null` quando não aplicável |
| `responsible` | str \| null | responsável do item de **menor `deadline` futuro**; se nenhum item tem prazo futuro, do item de menor prazo; omitido se ausente |
| `deadline` | date \| null | **menor `deadline` futuro** entre os itens/atribuições do módulo (datetime → `date`); omitido se ausente |
| `overdue` | bool | `true` se `deadline` < hoje **ou** `status = needs_review` |
| `next_action` | `NextAction` | heurística (D5) |
| `not_started` | bool | atalho de UI = `status == not_started` |
| `placeholder` | bool | `true` para `action_plan`/`evidence` (módulos futuros) |

### `NextAction`
| Campo | Tipo | Regra |
|-------|------|-------|
| `label` | str | texto da ação (ex.: "Consolidar do Gap") |
| `route` | str | rota de entrada do módulo (ex.: `soa`, `gap-analysis`) |
| `fragment` | str \| null | âncora/seção, só onde a rota já oferece (D5); senão `null` |

### `AdherencePoint` (P2)
| Campo | Tipo | Fonte |
|-------|------|-------|
| `date` | date | `DocumentVersion.emitted_at` da baseline (`DocType.gap_baseline`) |
| `adherence` | float | `content_snapshot["dashboard"]["overall_adherence"]` (0–1) |
| `version` | int | `version_number` da baseline |

---

## Fontes de domínio (somente leitura — entidades existentes)

| Entidade existente | Uso no dashboard | `tenant_id`? |
|--------------------|------------------|--------------|
| `GapAssessment` + `GapAssessmentItem` | status, completude, aderência, lacunas, responsável/prazo de item | sim |
| `gap_metrics_service.compute_dashboard` | KPIs de Gap (reuso de regra) | — (recebe tenant_id) |
| `Soa` + `SoaItem` | status, % itens preenchidos, responsável/prazo | sim |
| `Diagnostic` / análise de contexto (`context_analysis`/`scope`/`stakeholder_map`) | status do Contexto, % aprovado | sim |
| `DocumentVersion` | `current_version_id`, `next_review_at`, `review_overdue`, baselines (trend) | sim |
| `FormAssignment` | responsável/prazo de condução (Gap/diagnóstico) | sim |
| `Organization` | nome da organização | (id = tenant) |

---

## Regras de validação / invariantes

- **Isolamento**: nenhuma query sem `tenant_id` do contexto; `GET /dashboard` para outro tenant ⇒
  404 genérico via `get_org_context`.
- **Gating de card**: card de um módulo só entra em `cards` se o papel tiver a permissão de visão
  (`view_context`/`view_gap`/`view_soa`). Placeholders (`action_plan`/`evidence`) sempre entram.
- **Sem dado inventado**: módulo sem dados ⇒ `status=not_started`, `progress_pct=null`,
  `responsible/deadline` omitidos.
- **Degradação**: exceção ao montar um card ⇒ `status=error` para aquele card; os demais seguem.
- **`adherence_trend`**: presente só com ≥ 2 baselines aprovadas; nunca interpola.

## State transitions

N/A — recurso read-only. O estado exibido é **derivado** ao vivo das transições dos módulos de
origem (documento controlado: draft → in_review → in_force; vencimento por `next_review_at`).
