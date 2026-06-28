# Quickstart — Módulo de Gestão de Riscos (Feature 012)

Guia rápido para desenvolver, testar e validar o módulo. Pré-requisitos: ambiente da White Tree Nexus
já configurado (ver `CLAUDE.md`), Postgres do Docker para E2E (ver memória `local-e2e-postgres`),
e os módulos **Ativos (011)**, **Gap (004/007)** e **SoA (005)** presentes (fornecem ativos, catálogo de
controles A.5–A.8 e os campos forward-compatible da SoA).

## 1. Backend — ordem de implementação sugerida

1. **`settings.py`**: enums novos (`ThreatCategory`, `ThreatOrigin`, `VulnerabilityCategory`,
   `RiskStatus`, `RiskTreatmentOption`, `RiskEventType`), `DocType.risk_treatment_plan`,
   `RISK_CODE_PREFIX="RSK"`, e `DEFAULT_RISK_METHODOLOGY` (5x5 + critério ≤ Médio + `cia_impact_map`).
2. **Modelos** (`models/risk_methodology_model.py`, `risk_catalog_model.py`, `risk_model.py`) + registrar
   em `models/__init__.py`. Triggers append-only em `risk_events` (SQLite+PG), padrão `asset_item_events`.
3. **Seed** `data/iso27005_seed.py` (PT-BR original) + `risk_catalog_service.load_seed()` chamado no
   startup (idempotente), como o Gap.
4. **Serviços**: `risk_methodology_service` (get-or-default, validação, `compute_level`, recálculo em
   massa), `risk_service` (código, derivação de impacto/override, transições, diffing/eventos),
   `risk_catalog_service` (adopt + vínculos), `risk_treatment_service` (opção/controles/residual/
   aceitação/plano/SoA-feed), `risk_metrics_service` (heat map/dashboard).
5. **Schemas** Pydantic (`schemas/risk_schema.py`).
6. **Router** `routers/risk.py` (`/risk`, prefixo) com `require_permission` + `scoped_query` +
   `AuditService`; registrar em `main.py`.
7. **RBAC**: `helpers/permissions.py` — `view_risk`/`manage_risk`/`approve_risk_plan` (ver matriz abaixo).
8. **Dashboard**: `dashboard_schema.py` (`DashboardModuleId.risk`) + `dashboard_service._risk_card`.
9. **Migration** `alembic/versions/c2d3e4f5a116_risk_management_module.py`
   (`down_revision="b1c2d3e4f015"`, idempotente: `_table_exists`, RLS com `DROP POLICY IF EXISTS`,
   triggers com `CREATE OR REPLACE`/`IF NOT EXISTS`).

### Matriz RBAC (a aplicar em `PERMISSIONS`)
| Papel | view_risk | manage_risk | approve_risk_plan |
|------|:---:|:---:|:---:|
| Super Admin | ✓ | ✓ | ✓ |
| Admin da organização | ✓ | ✓ | ✓ |
| Consultor | ✓ | ✓ | — |
| Gestor / Dono de processo / Dono de controle / Auditor interno / Cliente | ✓ | — | — |
| Colaborador convidado | — | — | — |

> Edição do **catálogo-semente** (ameaças/vulnerabilidades de plataforma) = `require_super_admin`
> (sem contexto de org), igual à orientação do Gap (Feature 007).

## 2. Fluxo do usuário (as três fases da esteira)

1. **Metodologia** (opcional, gate suave): `GET/PUT /risk/methodology`. Sem configurar ⇒ default 5x5.
2. **Fase 1 — Catálogo**: `POST /risk/threats/adopt` + `/risk/vulnerabilities/adopt`; criar custom;
   arquivar; vincular a ativos (`POST /risk/threats/{id}/assets`). Os vínculos aparecem no detalhe do ativo.
3. **Fase 2 — Avaliação**: `POST /risk/risks` (cenário: ameaça+vuln+0..n ativos) → `PUT /risk/risks/{id}`
   (prob + impacto[derivado da CIA/override] + dono) → nível + acima/abaixo do critério calculados;
   `GET /risk/risks` (filtros/busca) e `GET /risk/matrix` (heat map 5x5). O dashboard completo do
   módulo é `GET /risk/dashboard` (Fase/US5).
