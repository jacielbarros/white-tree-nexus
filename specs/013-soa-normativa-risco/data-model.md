# Phase 1 — Data Model: SoA Normativa dirigida pelo Tratamento de Riscos

Evolução **in-place** do modelo de SoA (Feature 005). **Uma única mudança de schema**: coluna
`risk_links` em `soa_item`. Tudo o mais é reuso (`soa`, `soa_item`, `soa_item_event`,
`document_versions`) e enriquecimento do **conteúdo do snapshot** (JSON, sem coluna nova).

## Entidades

### Soa *(existente — inalterada)*
Artefato único por organização (`tenant_id`, índice único por tenant). `gap_assessment_id`,
`draft_status` (DocStatus), `current_version_id` (ponteiro da versão em vigor). **Sem mudança de
coluna.** Liga-se logicamente também ao insumo de risco vivo (não persistido na `soa`).

### SoaItem *(existente — +1 coluna)*
Um por controle do Anexo A (`tenant_id`, `soa_id`, `catalog_item_id` → `gap_catalog_item`,
`gap_assessment_item_id`). Campos existentes mantidos: `ref_code`, `theme`, `name`, `applicable`,
`inclusion_reasons` (JSON `list[SoaInclusionReason]`, já inclui `risk_treatment`), `inclusion_note`,
`exclusion_justification`, `implementation_status`, `responsible`, `deadline`, `risks_treated`
(texto **legado**, preservado), `expected_evidence`, `evidence_refs`, `observations`, `updated_by`,
`updated_at`.

| Campo novo | Tipo | Nullable | Default | Descrição |
|------------|------|----------|---------|-----------|
| `risk_links` | JSON | não | `[]` | Projeção dos riscos tratados vinda do `soa-feed`: `list[{risk_id: str, risk_code: str}]`. Preenchido na consolidação/reconciliação. |

**Regras de validação** (no router, como hoje):
- `applicable=True` ⇒ `inclusion_reasons` não-vazio (≥1 razão tipada: `risk_treatment`|`legal`|
  `contractual`|`best_practice`). Caso contrário item **incompleto** (bloqueia aprovação — FR-009a).
- `applicable=False` ⇒ `exclusion_justification` não-vazia.
- `risk_treatment` em `inclusion_reasons` ⟺ idealmente `risk_links` não-vazio; **divergência** quando
  quebra (item com `risk_treatment` mas feed/`risk_links` órfão; ou feed aponta mas item sem inclusão).

**Origem (derivada, não coluna)**: um controle aplicável tem origem **"risco"** se `risk_treatment`
∈ `inclusion_reasons`; **"manual"** se só razões manuais; ambas podem coexistir.

### SoaItemEvent *(existente — inalterada, append-only)*
Trilha de campo (`field`, `old_value`, `new_value`, `actor_id`). Passa a registrar também eventos de
mudança dirigida por risco (ex.: `field="risk_links"`/`"inclusion_reasons"`, `new_value="reconciled"`).
Gatilho append-only (SQLite + PG) inalterado.

### SoaVersion = DocumentVersion *(existente — conteúdo enriquecido)*
Versão imutável (append-only) via `document_versions`. **Sem coluna nova.** O `content_snapshot` (JSON)
passa a carregar, no nível raiz e por item:

```jsonc
{
  "soa_kind": "normative" | "pre_soa",          // rótulo do gate (imutável na versão)
  "risk_plan_version_number": 3 | null,          // versão vigente do Plano de Tratamento na aprovação
  "summary": { "total": 93, "applicable": 70, "not_applicable": 23 },
  "gap_assessment_id": "…",
  "items": [
    {
      "ref_code": "A.8.7", "theme": "tecnologico", "name": "...",
      "applicable": true,
      "inclusion_reasons": ["risk_treatment", "legal"],
      "inclusion_note": "...", "exclusion_justification": null,
      "implementation_status": "in_progress",
      "responsible": "...", "deadline": "2026-09-30",
      "risk_links": [{"risk_id": "...", "risk_code": "RSK-0003"}],
      "risks_treated": "texto legado (se houver)",
      "origin": "risk" | "manual" | "risk+manual",   // derivado, congelado no snapshot
      "expected_evidence": "...", "evidence_refs": "...", "observations": "...",
      "signature": { ... }    // quando assinada (igual à 005)
    }
  ]
}
```

## Relacionamentos (lógicos)

```
Organization 1───* Soa 1───* SoaItem *───1 GapCatalogItem
                                  │
                                  ├── risk_links (JSON) ──▶ Risk (id/código)   [projeção read-only do soa-feed]
                                  └── gap_assessment_item_id ──▶ GapAssessmentItem [status vivo]

Soa 1───* DocumentVersion (append-only, content_snapshot enriquecido + soa_kind)

soa-feed (read-only, Feature 012): RiskTreatmentControl(gap_catalog_item_id) ──▶ Risk
RiskPlan.current_version_id  ──▶  gate: soa_kind = normative se != None
```

## Enums (settings.py)

Reuso: `SoaImplementationStatus`, `SoaInclusionReason` (já com `risk_treatment`), `GAP_TO_SOA_STATUS`,
`DocStatus`, `DocType.soa`, `Classification`, `GapTheme`.

| Enum novo | Valores | Uso |
|-----------|---------|-----|
| `SoaKind` | `pre_soa`, `normative` | rótulo da versão / readiness na resposta |
| `SoaDivergenceSource` | `gap`, `risk` | fonte de cada divergência |

(`SoaKind` acompanha um mapa de rótulos PT-BR: `pre_soa`→"Pré-SoA (consolidação do Gap)",
`normative`→"SoA normativa (6.1.3 d)".)

## Migração de schema

`wtnapp/alembic/versions/<rev>_soa_risk_normative.py`, `down_revision = "c2d3e4f5a116"` (head atual,
Feature 012). **Idempotente** (padrão obrigatório do projeto):
- `op.add_column("soa_item", risk_links JSON nullable default '[]')` **guardado** por checagem de coluna
  (`"risk_links" not in [c["name"] for c in sa.inspect(conn).get_columns("soa_item")]`), pois o
  `create_all()` do startup já cria a coluna em DB zerado mas não em tabela preexistente.
- Backfill idempotente: `UPDATE soa_item SET risk_links='[]' WHERE risk_links IS NULL`.
- Sem RLS/trigger novos (a coluna entra numa tabela que já tem RLS + trigger append-only de evento).

## Transição não destrutiva (orgs com Pré-SoA existente)

- Itens existentes ganham `risk_links=[]` (default) — nenhuma razão manual/justificativa é tocada.
- Primeira consolidação dirigida por risco aplica `risk_treatment`/`risk_links` **só** a itens "1ª-mão"
  (R6); demais permanecem; drift vira divergência reconciliável.
- `risks_treated` (texto legado) intacto; passa a coexistir como observação/fallback no PDF.
