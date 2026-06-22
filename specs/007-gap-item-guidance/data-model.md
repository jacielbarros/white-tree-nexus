# Phase 1 — Data Model: Orientação de Avaliação por Item

Conteúdo de **plataforma** (sem `tenant_id`), igual ao catálogo-base do Gap. Migration **`<rev>`**
com `down_revision="f8a9b0c1d207"` (head atual = SoA). Idempotente (guardas de coluna/tabela +
triggers `IF NOT EXISTS`/`OR REPLACE`).

---

## 1. `gap_seed_item` — colunas novas (EDITADO)

Item do catálogo-base compartilhado. Já tem: `id`, `seed_version_id`, `dimension`, `ref_code`,
`name`, `theme`, **`objective`** (Text, já autorado), `order`.

| Coluna nova | Tipo | Regra |
|-------------|------|-------|
| `referencia` | String(120), default "" | rótulo factual (ex.: "ISO/IEC 27001:2022 — A.8.24") |
| `como_avaliar` | JSON (lista de strings), default `[]` | perguntas práticas |
| `evidencias_esperadas` | JSON (lista de strings), default `[]` | exemplos de comprovação |
| `nota` | Text, nullable | observação opcional |

> `objetivo` reaproveita o `objective` existente. Em DB zerado, `create_all()` cria as colunas; em DB
> existente, a migration faz `add_column` guardado por checagem de coluna.

## 2. `gap_legend_entry` — NOVO (plataforma)

Definições das escalas, editáveis pelo Super Admin.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `kind` | String(10) | `status` \| `priority` |
| `code` | String(20) | `meets`/`partial`/`not_meet`/`not_applicable`/`not_filled` ou `critical`/`high`/`medium`/`low` |
| `label` | String(60) | rótulo curto (ex.: "Atende Totalmente") |
| `definition` | Text | definição objetiva (PT-BR original) |
| `order` | Integer | ordem de exibição |

Restrição: único por (`kind`, `code`). **Sem `tenant_id`**. Seed inicial idempotente (por `kind`+`code`).

## 3. `gap_guidance_event` — NOVO (plataforma, append-only)

Trilha imutável de edições de orientação e de legenda.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | |
| `target_type` | String(20) | `seed_item` \| `legend` |
| `target_id` | UUID | id do `gap_seed_item` ou `gap_legend_entry` |
| `field` | String(40) | campo alterado (`referencia`/`objetivo`/`como_avaliar`/`evidencias_esperadas`/`nota`/`label`/`definition`) |
| `old_value` | Text, nullable | valor anterior (serializado p/ listas) |
| `new_value` | Text, nullable | valor novo |
| `actor_id` | UUID, nullable | Super Admin que editou |
| `created_at` | datetime(tz) | |

**Sem `tenant_id`.** Append-only: triggers bloqueiam UPDATE/DELETE (SQLite `CREATE TRIGGER IF NOT
EXISTS`; PG função + trigger idempotentes). Índice por (`target_type`, `target_id`).

---

## 4. DTOs de resposta (leitura `GET /gap/guidance`)

### `ItemGuidance`
| Campo | Tipo | Fonte |
|-------|------|-------|
| `seed_item_id` | UUID | `gap_seed_item.id` |
| `ref_code` | str | `gap_seed_item.ref_code` |
| `referencia` | str | novo |
| `objetivo` | str | `gap_seed_item.objective` |
| `como_avaliar` | list[str] | novo |
| `evidencias_esperadas` | list[str] | novo |
| `nota` | str \| null | novo |

### `LegendEntry`
`code` · `label` · `definition` · `order`

### `GuidanceResponse`
`items: list[ItemGuidance]` · `legend: { status: list[LegendEntry], priority: list[LegendEntry] }`

> A matriz resolve a orientação de cada linha por `ref_code` (ou `gap_catalog_item.seed_item_id`).
> Itens `is_custom` (sem `seed_item_id`) ⇒ sem orientação ("sem orientação disponível").

---

## 5. Edição (entrada)

### `ItemGuidanceUpdate` (PUT items/{seed_item_id}) — Super Admin
`referencia?` · `objetivo?` · `como_avaliar?` (list[str]) · `evidencias_esperadas?` (list[str]) ·
`nota?`. Campos ausentes não mudam; cada campo alterado gera 1 `gap_guidance_event` + audit.

### `LegendEntryUpdate` (PUT legend/{entry_id}) — Super Admin
`label?` · `definition?`.

---

## Regras de validação / invariantes

- **Plataforma, não tenant**: nenhuma das 3 estruturas tem `tenant_id`; leitura não expõe dado de
  avaliação de org; edição não tem contexto de org.
- **Seed não sobrescreve**: `load_seed` preenche `referencia/como_avaliar/evidencias_esperadas/nota`
  **só quando vazios**; nunca apaga edição do admin (idempotente).
- **Append-only**: `gap_guidance_event` nunca é alterada/apagada (trigger).
- **IP**: textos do seed são originais; proibido reproduzir norma (validado na revisão de conteúdo).
- **Cobertura**: 100 itens (93 Anexo A + 7 cláusulas) com `referencia`/`objetivo` no mínimo;
  `como_avaliar`/`evidencias_esperadas` podem ser vazios em alguns, mas a meta é cobrir todos.

## State transitions

N/A para o valor da orientação (mutável in-place). O histórico é a sequência append-only de
`gap_guidance_event` (cada edição = novo registro antes→depois).
