# Quickstart — Dashboard de Conformidade (Feature 006)

Guia rápido para implementar e validar o dashboard. **Sem migration** (read-only).

## Pré-requisitos

- Fundação multi-tenant (001), Contexto (002), Workflow (003), Gap Analysis (004) e SoA (005)
  implementados (já estão).
- Ambiente: backend `uvicorn wtnapp.main:app --reload` (:8000) + frontend `npm start` (:4200).
- Seed de cenário: reusar `scripts/seed_soa_demo.py` (gera org com Contexto/Gap/SoA em estados
  variados) — bom para ver os cards populados.

## Backend — ordem de implementação

1. **Permissão** — `helpers/permissions.py`: adicionar `"view_dashboard"` a todos os papéis
   **exceto** `guest_collaborator`.
2. **Schema** — `schemas/dashboard_schema.py`: `DashboardResponse`, `DashboardKpis`, `ModuleCard`,
   `NextAction`, `AdherencePoint`, enums `DashboardCardStatus`/`DashboardModuleId`
   (Pydantic v2; `model_dump(mode="json")`).
3. **Service** — `services/dashboard_service.py`: `build_dashboard(db, ctx) -> DashboardResponse`.
   - Reusa `gap_metrics_service.compute_dashboard` e `list_gaps`.
   - Lê `Soa`/`SoaItem`, artefatos de contexto (helpers de `context_analysis`/`scope`/`stakeholders`),
     `DocumentVersion` (`cds.review_overdue`, baselines), `FormAssignment`.
   - Monta cada card em try/except (fail-open por card ⇒ `status="error"`).
   - Gating: inclui o card só se `has_permission(ctx.role, "view_<modulo>")`.
4. **Router** — `routers/dashboard.py`: `APIRouter(prefix="/dashboard", tags=["dashboard"])`,
   `GET ""` com `Depends(require_permission("view_dashboard"))`, retorna `build_dashboard(db, ctx)`.
   **Sem** `AuditService` no sucesso (decisão SEC-003).
5. **Registrar** — `main.py`: `app.include_router(dashboard.router)`.

## Frontend — ajuste da home

- `pages/dashboard/dashboard.ts`: trocar o `forkJoin` de 3 chamadas por **uma** chamada
  `api.get<DashboardResponse>('/dashboard')`. Tipar pelos DTOs. Renderizar `kpis`, `cards`
  (status/progress/responsible/deadline/overdue/next_action). Navegação do card e da próxima ação
  usam `next_action.route` (+ `fragment` quando presente).
- `pages/dashboard/dashboard.spec.ts`: mockar `/dashboard` único.

## Validação (testes obrigatórios)

### Backend — `test/test_dashboard.py`
- **happy path**: org com Contexto aprovado + Gap parcial + SoA rascunho ⇒ 3 cards com status,
  `progress_pct` e KPIs corretos (comparar com `compute_dashboard` direto — SC-002).
- **não iniciado**: org sem Gap/SoA ⇒ cards `not_started`, sem progresso/responsável inventados.
- **revisão vencida**: versão de Contexto com `next_review_at` no passado ⇒ card `needs_review`,
  `overdue=true`.
- **próxima ação**: estados distintos ⇒ `next_action.route` esperado.
- **RBAC**: papel sem `view_dashboard` ⇒ 403; papel sem `view_gap` ⇒ card de Gap omitido.
- **degradação**: forçar erro num módulo (ex.: assessment malformado) ⇒ card `error`, demais ok.

### Backend — `test/test_tenant_isolation_dashboard.py` (obrigatório)
- Usuário da Org A com `X-Org-Context` da Org B ⇒ **404 genérico**, nenhum dado de B no corpo,
  audit log `CROSS_TENANT_DENIED` registrado.
- Consultor multi-org operando na Org A ⇒ só dados de A.

### Frontend — `dashboard.spec.ts`
- Render dos KPIs e do nº de cards a partir do mock de `/dashboard`.
- Estado de loading e de "não iniciado".

## Comandos

```bash
# Backend
pytest wtnapp/test/test_dashboard.py wtnapp/test/test_tenant_isolation_dashboard.py

# Frontend
cd wtnadmin && npm test
```

## Definition of Done (recap da constituição)

- [ ] `GET /dashboard` escopado por tenant (via `get_org_context`), RBAC `view_dashboard`.
- [ ] Cards gated por permissão de módulo; sem elevação.
- [ ] Sem audit log em sucesso; tentativas não autorizadas auditadas (dependencies centrais).
- [ ] Testes: happy, falhas, **isolamento de tenant**, RBAC, degradação.
- [ ] Router registrado em `main.py`. **Sem migration** (nenhuma mudança de schema).
- [ ] Frontend consome o endpoint único; specs verdes.
