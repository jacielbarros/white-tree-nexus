# Contracts — Feature 003 (Motor de Workflow de Preenchimento)

- [`openapi.yaml`](openapi.yaml) — OpenAPI 3.0.3 (19 paths, 15 schemas). Validado (parse OK).

## Convenções

- **Autenticadas**: `bearerAuth` (JWT) + header `X-Org-Context` (org ativa), como nas features 001/002.
- **Públicas por token**: `/forms/respond/{token}/*` — o **token é a credencial** e dá acesso a
  **apenas 1 atribuição**. Sem `X-Org-Context` (o token resolve o tenant internamente).
- **Cross-tenant** ⇒ `404`/`403` genérico (sem revelar existência) + audit. Token inválido/expirado
  ⇒ `404`/`410`.
- **Transição de estado inválida** ⇒ `409`. **Campo obrigatório ausente** no envio ⇒ `422`.

## Grupos de endpoints

| Grupo | Prefixo | Permissão base |
|---|---|---|
| Templates (autoria) | `/forms/templates` | `assign_form` (escrita) / `view_form` (leitura) |
| Atribuições (consultor + preenchedor membro) | `/forms/assignments` | `assign_form` / `fill_form` / `sign_form` + ownership |
| Resposta externa (token) | `/forms/respond/{token}` | posse do token (sem conta) |
| Política de assinatura | `/forms/signature-policy` | `assign_form` |

## Notas de segurança

- `token` e `otp` trafegam, mas **só o hash** é persistido (token na atribuição; OTP em tabela
  transiente com TTL). Nunca aparecem em audit/logs.
- A assinatura retorna metadados (papel, nome, `signed_at`, `content_hash`, `level=advanced`) — não o
  conteúdo das respostas.
- `GET /forms/assignments/{id}/verify` recomputa o selo SHA-256 sobre a versão imutável e compara.
