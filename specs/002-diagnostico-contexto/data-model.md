# Phase 1 — Data Model: Diagnóstico e Contexto da Organização

**Feature**: `002-diagnostico-contexto` · **Date**: 2026-06-19

Convenções herdadas da fundação: PK UUID v4; timestamps UTC (`timezone=True`); **toda** tabela tem
`tenant_id` (FK → `organizations.id`) e fica sob RLS; SAEnum `native_enum=False`; Alembic +
`create_all()`. Unicidade "um conjunto por organização" via constraint sobre `tenant_id` (R3).

---

## Entidades

### Diagnostic (`diagnostics`) — insumo de trabalho (não versionado)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `tenant_id` | UUID FK→organizations | **único** (1 por organização) |
| `status` | enum `DiagnosticStatus` | `draft` \| `completed` |
| `sections` | JSONB | seções: identificacao, estrutura, negocio, tecnologia, dados, cadeia_suprimento, requisitos |
| `updated_by` / `created_at` / `updated_at` | — | auto-save de rascunho |

### ContextAnalysis (`context_analyses`) — documento controlado (4.1)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `tenant_id` | UUID FK | **único** |
| `intended_outcomes` | text | resultados pretendidos do SGSI |
| `methodology` | text null | metodologia/fontes |
| `draft_status` | enum `DocStatus` | estado do rascunho corrente (`draft`/`in_review`) |
| `current_version_id` | UUID FK→document_versions null | versão **em vigor** |

**Child — ContextIssue (`context_issues`)** (tenant_id):
`origin` (enum `IssueOrigin`: internal/external), `framework` (enum: pestel/swot), `category`
(dimensão PESTEL ou quadrante SWOT), `description`, `impact` (enum `ImpactLevel`: alto/medio/baixo).

### StakeholderMap (`stakeholder_maps`) — documento controlado (4.2)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id`/`tenant_id` (único) · `draft_status` · `current_version_id` | — | igual ao padrão |

**Child — Stakeholder (`stakeholders`)** (tenant_id): `name`, `type` (internal/external),
`power` (enum `Level`: alto/medio/baixo), `interest` (enum `Level`), `strategy` (enum
`EngagementStrategy`, **derivado**: manage_closely/keep_satisfied/keep_informed/monitor).

**Child — StakeholderRequirement (`stakeholder_requirements`)** (tenant_id, FK→stakeholders):
`type` (enum: legal/regulatory/contractual/expectation), `description`, `how_addressed` (text).

### ScopeStatement (`scope_statements`) — documento controlado (4.3)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id`/`tenant_id` (único) · `draft_status` · `current_version_id` | — | padrão |
| `interfaces_dependencies` | text | entrada 4.3(c) |
| `context_version_ref` | UUID FK→document_versions null | versão da Análise de Contexto que fundamentou |
| `stakeholder_version_ref` | UUID FK→document_versions null | versão do Mapa que fundamentou |

**Child — ScopeItem (`scope_items`)** (tenant_id): `kind` (enum: inclusion/exclusion),
`description`, `justification`.

### DocumentVersion (`document_versions`) — append-only (realiza "Documento Controlado SGSI 7.5")

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `tenant_id` | UUID FK | escopo |
| `document_type` | enum `DocType` | context_analysis \| stakeholder_map \| scope_statement |
| `document_id` | UUID | id do artefato dono |
| `identifier` | str | ex.: `SGSI-DOC-002` (padrão configurável por org) |
| `version_number` | int | incremental por artefato |
| `status` | enum `DocStatus` | draft \| in_review \| in_force \| obsolete |
| `classification` | enum `Classification` | publico/uso_interno/confidencial/restrito |
| `emitted_at` / `next_review_at` | timestamptz | emissão + próxima análise crítica |
| `elaborated_by` / `reviewed_by` / `approved_by` | UUID null | cadeia de aprovação |
| `change_nature` | text | natureza da alteração |
| `content_snapshot` | JSONB | conteúdo congelado e imutável |
| `created_at` | timestamptz | — |

- **Append-only**: nunca UPDATE/DELETE (reforço por trigger, como em `audit_logs`). Invariante: no
  máximo 1 linha com `status='in_force'` por (`tenant_id`,`document_type`,`document_id`).

### ClassificationAccessPolicy (`classification_access_policies`) — config por org (R4)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id`/`tenant_id` | — | 0..1 por organização |
| `rules` | JSONB | mapeamento nível→papéis permitidos; ausência ⇒ RBAC-apenas (default) |

---

## Enums

```
DiagnosticStatus    = draft | completed
DocStatus           = draft | in_review | in_force | obsolete
DocType             = context_analysis | stakeholder_map | scope_statement
IssueOrigin         = internal | external
IssueFramework      = pestel | swot
ImpactLevel / Level = alto | medio | baixo
EngagementStrategy  = manage_closely | keep_satisfied | keep_informed | monitor   (derivado)
RequirementType     = legal | regulatory | contractual | expectation
ScopeItemKind       = inclusion | exclusion
Classification      = publico | uso_interno | confidencial | restrito
```

### Derivação Poder × Interesse → estratégia (FR-007 / SC-004)

| Poder \ Interesse | alto | medio/baixo |
|---|---|---|
| **alto** | manage_closely | keep_satisfied |
| **medio/baixo** | keep_informed | monitor |

---

## Papéis & Permissões (extensão de `helpers/permissions.py`)

| Permissão | super_admin | org_admin | consultant | manager | process_owner | demais |
|-----------|:---:|:---:|:---:|:---:|:---:|:---:|
| `view_context` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅¹ |
| `manage_context` | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| `approve_context_document` | ✅ | ✅ | — | — | — | — |

¹ `view_context` sujeito à política de classificação da organização, quando configurada (R4).

---

## State Machine — artefato controlado (R2)

```
        criar              enviar p/ revisão        aprovar
rascunho ───▶ (rascunho) ───────────▶ em revisão ───────▶ EM VIGOR
   ▲                                                         │
   │            revisar (cria novo rascunho)                 │ aprovar nova versão
   └─────────────────────────────────────────────────────────┘
                          versão anterior ▶ OBSOLETA
```

- Editar dados relacionais ⇒ atua no **rascunho corrente**. `approve_context_document` aprova ⇒
  snapshot imutável em `document_versions` (status `in_force`), ponteiro `current_version_id`
  atualizado, versão anterior → `obsolete`. Sempre ≤ 1 `in_force` por artefato.
- Aprovar exige o papel autorizado (403 + audit caso contrário).

## Row-Level Security

Todas as tabelas acima são escopadas e recebem a policy padrão da plataforma:
`tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid` (defesa em profundidade), com
o escopo de aplicação via `tenant_scope` como mecanismo primário. `document_versions` ganha também
o gatilho **append-only** (bloqueia UPDATE/DELETE), análogo a `audit_logs`.

## Relacionamentos (resumo)

```
organizations 1──1 diagnostics
organizations 1──1 context_analyses 1──∞ context_issues
organizations 1──1 stakeholder_maps 1──∞ stakeholders 1──∞ stakeholder_requirements
organizations 1──1 scope_statements 1──∞ scope_items
context_analyses/stakeholder_maps/scope_statements 1──∞ document_versions (snapshots)
scope_statements ∞──1 document_versions (context_version_ref, stakeholder_version_ref)
organizations 0..1 classification_access_policies
```
