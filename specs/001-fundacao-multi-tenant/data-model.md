# Phase 1 — Data Model: Fundação Multi-Tenant

**Feature**: `001-fundacao-multi-tenant` · **Date**: 2026-06-18

Convenções: PKs são UUID v4. Timestamps em UTC (`timezone=True`). Toda entidade escopada por
tenant tem `tenant_id` (FK → `organizations.id`) e está sujeita a RLS. `User`,
`PasswordResetToken` e eventos de plataforma do `AuditLog` **não** são escopados por tenant
(identidade/plataforma globais). Migrations Alembic + `create_all()` no startup.

---

## Entidades

### Organization (`organizations`) — raiz de tenancy

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `name` | str(200) | obrigatório |
| `slug` | str(60) | **único**, lowercase, `[a-z0-9-]`; identificador estável |
| `status` | enum `OrgStatus` | `active` \| `suspended`; default `active` na criação |
| `created_by` | UUID FK→users.id (nullable) | Super Admin criador |
| `created_at` / `updated_at` | timestamptz | — |

- **Não** possui `tenant_id` (é o tenant). Não sujeita a RLS de tenant (acesso controlado por
  pertença/Super Admin na aplicação).
- Transições de estado: ver §State Machines.

### User (`users`) — identidade global

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `email` | citext/str(320) | **único** global, normalizado lowercase; usado p/ login |
| `full_name` | str(200) | PII — nunca em logs/auditoria/erros |
| `password_hash` | str | Argon2id; `NULL` até o aceite do convite/definição |
| `status` | enum `UserStatus` | `pending` \| `active` \| `disabled` |
| `failed_login_count` | int | default 0 (R6) |
| `locked_until` | timestamptz null | bloqueio temporário (R6) |
| `password_changed_at` | timestamptz | invalida tokens com `iat` anterior (R3) |
| `is_platform_super_admin` | bool | default false; marca o papel cross-tenant |
| `created_at` / `updated_at` | timestamptz | — |

- Identidade global: **sem** `tenant_id`. A atuação ocorre sempre via `Membership`.
- `email`/`full_name` são PII operacional: protegidos por controle de acesso + escopo; **não**
  cifrados em coluna (necessários para lookup/exibição); cifragem de campo (`FIELD_ENCRYPTION_KEY`)
  fica reservada a dados de domínio mais sensíveis em features futuras.

### Membership (`memberships`) — vínculo Usuário↔Organização (escopado)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `tenant_id` | UUID FK→organizations.id | **escopo de tenant** |
| `user_id` | UUID FK→users.id | — |
| `role` | enum `Role` | papel do vínculo (ver §Papéis) |
| `status` | enum `MembershipStatus` | `active` \| `disabled` |
| `invited_by` | UUID FK→users.id null | quem convidou |
| `created_at` / `updated_at` | timestamptz | — |

- **Unique** `(tenant_id, user_id)` — no máximo um vínculo por par.
- **Invariante FR-020** (validada na aplicação): só `role = consultant` pode ter um usuário com
  >1 membership. Se um usuário possui qualquer membership de papel ≠ `consultant`, esse é o seu
  **único** membership. (Reforço opcional por trigger/constraint de verificação.)
- **Salvaguardas** (FR-022): não permitir desativar/alterar o último `org_admin` ativo de uma
  organização; não permitir remover o único Super Admin da plataforma.

### Invitation (`invitations`) — escopado

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `tenant_id` | UUID FK→organizations.id | escopo de tenant |
| `email` | str(320) | destinatário (lowercase) |
| `role` | enum `Role` | papel a atribuir no aceite |
| `invited_by` | UUID FK→users.id | autor |
| `token_hash` | str(64) | **único**; SHA-256 do segredo (R7) |
| `status` | enum `InviteStatus` | `pending` \| `accepted` \| `expired` \| `revoked` |
| `expires_at` | timestamptz | `INVITE_EXPIRY_HOURS` |
| `accepted_at` | timestamptz null | uso único |
| `created_at` | timestamptz | — |

- **Unique parcial** `(tenant_id, email)` enquanto `status = pending` (evita convite duplicado
  ativo p/ o mesmo e-mail na mesma org).
- Convidar e-mail que já tem membership ativo naquela org ⇒ rejeitar (edge case da spec).

### PasswordResetToken (`password_reset_tokens`) — global (user-level)

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `user_id` | UUID FK→users.id | — |
| `token_hash` | str(64) | **único**; SHA-256 (R7) |
| `expires_at` | timestamptz | `RESET_TOKEN_EXPIRY_MINUTES` |
| `used_at` | timestamptz null | uso único |
| `created_at` | timestamptz | — |

### AuditLog (`audit_logs`) — append-only