4. **Fase 3 — Tratamento**: `PUT /risk/risks/{id}/treatment` (opção + residual) →
   `POST /risk/risks/{id}/controls` (gap da org ou custom; resp.+prazo se mitigar) →
   `POST /risk/risks/{id}/accept` (se aceitar) → `POST /risk/plan/submit-review` →
   `POST /risk/plan/approve` (gate duro: riscos avaliados; assinatura opcional).
5. **SoA-feed**: `GET /risk/soa-feed` expõe controle←riscos (read-only). **Não** escreve na SoA.

## 3. Testes (test-first, pytest + SQLite in-memory)

```bash
pytest wtnapp/test/test_risk_methodology.py     # default 5x5, edição, compute_level, recálculo em massa
pytest wtnapp/test/test_risk_catalog.py         # adoção idempotente, custom, arquivar, vínculos
pytest wtnapp/test/test_risk_assessment.py      # cenário, código RSK, impacto da CIA/override, nível, critério, filtros, heat map
pytest wtnapp/test/test_risk_treatment.py       # opção, controles (mitigar exige ≥1 c/ resp+prazo), residual, aceitação, SoA-feed
pytest wtnapp/test/test_risk_plan.py            # consolidação, gate duro, aprovação + versão imutável, assinatura opcional
pytest wtnapp/test/test_risk_history.py         # append-only + justificativa
pytest wtnapp/test/test_risk_metrics.py         # heat map + distribuições + inerente×residual
pytest wtnapp/test/test_risk_dashboard_card.py  # card de readiness na esteira (Feature 006)
pytest wtnapp/test/test_tenant_isolation_risk.py  # OBRIGATÓRIO
```

Casos de borda obrigatórios: metodologia ausente → default; cenário sem ativos → impacto manual; CIA
incompleta → manual; override sem justificativa → 422; mitigar sem controle → 422; aceitar sem
justificativa/dono → 422; aprovar plano com risco não avaliado → 409; referência cross-tenant (ativo/
ameaça/vuln/gap de outro tenant) → 404 genérico; UPDATE/DELETE em `risk_events` → bloqueado; re-adoção
idempotente (sem duplicar).

## 4. Frontend (`wtnadmin/`)

- `core/permissions.ts`: `view_risk`/`manage_risk`/`approve_risk_plan`. `core/models.ts`: tipos.
- Páginas lazy (`permissionGuard('view_risk')`): `risk-methodology`, `risk-catalog`, `risks`,
  `risk-detail`, `risk-treatment-plan`, `risk-dashboard`.
- `pages/asset-detail`: ligar os placeholders ("Ameaças/Vulnerabilidades/Riscos vinculados",
  "Controles relacionados") a `GET /risk/assets/{id}/links` (sem alterar o modelo de Ativos).
- Shell: links das três fases do módulo (Ameaças/Vulnerabilidades · Avaliação · Tratamento).

```bash
cd wtnadmin && npm test   # Vitest — inclui as specs das novas páginas
```

## 5. Migration no Postgres real (E2E)

```bash
alembic upgrade head        # aplica c2d3e4f5a116 (idempotente mesmo com create_all do startup)
alembic downgrade -1        # valida o downgrade
```

Validar no browser (login + Postgres real): configurar metodologia, adotar catálogos, criar e avaliar
um risco (impacto derivado da CIA), tratar (mitigar com controle do Gap da org), aceitar um risco,
aprovar o plano (com e sem assinatura), conferir heat map/dashboard, o SoA-feed e os placeholders do
ativo preenchidos. Seed de cenário sugerido: `scripts/seed_risk_demo.py` (a criar, no padrão de
`scripts/seed_soa_demo.py`).

## 6. Definition of Done (lembrete da constitution)

Isolamento de tenant testado · audit nos pontos sensíveis · sem PII em logs/erros · router em `main.py` ·
migration idempotente · histórico/plano append-only · **não** escrever na SoA · **não** alterar o modelo
de Ativos · spec atualizada se houver divergência técnica.
