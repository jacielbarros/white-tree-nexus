# Quickstart — SoA Normativa dirigida pelo Tratamento de Riscos (Feature 013)

Evolução **in-place** do módulo de SoA (005). Pré-requisitos: ambiente do projeto rodando
(backend :8000, frontend :4200, Postgres do Docker — ver memória `local-e2e-postgres`).

## 1. Backend — ordem de implementação

1. **settings.py**: adicionar enums `SoaKind` (`pre_soa`/`normative`) + mapa de rótulos PT-BR e
   `SoaDivergenceSource` (`gap`/`risk`). Reusar `SoaInclusionReason`/`SoaImplementationStatus`/
   `GAP_TO_SOA_STATUS`.
2. **models/soa_model.py**: adicionar coluna `risk_links: Mapped[list] = mapped_column(JSON, default=list)`
   em `SoaItem`. Sem outras mudanças de modelo.
3. **alembic**: `alembic revision -m "soa risk normative"`; `down_revision="c2d3e4f5a116"`; **idempotente**
   (guard de coluna em `soa_item`; backfill `'[]'` onde NULL). Validar `alembic upgrade head` em DB zerado
   e em DB com `create_all()` já aplicado.
4. **services/soa_consolidation_service.py**:
   - `consolidate(db, tenant_id)`: após o passo Gap, passo risco — indexar `risk_treatment_service.soa_feed`
     por `gap_catalog_item_id`; aplicar "1ª-mão" (applicable + add `risk_treatment` + `risk_links`) só a
     itens sem vínculo de risco; coletar `out_of_scope` (feed sem SoaItem). Retornar
     `{added, preserved, risk_applied, out_of_scope: [ref_code|gap_id]}`.
   - `compute_risk_divergence(db, item, feed_index)`: divergências fonte=risk (feed aponta mas não incluso;
     incluso por risco mas feed órfão / `risk_links` difere).
   - `reconcile(db, item, fields, source)`: estender para fonte risco (aplicar/remover do feed vivo);
     preservar razões manuais; remoção da última razão ⇒ item incompleto (não auto-flip).
5. **schemas/soa_schema.py**: `risk_links` + `origin` + `incomplete` em `SoaItemResponse`; `source`/
   `source_value` em `DivergenceField`; `risk_divergent`/`incomplete` em `SoaSummary`; novo `SoaReadiness`
   + `readiness` em `SoaResponse`; `kind` em `SoaVersionResponse`; `source` em `ReconcileRequest`.
6. **routers/soa.py**:
   - `_soa_response`: calcular o `soa_feed` **1×** e passar índice ao builder de item; preencher
     `readiness` (`kind` se aprovada agora, `risk_plan_approved`, `pending_for_normative`, notices).
   - `_item_response`: incluir `risk_links`, `origin` (derivado), `incomplete`, e divergência com `source`.
   - `consolidate_soa`: audit já existe; incluir `risk_applied`/`out_of_scope` no audit details.
   - `reconcile_item`: passar `body.source`; registrar eventos por campo (incl. `risk_links`).
   - `approve_soa`: calcular `has_approved_risk_plan = RiskPlan.current_version_id is not None` (tenant);
     gravar no snapshot `soa_kind` + `risk_plan_version_number` + por item `risk_links`/`origin`.
   - `_version_response`: ler `kind` do `content_snapshot`.
7. **services/soa_export_service.py**: cabeçalho com rótulo (`soa_kind`); coluna de riscos a partir de
   `risk_links` (códigos), fallback ao `risks_treated` legado; mostrar razões tipadas + origem.

## 2. Frontend

- `pages/soa/soa.ts`: chips de razão (incl. **Risco**); riscos tratados estruturados (códigos); badge de
  **origem** (risco/manual); indicador de **divergência de risco** + botão **Reconciliar** (source=risk);
  **banner Pré-SoA × SoA normativa** lendo `readiness` (com `pending_for_normative` e notices fora-Anexo-A).
- `pages/soa-versions/soa-versions.ts`: exibir o **rótulo `kind`** por versão (Pré-SoA / SoA normativa).
- Reusar `permissionGuard('view_soa')`, `ApiService`, `getBlob` (export). Sem rotas novas.

## 3. Roteiro E2E (browser, Postgres real)

1. Org com Gap avaliado + **riscos** cujo tratamento seleciona controles (ex.: A.8.7, A.5.15), **sem**
   Plano de Tratamento aprovado ainda.
2. `POST /soa/consolidate` → A.8.7/A.5.15 ficam **Aplicável**, razão **Risco**, `risk_links` com `RSK-####`.
3. Adicionar razão manual `legal` a A.5.1; marcar um controle N/A com justificativa → validações OK.
4. Consolidar **de novo** → idempotente (sem duplicar, sem perder a razão `legal`).
5. Mudar um risco para deixar de tratar A.8.7 → A.8.7 vira **divergente (risco órfão)**; **Reconciliar**
   remove `risk_treatment`/`risk_links`; se era a única razão → item fica **incompleto** (banner/realce).
6. Enviar para revisão → **Aprovar** sem Plano aprovado → versão **"Pré-SoA"**; banner avisa o que falta.
7. Aprovar o **Plano de Tratamento de Riscos** (módulo 012) → reconsolidar/abrir SoA → `readiness.kind=normative`.
8. Nova versão da SoA → rótulo **"SoA normativa (6.1.3 d)"**; **Exportar PDF** → razões/risco/origem/rótulo
   no documento.

## 4. Testes (pytest + Vitest)

- `test_soa_risk_consolidation.py`: risco "1ª-mão" aplica; idempotência; preserva razões manuais;
  notice fora-Anexo-A; risco torna aplicável item que era N/A pelo Gap (1ª-mão).
- `test_soa_risk_divergence.py`: ambos os tipos de divergência de risco; reconciliar add/remove;
  remover última razão ⇒ incompleto (não auto-flip); razões manuais preservadas.
- `test_soa_gate_normative.py`: sem plano ⇒ `pre_soa`; com `RiskPlan.current_version_id` ⇒ `normative`;
  rótulo congelado/imutável na versão; completude ainda bloqueia aprovação.
- `test_soa_export.py` (estender): snapshot/PDF contêm `soa_kind`, `risk_links`, razões, origem.
- `test_tenant_isolation_soa.py` (estender): consolidar no contexto de B **não** agrega `soa_feed` de A;
  nenhum `risk_link` cruza tenant; cross-tenant em item/versão ⇒ 404 + audit.

## Validação rápida

```bash
pytest wtnapp/test/test_soa_risk_consolidation.py wtnapp/test/test_soa_risk_divergence.py \
       wtnapp/test/test_soa_gate_normative.py wtnapp/test/test_tenant_isolation_soa.py -q
cd wtnadmin && npm test
alembic upgrade head   # idempotente: rodar 2× sem erro (DB zerado e com create_all)
```
