# Phase 1 — Data Model: Statement of Applicability (SoA)

Todas as tabelas novas carregam `tenant_id` (FK → `organizations.id`) e têm **RLS** no PostgreSQL.
A versão imutável da SoA reusa a tabela compartilhada `document_versions` (não é criada aqui).

## Enums (em `wtnapp/settings.py`)

```python
# Extensão de DocType existente
class DocType(str, Enum):
    ...
    soa = "soa"                       # NOVO

class SoaImplementationStatus(str, Enum):
    implemented = "implemented"       # Implementado
    in_progress = "in_progress"       # Em andamento
    planned = "planned"               # Planejado
    not_started = "not_started"       # Não iniciado
    not_applicable = "not_applicable" # Não aplicável

class SoaInclusionReason(str, Enum):
    risk_treatment = "risk_treatment" # resultado do tratamento de riscos
    legal = "legal"                   # requisito legal/regulatório
    contractual = "contractual"       # requisito contratual
    best_practice = "best_practice"   # melhor prática / requisito de negócio
```

Mapa Gap→SoA (consolidação, D1): `meets→implemented`, `partial→in_progress`, `not_meet→not_started`,
`not_applicable→not_applicable`, `not_filled→None`. Aplicabilidade: `not_applicable⇒False`, senão `True`.

---

## Entidade: `Soa` (tabela `soa`)

Artefato **único por organização** (Documento Controlado). Espelha o padrão de `GapAssessment`.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK `organizations.id`; **único** (1 SoA por org) |
| `gap_assessment_id` | UUID? | FK `gap_assessment.id`; origem da consolidação (nullable) |
| `draft_status` | `DocStatus` | `draft` / `in_review` / `in_force` / `obsolete` (estado do rascunho) |
| `current_version_id` | UUID? | ponteiro para a `DocumentVersion` em vigor (nullable) |
| `created_at` / `updated_at` | datetime(tz) | |

Constraints: `UniqueConstraint(tenant_id)`; índice em `tenant_id`.

---

## Entidade: `SoaItem` (tabela `soa_item`)

Um por controle do Anexo A da organização.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK `organizations.id` |
| `soa_id` | UUID | FK `soa.id` |
| `catalog_item_id` | UUID | FK `gap_catalog_item.id` (controle do Anexo A na cópia da org) |
| `gap_assessment_item_id` | UUID? | FK `gap_assessment_item.id` — rastreabilidade + base da divergência |
| `ref_code` | String(20) | ex.: "A.5.1" (snapshot p/ estabilidade de exibição) |
| `theme` | `GapTheme`? | organizational / people / physical / technological |
| `name` | String(300) | nome do controle (snapshot) |
| `applicable` | Boolean | Aplicável (Sim/Não) |
| `inclusion_reasons` | JSON | array de `SoaInclusionReason`; ≥1 se `applicable` |
| `inclusion_note` | Text? | texto livre complementar da inclusão |
| `exclusion_justification` | Text? | obrigatória se `applicable == False` |
| `implementation_status` | `SoaImplementationStatus`? | nullable (Não avaliado ⇒ vazio) |
| `responsible` | String(200)? | |
| `deadline` | Date? | |
| `risks_treated` | Text? | referências rastreáveis (ex.: "R01, R02") |
| `expected_evidence` | Text? | descrição das evidências objetivas esperadas |
| `evidence_refs` | Text? | referências a documentos/evidências (ex.: "POL-SI-001") |
| `observations` | Text? | |
| `updated_by` | UUID? | |
| `updated_at` | datetime(tz) | |

Constraints: `UniqueConstraint(soa_id, catalog_item_id)`; índices em `tenant_id`, `soa_id`.

**Regras de validação (aplicadas no router/schema):**
- `applicable == True` ⇒ `len(inclusion_reasons) >= 1` (senão 422).
- `applicable == False` ⇒ `exclusion_justification` não vazio (senão 422).
- A **divergência** NÃO é coluna: é derivada comparando os campos consolidados com o
  `gap_assessment_item` vinculado (ver data flow).

---

## Entidade: `SoaItemEvent` (tabela `soa_item_event`) — append-only

