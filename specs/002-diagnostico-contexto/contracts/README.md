# Contracts — Diagnóstico e Contexto (Cláusula 4)

Arquivo principal: [`openapi.yaml`](openapi.yaml) (OpenAPI 3.1). Convenções herdadas da fundação
(ver `specs/001-fundacao-multi-tenant/contracts/README.md`):

- **`Authorization: Bearer <JWT>`** + **`X-Org-Context: <org_id>`** (obrigatório p/ Consultor
  multi-org e Super Admin).
- Erros padronizados: 401 (não autenticado), 403 (sem permissão no próprio tenant), 404
  (cross-tenant/recurso inexistente, genérico), 409 (conflito), 422 (validação), 429 (rate limit).
  Corpo: `{ "detail": "<mensagem genérica PT>" }`. Nunca vaza stack/tabela/existência cross-tenant.
- Toda operação sensível é auditada (`AuditService`). Isolamento via `tenant_scope` + RLS.

## Padrão de ciclo de vida de documento controlado (compartilhado pelos 3 artefatos)

Análise de Contexto, Mapa de Partes Interessadas e Declaração de Escopo expõem o mesmo conjunto de
ações de ciclo de vida (ver os caminhos `.../submit-review`, `.../approve`, `.../versions`):

- Edição dos dados de trabalho (rascunho corrente) exige `manage_context`.
- `submit-review`: `draft` → `in_review`.
- `approve`: `in_review` → emite **versão imutável** (snapshot) com status `in_force`; versão
  anterior → `obsolete`. Exige **`approve_context_document`** (Admin da organização). Sempre ≤ 1
  versão `in_force` por artefato.
- `versions`: lista o histórico append-only (somente leitura).

Permissões: `view_context` (ver), `manage_context` (editar), `approve_context_document` (aprovar).
Acesso de leitura adicionalmente sujeito à política de classificação da organização, se configurada.
