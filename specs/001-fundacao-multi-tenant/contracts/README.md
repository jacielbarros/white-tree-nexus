# Contracts — Fundação Multi-Tenant

Arquivo principal: [`openapi.yaml`](openapi.yaml) (OpenAPI 3.1). Este README documenta as
**convenções transversais** que todo endpoint segue — derivadas de `spec.md` e `research.md`.

## Autenticação & contexto

- **`Authorization: Bearer <JWT>`** (HS512). Claims: `sub`, `tenant_ids`, `role`, `iss`, `iat`,
  `exp`, `jti`. Expiração: `TOKEN_EXPIRY_MINUTES` (padrão 20).
- **`X-Org-Context: <org_id>`** — organização-alvo da requisição (R10). Obrigatório para
  Consultor (multi-org) e Super Admin; validado contra os vínculos. Ausência quando exigido ⇒
  **400**.
- Endpoints públicos (sem auth): bootstrap, login, forgot/reset password, accept invite.

## Política de status de erro (R9)

| Situação | Status |
|----------|--------|
| Recurso de **outro tenant** (por id) | **404** genérico (não revela existência) + audit `denied` |
| Sem permissão **no próprio tenant** | **403** + audit `denied` |
| Não autenticado / token inválido/expirado/revogado / conta bloqueada / org suspensa | **401** genérico |
| Contexto de organização ausente quando exigido | **400** |
| Conflito (slug/e-mail duplicado, bootstrap já feito, última-admin) | **409** |
| Validação de payload | **422** |
| Rate limit excedido | **429** |

- Corpo de erro: `{ "detail": "<mensagem genérica em PT>" }`. **Nunca** stack, nome de tabela,
  ou confirmação de existência cross-tenant (FR-034).
- Listagens nunca retornam itens de outro tenant (resultado vazio, não erro).

## Rate limiting

- `POST /auth/login` → `RATE_LIMIT_AUTH` (padrão 5/min).
- `POST /auth/password/forgot` → `RATE_LIMIT_PASSWORD_REQUEST` (padrão 3/min).
- Demais endpoints sensíveis podem herdar limites default. Implementado via slowapi.

## Auditoria

Toda operação sensível chama `AuditService.log_from_request()` (sessão própria, append-only,
sem PII/segredos). Operações cobertas: ver `data-model.md` §AuditLog. Ações do Super Admin são
auditadas sem exceção (FR-025/FR-031).

## Isolamento de tenant

Aplicado pela dependency central `tenant_scope` (escopo primário) + RLS no PostgreSQL (defesa em
profundidade). Nenhum filtro de tenant ad-hoc nos routers. Toda rota escopada tem teste de
isolamento dedicado (`test/test_tenant_isolation.py`).