| Campo | Tipo | Regras |
|-------|------|--------|
| `id` | UUID PK | — |
| `actor_user_id` | UUID null | null p/ sistema/bootstrap |
| `actor_role` | str null | papel no momento da ação |
| `tenant_id` | UUID null | contexto; null p/ eventos de plataforma |
| `operation` | str | ex.: `LOGIN`, `LOGIN_FAILED`, `ACCOUNT_LOCKED`, `ACCOUNT_UNLOCKED`, `BOOTSTRAP`, `ORG_CREATE`, `ORG_STATUS_CHANGE`, `USER_INVITE`, `INVITE_ACCEPT`, `INVITE_REVOKE`, `ROLE_CHANGE`, `MEMBERSHIP_DISABLE`, `PWD_RESET_REQUEST`, `PWD_RESET_COMPLETE`, `CROSS_TENANT_DENIED` |
| `entity_type` / `entity_id` | str null | alvo |
| `outcome` | enum | `success` \| `denied` |
| `ip` / `user_agent` | str null | metadados de segurança (não conteúdo) |
| `details` | JSONB null | **sem** senhas/tokens/chaves/PII de conteúdo |
| `created_at` | timestamptz | — |

- **Imutável**: nenhum endpoint de UPDATE/DELETE; reforço por trigger PostgreSQL que rejeita
  UPDATE/DELETE.
- Persistido em sessão própria (sobrevive a rollback). Super Admin é auditado sem exceção.

---

## Enums

```text
OrgStatus        = active | suspended
UserStatus       = pending | active | disabled
MembershipStatus = active | disabled
InviteStatus     = pending | accepted | expired | revoked
Role             = super_admin | org_admin | consultant | client | manager
                 | process_owner | control_owner | internal_auditor | guest_collaborator
AuditOutcome     = success | denied
```

> `Role` é definido em `settings.py`. `super_admin` aparece como papel de plataforma (marcado
> também por `users.is_platform_super_admin`); os demais são papéis de `Membership`.

---

## Papéis & Permissões (matriz — `helpers/permissions.py`)

Permissões desta fundação:

| Permissão | Descrição |
|-----------|-----------|
| `manage_organizations` | criar organização e mudar ciclo de vida (ativar/suspender/reativar) |
| `invite_users` | convidar / revogar / reenviar convites na organização |
| `manage_memberships` | alterar papel, desativar vínculo, desbloquear conta de usuário |
| `view_organization` | ver dados da própria organização |

Mapeamento papel → permissões (default; configurável):

| Papel | manage_organizations | invite_users | manage_memberships | view_organization |
|-------|:---:|:---:|:---:|:---:|
| **super_admin** | ✅ (cross-tenant) | ✅ | ✅ | ✅ |
| **org_admin** | — | ✅ | ✅ | ✅ |
| **consultant** | — | ✅¹ | —² | ✅ |
| **client** | — | — | — | ✅ |
| **manager** | — | — | — | ✅ |
| **process_owner** | — | — | — | ✅ |
| **control_owner** | — | — | — | ✅ |
| **internal_auditor** | — | — | — | ✅ |
| **guest_collaborator** | — | — | — | ✅³ |

¹ Consultor convida **dentro das organizações em que tem vínculo ativo**.
² Gestão de papéis/desbloqueio reservada a `org_admin`/`super_admin` no MVP (ajustável por org
em features futuras).
³ `view_organization` mínimo; permissões de negócio chegam nas features de domínio.

- `super_admin` **bypassa o escopo de pertença** (cross-tenant) mas **não** a auditoria, e opera
  um tenant por vez via `X-Org-Context` (R8/R10).
- Verificação sempre via `require_permission("<perm>")`; negação ⇒ 403 + audit (FR-024).

---

## State Machines

**Organization.status**
```
            create
              │
              ▼
        ┌──────────┐  suspend   ┌────────────┐
        │  active  │ ─────────▶ │ suspended  │
        │          │ ◀───────── │            │
        └──────────┘  reactivate└────────────┘
```
- `active`: usuários operam normalmente. `suspended`: login recusado e requests negados
  (fail-closed, R4); dados preservados. "Ativar" = transição inicial/garantir `active`.

**User.status**: `pending` (convidado, sem senha) → `active` (aceitou + senha definida) →
`disabled` (desativado). `disabled`/`pending` não autenticam.

**Membership.status**: `active` ↔ `disabled` (sujeito às salvaguardas FR-022).

**Invitation.status**: `pending` → `accepted` (uso único) | `expired` (passou `expires_at`) |
`revoked` (autor/admin revogou). Estados finais não aceitáveis (FR-018).

---

## Row-Level Security (defesa em profundidade)

Para cada tabela escopada (`memberships`, `invitations`, e todo modelo de domínio futuro):

```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON <t>
  USING (tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid);
```

- A dependency `tenant_scope` executa `SET LOCAL app.tenant_id = :ctx` na sessão da requisição
  (mesma conexão do ORM). Super Admin seta o tenant-alvo escolhido (opera 1 por vez).
- `organizations` não tem RLS de tenant (escopo de pertença é aplicado na app); `users` e
  `audit_logs` são globais/append-only.
- RLS é **defesa em profundidade** — o escopo central da app continua sendo o mecanismo primário
  e o **teste de isolamento de tenant** valida ambos.

---

## Relacionamentos (resumo)

```
organizations 1───∞ memberships ∞───1 users
organizations 1───∞ invitations
users        1───∞ password_reset_tokens
(*)          0..1─∞ audit_logs            # actor/tenant podem ser null (plataforma/sistema)
```
