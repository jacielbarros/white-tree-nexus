# Data Model — Gestão de Ativos / Processos / Escopo (Feature 011)

Todas as tabelas são **tenant-scoped** (`tenant_id` FK → `organizations.id`, RLS no PostgreSQL com a
policy `tenant_isolation`). Tipos UUID, `DateTime(timezone=True)`. Enums com `SAEnum(..., native_enum=
False)` (string em coluna), declarados em `settings.py`.

---

## Enums (em `settings.py`)

```text
AssetType            = information_asset | system | database | business_process | infrastructure
                       | service | supplier | document | person_team | physical_environment | other
CiaLevel             = baixa | media | alta | critica          # ordenado p/ max(): baixa<media<alta<critica
AssetScopeStatus     = in_scope | out_of_scope | under_analysis
AssetRecordStatus    = active | in_review | archived
AssetRelationshipType= depends_on | supports | uses | stores | processes | responsible_for
                       | operated_by | regulated_by | linked_to | replaces | other
AssetReviewStatus    = up_to_date | due_soon | overdue | undefined   # DERIVADO (não é coluna)
```

Config adicional em `settings.py`:

```text
ASSET_CODE_PREFIXES = {information_asset:"ATV", system:"SIS", database:"BD", business_process:"PROC",
                       infrastructure:"INFRA", service:"SVC", supplier:"FORN", document:"DOC",
                       person_team:"PESS", physical_environment:"AMB", other:"OUTRO"}
ASSET_REVIEW_DUE_SOON_DAYS = int(os.getenv("ASSET_REVIEW_DUE_SOON_DAYS", "30"))
```

---

## 1. `asset_items` — Item de Ativo/Processo/Escopo (entidade central)

| Campo | Tipo | Nulo | Notas |
|-------|------|------|-------|
| id | UUID PK | não | |
| tenant_id | UUID FK organizations | não | índice; RLS |
| code | String(20) | não | auto, imutável; `UniqueConstraint(tenant_id, code)` |
| item_type | AssetType | não | índice |
| name | String(300) | não | |
| description | Text | sim | |
| business_unit | String(160) | sim | unidade/área relacionada |
| responsible_user_id | UUID FK users | sim | Responsável (membro da org) |
| owner_user_id | UUID FK users | sim | Dono do ativo/processo |
| custodian_user_id | UUID FK users | sim | Custodiante |
| record_status | AssetRecordStatus | não | default `active` |
| scope_status | AssetScopeStatus | não | índice |
| scope_justification | Text | sim | obrigatória se `out_of_scope` |
| location | String(255) | sim | localização/ambiente |
| related_system_id | UUID FK asset_items | sim | conveniência (mesmo tenant) |
| related_process_id | UUID FK asset_items | sim | conveniência (mesmo tenant) |
| related_supplier_id | UUID FK asset_items | sim | conveniência (mesmo tenant) |
| has_personal_data | Boolean | não | default false |
| has_sensitive_data | Boolean | não | default false |
| compliance_notes | Text | sim | observações LGPD/compliance (sem PII bruta) |
| confidentiality | CiaLevel | sim | obrigatório se `in_scope` |
| integrity | CiaLevel | sim | obrigatório se `in_scope` |
| availability | CiaLevel | sim | obrigatório se `in_scope` |
| criticality | CiaLevel | sim | calculada (max C/I/A) ou ajustada |
| criticality_is_manual | Boolean | não | default false; true após override |
| last_review_at | DateTime(tz) | sim | data da última revisão |
| next_review_at | DateTime(tz) | sim | próxima revisão (base do `review_status`) |
| context_origin_type | String(40) | sim | US5: ex. `stakeholder`/`context_issue`/`scope` |
| context_origin_id | UUID | sim | US5: id do elemento de contexto de origem |
| archived_at | DateTime(tz) | sim | preenchido no arquivamento lógico |
| archived_by | UUID | sim | |
| archive_reason | String(500) | sim | obrigatório no arquivamento |
| created_by | UUID FK users | não | |
| updated_by | UUID FK users | sim | autor da última atualização |
| created_at | DateTime(tz) | não | |
| updated_at | DateTime(tz) | não | onupdate |

Índices: `tenant_id`, `item_type`, `scope_status`, `responsible_user_id`, `next_review_at`.

**Campos derivados na resposta (não persistidos)**:
- `review_status` (AssetReviewStatus): `undefined` se `next_review_at` nulo; `overdue` se `< now`;
  `due_soon` se `now ≤ next_review_at ≤ now + ASSET_REVIEW_DUE_SOON_DAYS`; senão `up_to_date`.
- `criticality_computed` (CiaLevel|null): `max(C,I,A)` quando os três existem.
- `criticality_divergent` (bool): `criticality_is_manual and criticality != criticality_computed`.
- `pending_fields` (lista): para `under_analysis`/`in_scope` incompleto — responsável e/ou CIA ausentes.
- `cia_complete` (bool): C, I e A preenchidos.