Histórico de alterações de item (espelha `gap_assessment_item_event`). Gatilho bloqueia UPDATE/DELETE.

| Campo | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK |
| `tenant_id` | UUID | FK `organizations.id` |
| `item_id` | UUID | FK `soa_item.id` |
| `field` | String(40) | campo alterado |
| `old_value` | String(120)? | |
| `new_value` | String(120)? | |
| `actor_id` | UUID? | |
| `created_at` | datetime(tz) | |

---

## Versão imutável: `document_versions` (reuso, `DocType.soa`)

Criada por `controlled_document_service.approve_document`. O `content_snapshot` (JSON) congela a SoA
inteira para exibição/exportação:

```json
{
  "generated_at": "<iso>",
  "gap_assessment_id": "<uuid|null>",
  "items": [
    {
      "ref_code": "A.5.1", "theme": "organizational", "name": "...",
      "applicable": true,
      "inclusion_reasons": ["risk_treatment", "legal"], "inclusion_note": "...",
      "exclusion_justification": null,
      "implementation_status": "in_progress",
      "responsible": "...", "deadline": "2026-09-30",
      "risks_treated": "R01, R02", "expected_evidence": "...",
      "evidence_refs": "POL-SI-001", "observations": "..."
    }
  ],
  "summary": { "total": 93, "applicable": 90, "not_applicable": 3,
               "by_implementation_status": { "implemented": 40, "in_progress": 30, "...": 0 } }
}
```

`identifier` = `SGSI-DOC-SOA`; `version_number` incremental por (tenant, doc_type, document_id);
`classification`, `next_review_at`, `change_nature`, cadeia elaborado/revisado/aprovado preenchidos
pelo serviço. Assinatura opcional (Motor 003) referencia esta versão.

---

## Relacionamentos

```
Organization (tenant) 1───* Soa (único por tenant)
Soa 1───* SoaItem
SoaItem *───1 gap_catalog_item        (controle do Anexo A)
SoaItem *───0..1 gap_assessment_item  (origem/divergência)
SoaItem 1───* SoaItemEvent            (append-only)
Soa 1───* DocumentVersion             (DocType.soa; append-only; current_version_id aponta a vigente)
DocumentVersion 0..1───* FormSignature (assinatura opcional reusando Motor 003)
gap_assessment_item.soa_ref ───▶ SoaItem.ref_code  (rastreabilidade reversa já existente)
```

## Data flow — consolidação e divergência

1. **Consolidar** (`POST /soa/consolidate`): cria a `Soa` se não existir; para cada
   `gap_assessment_item` com `gap_catalog_item.dimension == annex_a` (não descontinuado), cria o
   `SoaItem` se ausente (pré-preenchido via mapeamento D1) ou **preserva** o existente.
2. **Ler** (`GET /soa`): para cada `SoaItem` com `gap_assessment_item_id`, compara campos consolidados
   com o valor vivo do Gap (status via mapa) → bloco `divergence[]`.
3. **Reconciliar** (`POST /soa/items/{id}/reconcile`): aplica o valor vivo do Gap ao(s) campo(s)
   escolhido(s); grava `SoaItemEvent`; ação explícita.

## Transições de estado (Documento Controlado)

```
draft ──submit-review──▶ in_review ──approve──▶ (DocumentVersion in_force; draft volta a draft)
                                   └─ approve sem review ⇒ 409
                                   └─ approve incompleta ⇒ 422 (lista ref_codes)
                                   └─ approve sem approve_soa ⇒ 403
versão emitida: imutável (gatilho append-only) — UPDATE/DELETE bloqueados
```

## Estratégia de migration (idempotente — conforme diretiva do CLAUDE.md)

`alembic/versions/<rev>_soa_module.py` (`down_revision = "e7f8a9b0c106"`): cria `soa`, `soa_item`,
`soa_item_event` com guard `_table_exists`; RLS + policies (`DROP POLICY IF EXISTS` antes de `CREATE`);
gatilho append-only em `soa_item_event` (`CREATE OR REPLACE`/`DROP TRIGGER IF EXISTS` no PG;
`CREATE TRIGGER IF NOT EXISTS` no SQLite). Sem alteração de DDL em `document_versions` (DocType é
`native_enum=False` ⇒ apenas string).
