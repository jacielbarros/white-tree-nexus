# Phase 0 — Research: Fundação Multi-Tenant

**Feature**: `001-fundacao-multi-tenant` · **Date**: 2026-06-18

Todas as decisões abaixo resolvem os pontos técnicos do plano. Formato por item:
**Decisão · Justificativa · Alternativas consideradas**.

---

## R1. Estratégia de isolamento de tenant

**Decisão**: Shared-DB em PostgreSQL com coluna **`tenant_id`** (FK → `organizations.id`) em
todo modelo de domínio. Enforcement em **ponto único e não-contornável**: dependency
`tenant_scope` que (1) resolve o(s) tenant(s) do JWT + contexto de organização da requisição,
(2) expõe `scoped_query(db, Model, user)` que sempre injeta `WHERE tenant_id = :ctx`, e (3) seta
`SET LOCAL app.tenant_id = :ctx` na sessão ORM da requisição. **Defesa em profundidade:**
**Row-Level Security (RLS)** habilitada nas tabelas escopadas, com política que compara
`tenant_id` a `current_setting('app.tenant_id')`. Super Admin opera com contexto explícito de
organização (não há bypass de RLS por padrão; ver R8).

**Justificativa**: O volume inicial (~10³ orgs) não justifica o custo operacional de
schema/db-per-tenant (migrations multiplicadas, provisionamento, conexões). Shared-DB +
`tenant_id` com helper central satisfaz FR-027 ("ponto único e não-contornável"); RLS atende ao
"idealmente reforçado na camada de banco" da constitution, transformando um bug de filtro
esquecido em erro de zero linhas em vez de vazamento.

**Alternativas**: *Schema-per-tenant* (isolamento mais forte, mas migrations/conn-pool por
schema inviáveis no MVP); *DB-per-tenant* (máximo isolamento, custo operacional alto, rejeitado);
*apenas app-layer sem RLS* (rejeitado — fundação é o lugar certo para a defesa em profundidade da
invariante catastrófica).

---

## R2. Modelo de sessão / token

**Decisão**: JWT **HS512** assinado com `JWT_SECRET_KEY`. Claims: `sub` (user id),
`tenant_ids` (lista — múltipla só para Consultor; vazia/implícita para Super Admin), `role` (ou
papel por tenant), `iss`, `iat`, `exp`, `jti` (UUID4). Expiração configurável
(`TOKEN_EXPIRY_MINUTES`, padrão 20). **Logout** revoga o `jti` no Redis com TTL = tempo restante
(denylist, **fail-open** se Redis indisponível, logando warning). **Sessões concorrentes
permitidas** (cada login emite um `jti`); logout encerra a sessão corrente. Não há tabela
`sessions` — estado de revogação vive no Redis.

**Justificativa**: Alinhado à constitution (HS512 + `jti` em Redis fail-open). Stateless evita
tabela de sessão e mantém a API horizontalmente escalável. Sessões concorrentes são consequência
natural do modelo e atendem ao uso multi-dispositivo.

**Alternativas**: Sessões server-side em DB (rejeitado — contraria stateless e adiciona escrita
por request); refresh tokens (fora de escopo do MVP; expiração curta + relogin é suficiente).

---

## R3. Invalidação de sessões na troca de senha (FR-014)

**Decisão**: Coluna `users.password_changed_at` (timestamp). Toda validação de token rejeita
tokens com `iat < password_changed_at`. Redefinição/troca de senha atualiza esse campo,
invalidando **todos** os tokens anteriores do usuário sem precisar enumerá-los no Redis.

**Justificativa**: Cumpre FR-014 num modelo stateless, sem varrer/registrar cada `jti` ativo.
Barato (uma comparação por request) e à prova de sessões concorrentes.

**Alternativas**: Revogar cada `jti` ativo no Redis (exigiria rastrear todos os `jti` por
usuário — estado extra desnecessário).

---

## R4. Suspensão de organização (FR-004) — fail-closed

**Decisão**: A dependency `tenant_scope` verifica o `status` da organização do contexto a cada
requisição; se `suspensa`, retorna negação (403) e o token deixa de operar nesse tenant
imediatamente — **sem** depender de revogar tokens. Login de usuário cujo (único) tenant está
suspenso é recusado. Dados preservados.

**Justificativa**: Fail-closed por verificação em tempo de request é a forma mais simples e
robusta; não há janela de token "válido" para um tenant suspenso. Constituição: tenant é sempre
fail-closed.

**Alternativas**: Revogar tokens na suspensão (frágil, deixa janela e depende do Redis —
rejeitado).

---

## R5. Hashing de senha e política mínima

