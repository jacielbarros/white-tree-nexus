# Contracts — Gap Analysis (Feature 004)

API REST do módulo. Todos os endpoints (exceto a rota pública tokenizada do respondente externo, que
reusa o padrão do Motor 003) exigem JWT + header `X-Org-Context`, são escopados por tenant
(`tenant_scope` + RLS) e auditados. Erros cross-tenant ⇒ `404` genérico.

Convenções de permissão (RBAC):
- `view_gap` — ler matriz/catálogo/dashboard/baselines.
- `manage_gap` — editar catálogo e itens de avaliação, adotar versão do seed.
- `approve_gap_baseline` — enviar p/ revisão e aprovar/congelar baseline (Admin da organização).
- Condução (US5) reusa `assign_form` / `fill_form` / `sign_form` do Motor 003.

Resumo dos grupos:
- **Catálogo** (`/gap/catalog`): cópia editável da org + adoção versionada do seed.
- **Avaliação** (`/gap/assessment`): matriz, itens, dashboard, lacunas, baseline (Documento Controlado).
- **Condução** (`/gap/assignments` + rota pública `/forms/respond/...` reusada do 003): atribuir,
  preencher, devolver/cancelar, assinar.

Spec completa: [openapi.yaml](openapi.yaml).
