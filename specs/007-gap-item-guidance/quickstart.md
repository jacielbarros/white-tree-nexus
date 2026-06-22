# Quickstart — Orientação de Avaliação por Item (Feature 007)

Guia de implementação + validação. **Tem migration** (colunas no seed + 2 tabelas de plataforma).

## Pré-requisitos
- Módulo 2 (Gap Analysis 004) implementado. `gap_seed_item` (com `objective`) e `gap_catalog_item`
  (com `seed_item_id`) já existem.
- Ambiente: backend `uvicorn wtnapp.main:app --reload` (:8000) + frontend `npm start` (:4200);
  Postgres do Docker p/ E2E.

## Backend — ordem de implementação
1. **Modelos** — `gap_seed_model.py`: +`referencia`(String 120, default ""), +`como_avaliar`(JSON,
   default list), +`evidencias_esperadas`(JSON, default list), +`nota`(Text, nullable). Novos:
   `gap_legend_model.py` (`GapLegendEntry`) e `gap_guidance_event_model.py` (`GapGuidanceEvent` +
   triggers append-only SQLite/PG). Nenhum com `tenant_id`.
2. **Migration** — `alembic/versions/<rev>_gap_guidance.py`, `down_revision="f8a9b0c1d207"`:
   `add_column` guardado nas 4 colunas; `create_table` guardado p/ `gap_legend_entry` e
   `gap_guidance_event`; triggers idempotentes; **idempotente** (rodar 2× sem erro). Sem RLS (são
   tabelas de plataforma).
3. **Seed** — `data/iso27001_seed.py`: incluir `referencia`/`como_avaliar`/`evidencias_esperadas`/
   `nota` (PT-BR **original**) nos 100 itens + lista de `LEGEND` (status/prioridade). Autoria por tema
   (A.5/A.6/A.7/A.8 + cláusulas).
4. **`gap_seed_service.load_seed`** — preencher os campos de orientação **só quando vazios** (nunca
   sobrescrever) e semear `gap_legend_entry` idempotentemente (por `kind`+`code`). Versão segue 2022.1.
5. **Service** — `gap_guidance_service.py`: `get_guidance(db)` (itens do seed corrente + legenda);
   `update_item_guidance(db, seed_item_id, patch, actor)` e `update_legend(db, entry_id, patch, actor)`
   — comparam antes→depois por campo, gravam `gap_guidance_event` e chamam audit.
6. **Schema** — `gap_guidance_schema.py` (DTOs do data-model).
7. **Router** — `routers/gap_guidance.py`: `GET /gap/guidance` (`require_permission("view_gap")`);
   `PUT /gap/guidance/items/{seed_item_id}`, `PUT /gap/guidance/legend/{entry_id}`,
   `GET /gap/guidance/events` (`require_super_admin`). Registrar em `main.py`.

## Frontend
- `pages/gap-analysis/gap-analysis.ts`: buscar `GET /gap/guidance` no init; no painel lateral, seção
  **"Orientação de avaliação"** (read-only) com referência, objetivo, `como_avaliar` (bullets),
  `evidencias_esperadas` (bullets), nota; mapear por `ref_code`. Deixar espaço p/ futura seção de
  Evidências. Exibir a **legenda** (status/prioridade) na tela (ex.: painel recolhível/ajuda).
- `pages/gap-guidance-admin/`: área (rota guardada p/ **Super Admin**) p/ editar orientação dos itens
  e a legenda; PUTs via `api.put`.
- `app.routes.ts`: rota `gap-guidance-admin` com guard de Super Admin.

## Validação (testes obrigatórios)
### Backend — `test/test_gap_guidance.py`
- **leitura**: `GET /gap/guidance` devolve itens (com orientação do seed) + legenda; item adotado
  resolve orientação via `seed_item_id`.
- **edição admin**: Super Admin edita um campo ⇒ persistido, `gap_guidance_event` registra
  antes→depois, audit gerado; nova leitura reflete o valor.
- **propagação**: edição feita uma vez é vista por leitura de **qualquer** org (conteúdo compartilhado).
- **seed não sobrescreve**: após editar via admin, rodar `load_seed` de novo **não** reverte a edição.
- **legenda**: editar uma entrada reflete na leitura.
- **append-only**: tentativa de UPDATE/DELETE em `gap_guidance_event` falha.

### Backend — `test/test_gap_guidance_rbac.py` (obrigatório)
- não-Super-Admin (incl. Admin de org) em `PUT .../items/{id}` ⇒ **403** + audit.
- a leitura/edição **não** expõe nem altera dado de avaliação de nenhuma organização.

### Frontend — `gap-analysis.spec.ts` + `gap-guidance-admin.spec.ts`
- painel renderiza a orientação (mock de `/gap/guidance`); item sem orientação ⇒ "sem orientação
  disponível"; legenda renderiza; editor admin chama o PUT correto.

## Comandos
```bash
pytest wtnapp/test/test_gap_guidance.py wtnapp/test/test_gap_guidance_rbac.py
cd wtnadmin && npm test
alembic upgrade head   # validar idempotência (rodar 2x) no Postgres real
```

## Definition of Done
- [ ] Orientação (4 campos novos + objetivo) lida na matriz via join do seed; legenda exibida.
- [ ] Edição só por Super Admin; não-plataforma ⇒ 403 + audit; trilha append-only registra antes→depois.
- [ ] `load_seed` idempotente e **não** sobrescreve edições; legenda semeada.
- [ ] 100 itens com orientação PT-BR **original** (sem texto normativo ISO).
- [ ] Migration idempotente (2×) no Postgres; router em `main.py`.
- [ ] Testes: leitura, edição, propagação, seed-não-sobrescreve, append-only, **RBAC/isolamento**.