**Decisão**: **Argon2id** via `argon2-cffi` (parâmetros calibrados p/ ~100–250 ms). Política
mínima configurável: `PASSWORD_MIN_LENGTH` (padrão 12), exigir não-trivialidade básica
(rejeitar senha = e-mail; checagem de comprimento). Sem expiração compulsória de senha no MVP.

**Justificativa**: Argon2id é o padrão recomendado atual (resistente a GPU/ASIC). Comprimento
mínimo 12 alinhado a guidelines NIST 800-63B (priorizar tamanho sobre regras de composição).

**Alternativas**: bcrypt (aceitável; preterido por Argon2id ser superior e já comum no
ecossistema); regras de composição rígidas (rejeitadas — pioram usabilidade sem ganho real).

---

## R6. Política de bloqueio de conta (FR-009 / FR-009a)

**Decisão**: Em `users`: `failed_login_count` e `locked_until`. Após `MAX_LOGIN_ATTEMPTS`
(padrão 5) falhas consecutivas, setar `locked_until = now + LOCKOUT_DURATION_MINUTES`
(novo env, padrão 15). Remoção do bloqueio por **três meios**: (a) auto-expiração quando
`now > locked_until`; (b) desbloqueio manual por papel com `manage_memberships`
(Admin da organização / Super Admin) — auditado; (c) redefinição de senha bem-sucedida zera
contador e `locked_until`. Contador zera em login bem-sucedido.

**Justificativa**: Cobre exatamente o esclarecimento Q3 (ambos: auto + manual + reset). Estado
em colunas do usuário evita dependência do Redis para uma garantia de segurança.

**Alternativas**: Contador só em Redis (rejeitado — bloqueio é controle de segurança e não pode
ser fail-open); bloqueio só manual (rejeitado — péssima UX).

---

## R7. Tokens de convite e de redefinição de senha

**Decisão**: Gerar segredo aleatório (`secrets.token_urlsafe(32)`); **armazenar apenas o hash**
(SHA-256) em `invitations.token_hash` / `password_reset_tokens.token_hash` (índice único).
Enviar o segredo em claro só por e-mail. **Uso único** (marca `accepted_at`/`used_at`) e
expiração (`INVITE_EXPIRY_HOURS` padrão 72; `RESET_TOKEN_EXPIRY_MINUTES` padrão 30). Validação
faz hash da entrada e compara em tempo constante.

**Justificativa**: Vazamento do banco não revela tokens utilizáveis; uso único + expiração
limitam janela. Atende SEC-004 (tokens nunca em claro no storage/logs).

**Alternativas**: Guardar token em claro (rejeitado); JWT como token de convite (rejeitado —
não revogável e maior superfície).

---

## R8. Bootstrap do primeiro Super Admin (FR-001) e papel cross-tenant

**Decisão**: Endpoint `POST /bootstrap/super-admin` que só cria o Super Admin **quando não
existe nenhum** e quando o header/corpo traz `BOOTSTRAP_TOKEN` igual ao do `.env`. Após a
criação, qualquer chamada subsequente retorna 409/410. Super Admin é o único papel cross-tenant:
para operar dentro de uma organização precisa informar o **contexto de organização**
(header `X-Org-Context`); a dependency permite o acesso (bypass de *scoping* de pertença, **não**
de auditoria). Para RLS, o contexto do Super Admin seta `app.tenant_id` para o tenant-alvo
escolhido (opera um tenant por vez), preservando RLS.

**Justificativa**: Duplo gate (inexistência + segredo) evita corrida de "primeiro a chamar vira
admin". Manter o Super Admin operando "um tenant por vez" preserva a proteção RLS e mantém a
auditoria precisa por tenant.

**Alternativas**: Seed via script/CLI (válido, mas endpoint guardado é testável via TestClient e
documentável no quickstart); Super Admin com `BYPASSRLS` global (rejeitado — perde a rede de
segurança da RLS).

---

## R9. Regra de status de erro: 404 vs 403 (FR-028 / FR-034)

**Decisão**:
- Recurso **de outro tenant** acessado por id (read/update/delete) ⇒ **404 Not Found** genérico
  (não revela existência) + audit `outcome=denied`.
- Ação **dentro do próprio tenant** sem a permissão exigida ⇒ **403 Forbidden** + audit.
- Falha de autenticação (credencial inválida / token ausente/expirado/revogado) ⇒ **401**
  genérico.
- Listagens nunca incluem itens de outro tenant (resultado vazio, não erro).

**Justificativa**: 404 para cross-tenant evita o oráculo de existência; 403 para permissão dentro
do tenant é semanticamente correto e não vaza nada (o usuário já sabe que o recurso existe no seu
tenant). Consistente com a constitution ("sem revelar existência").

**Alternativas**: 403 para tudo (rejeitado — em cross-tenant 403 já confirma existência).

---

## R10. Seleção de contexto de organização (FR-029) para Consultor/Super Admin