## 2. `asset_relationships` — Relacionamento direcional entre itens

| Campo | Tipo | Nulo | Notas |
|-------|------|------|-------|
| id | UUID PK | não | |
| tenant_id | UUID FK organizations | não | índice; RLS |
| source_item_id | UUID FK asset_items | não | índice |
| relationship_type | AssetRelationshipType | não | |
| target_item_id | UUID FK asset_items | não | índice |
| description | Text | sim | |
| created_by | UUID FK users | não | |
| created_at | DateTime(tz) | não | |

Constraints: `UniqueConstraint(tenant_id, source_item_id, relationship_type, target_item_id)`;
regra de app `source_item_id != target_item_id`; ambos os itens do mesmo tenant (app + RLS).

## 3. `asset_gap_links` — Vínculo item ↔ gap (catálogo da org)

| Campo | Tipo | Nulo | Notas |
|-------|------|------|-------|
| id | UUID PK | não | |
| tenant_id | UUID FK organizations | não | índice; RLS |
| item_id | UUID FK asset_items | não | índice |
| gap_catalog_item_id | UUID FK gap_catalog_item | não | índice |
| note | Text | sim | |
| created_by | UUID FK users | não | |
| created_at | DateTime(tz) | não | |

Constraint: `UniqueConstraint(tenant_id, item_id, gap_catalog_item_id)`. Sem cascade delete do gap.

## 4. `asset_item_events` — Histórico append-only do item

| Campo | Tipo | Nulo | Notas |
|-------|------|------|-------|
| id | UUID PK | não | |
| tenant_id | UUID FK organizations | não | índice; RLS |
| item_id | UUID FK asset_items | não | índice |
| event_type | String(40) | não | CREATE, UPDATE, SCOPE_CHANGE, SCOPE_EXCLUSION, CRITICALITY_CHANGE, RESPONSIBLE_CHANGE, ARCHIVE, RELATIONSHIP_ADD, RELATIONSHIP_REMOVE, GAP_LINK, GAP_UNLINK |
| field_name | String(60) | sim | campo alterado |
| old_value | Text | sim | valor anterior |
| new_value | Text | sim | novo valor |
| reason | String(500) | sim | justificativa (obrigatória em SCOPE_EXCLUSION/CRITICALITY_CHANGE/ARCHIVE) |
| actor_id | UUID | sim | usuário responsável |
| occurred_at | DateTime(tz) | não | |
| details | JSON | sim | metadados auxiliares |

**Append-only**: triggers `BEFORE UPDATE OR DELETE` (PG function + trigger; SQLite `RAISE(ABORT)`),
idênticos ao padrão `gap_evidence_event`.

---

## Regras de validação (aplicadas no `asset_service`)

- **Obrigatórios sempre** (FR-032): `name`, `item_type`, `scope_status`.
- **`in_scope`** (FR-010): `responsible_user_id` **e** `confidentiality`/`integrity`/`availability`.
- **`out_of_scope`** (FR-009): `scope_justification` não-vazia.
- **`under_analysis`** (FR-011): sem bloqueio; `pending_fields` na resposta.
- **Duplicidade** (FR-033): bloquear `name` repetido dentro do mesmo `item_type` no tenant, salvo
  flag explícita `allow_duplicate=true` (com `reason`) no payload.
- **Arquivamento** (FR-024): `record_status → archived` exige `archive_reason`; nunca exclusão física.
- **Responsáveis**: `responsible_user_id`/`owner_user_id`/`custodian_user_id` devem ser membros ativos
  do tenant (validado contra `memberships`).
- **Relacionamento**: `source != target`; ambos no tenant; tipo válido; sem duplicata.
- **Gap link**: `gap_catalog_item_id` deve pertencer ao catálogo do tenant.

## Transições de estado

- **`record_status`**: `active ⇄ in_review` (livre); `* → archived` (exige justificativa;
  reversível p/ `active` conforme política — também registrada no histórico).
- **`scope_status`**: livre entre `in_scope`/`out_of_scope`/`under_analysis`; cada transição gera
  evento `SCOPE_CHANGE` (ou `SCOPE_EXCLUSION` quando passa a `out_of_scope`, exigindo justificativa).
- **`criticality`**: recalculada quando C/I/A mudam e `criticality_is_manual=false`; override seta
  `is_manual=true` e gera `CRITICALITY_CHANGE` (com justificativa).

## Relacionamento com Organization e módulos existentes

- Todas as 4 tabelas → `organizations.id` via `tenant_id`.
- `asset_gap_links.gap_catalog_item_id` → `gap_catalog_item.id` (somente leitura do Gap; sem alterar
  o módulo Gap).
- `responsible/owner/custodian/created_by/updated_by` → `users.id` (membros do tenant).
- `context_origin_*` referenciam (logicamente) elementos de Contexto (002) para a ação "criar a partir
  do contexto" — sem FK rígida (referência fraca, fonte de origem informativa).