**Decisão**: Requisições de usuários com múltiplas organizações (Consultor) ou cross-tenant
(Super Admin) carregam o contexto via header **`X-Org-Context: <org_id>`**. A `tenant_scope`
valida que: Consultor só escolhe orgs em que tem vínculo ativo; Super Admin pode escolher
qualquer org existente (auditado). Usuários de uma única organização derivam o contexto do seu
vínculo (header ignorado/validado). Ausência de contexto obrigatório ⇒ 400.

**Justificativa**: Contexto explícito por request mantém a API stateless e o escopo determinístico
por chamada (essencial para RLS via `SET LOCAL`). Evita estado de "org ativa" no servidor.

**Alternativas**: Codificar a org no path (`/orgs/{id}/...`) — mais verboso e duplica o escopo;
"org ativa" em sessão server-side (rejeitado — contraria stateless).

---

## R11. Auditoria — campos e imutabilidade (FR-030..FR-033)

**Decisão**: `AuditService.log_from_request()` grava em `audit_logs` numa **sessão própria**
(`SessionLocal`), persistindo mesmo em rollback da transação principal; falha de auditoria não
derruba a operação (loga warning). Campos: `actor_user_id` (nullable p/ sistema/bootstrap),
`actor_role`, `tenant_id` (nullable p/ eventos de plataforma), `operation`, `entity_type`,
`entity_id`, `outcome` (`success`/`denied`), `ip`, `user_agent`, `created_at`, `details` (JSON
**sem** segredos/PII de conteúdo). Append-only por convenção + ausência de endpoints de
edição/remoção; reforçável com trigger que bloqueia UPDATE/DELETE.

**Justificativa**: Espelha o padrão existente da plataforma (CLAUDE.md). `ip`/`user_agent` são
metadados de segurança legítimos (forense), não conteúdo sensível do tenant. Sessão própria
garante a trilha mesmo quando a operação falha/rollback.

**Alternativas**: Auditar na mesma transação (rejeitado — perde o registro no rollback);
não capturar `ip`/`ua` (rejeitado — reduz valor forense; mantidos como metadados de segurança).

---

## R12. Entrega de e-mail (convite/reset) — fail-soft

**Decisão**: `notification_service` + `utils/email.py` (SMTP). Convite/reset são **criados no
banco primeiro**; o envio do e-mail é best-effort: falha de SMTP não desfaz a criação, retorna
resposta genérica ao usuário e permite reenvio (FR-019). Nunca confirma existência de e-mail.

**Justificativa**: Degradação graciosa (Princípio de Produto). O artefato (convite/reset) é a
fonte de verdade; o e-mail é só transporte e é reenviável.

**Alternativas**: Transação atômica criação+envio (rejeitado — acopla disponibilidade do SMTP à
operação e pode vazar erro de envio).

---

## R13. Frontend — autenticação e contexto de organização

**Decisão**: `core/auth` com Signals (`signal()` para usuário/token/estado). HTTP interceptor
injeta `Authorization: Bearer` e `X-Org-Context` (org ativa selecionada, persistida em
`localStorage` e validada no servidor). Guards de rota: `authGuard` (sessão) e `roleGuard`
(permissão por papel). Telas standalone, `OnPush`, Reactive Forms com `NonNullableFormBuilder`.

**Justificativa**: Conforme constitution (Signals, standalone, OnPush). Interceptor centraliza o
contexto de tenant no cliente, espelhando o `tenant_scope` do servidor.

**Alternativas**: Estado via `BehaviorSubject` (preterido por Signals); org no path em vez de
header (mantido alinhado ao backend R10).

---

## Novos parâmetros de `.env` introduzidos por esta feature

| Variável | Padrão | Uso |
|----------|--------|-----|
| `LOCKOUT_DURATION_MINUTES` | `15` | Janela de auto-expiração do bloqueio de conta (R6) |
| `INVITE_EXPIRY_HOURS` | `72` | Validade do convite (R7) |
| `PASSWORD_MIN_LENGTH` | `12` | Política mínima de senha (R5) |
| `BOOTSTRAP_TOKEN` | — | Segredo de uso único p/ bootstrap do 1º Super Admin (R8) |

(Os demais — `DATABASE_URL`, `JWT_SECRET_KEY`, `TOKEN_EXPIRY_MINUTES`,
`RESET_TOKEN_EXPIRY_MINUTES`, `REDIS_URL`, `RATE_LIMIT_*`, `MAX_LOGIN_ATTEMPTS`, `SMTP_*`,
`CORS_ALLOWED_ORIGINS`, `CSP_ENABLED`, `FIELD_ENCRYPTION_KEY`) já constam no CLAUDE.md.)

**Status**: Todos os NEEDS CLARIFICATION resolvidos. Pronto para Phase 1.
