# Quickstart — Fundação Multi-Tenant

**Feature**: `001-fundacao-multi-tenant`. Como subir a base, exercitar o fluxo
bootstrap → organização → convite → login, e rodar os testes (incluindo isolamento de tenant).

> Greenfield: os diretórios `wtnapp/` e `wtnadmin/` são criados por esta feature
> (ver `plan.md` §Source Code). O passo a passo abaixo assume que a implementação seguiu o plano.

---

## 1. Pré-requisitos

- Python 3.13, PostgreSQL, Redis (opcional em dev — revogação de `jti` é fail-open).
- Node 20+ para o frontend.

## 2. Backend — `.env`

```env
DATABASE_URL=postgresql://postgres:password@localhost/wtndatabase
JWT_SECRET_KEY=<64-byte hex>
TOKEN_EXPIRY_MINUTES=20
RESET_TOKEN_EXPIRY_MINUTES=30
REDIS_URL=redis://localhost:6379/0
CORS_ALLOWED_ORIGINS=http://localhost:4200,http://127.0.0.1:4200
RATE_LIMIT_AUTH=5/minute
RATE_LIMIT_PASSWORD_REQUEST=3/minute
MAX_LOGIN_ATTEMPTS=5
# --- novos nesta feature (research.md R5/R6/R7/R8) ---
LOCKOUT_DURATION_MINUTES=15
INVITE_EXPIRY_HOURS=72
PASSWORD_MIN_LENGTH=12
BOOTSTRAP_TOKEN=<segredo de uso único p/ o 1º Super Admin>
SMTP_HOST=...
SMTP_PORT=...
SMTP_USER=...
SMTP_PASSWORD=...
EMAIL_FROM=no-reply@example.com
```

## 3. Subir backend

```bash
source <venv>/Scripts/activate          # Windows
pip install -r requirements.txt
alembic upgrade head                     # cria tabelas + políticas RLS
uvicorn wtnapp.main:app --reload
```

## 4. Fluxo end-to-end (curl)

```bash
# (1) Bootstrap do 1º Super Admin — só funciona uma vez, exige BOOTSTRAP_TOKEN
curl -X POST localhost:8000/bootstrap/super-admin -H 'Content-Type: application/json' -d '{
  "bootstrap_token":"<BOOTSTRAP_TOKEN>","email":"root@plataforma.com",
  "full_name":"Root","password":"<senha forte 12+>"}'

# (2) Login do Super Admin
TOKEN=$(curl -s -X POST localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"root@plataforma.com","password":"<senha>"}' | jq -r .access_token)

# (3) Criar organização
ORG=$(curl -s -X POST localhost:8000/organizations -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' -d '{"name":"ACME S/A","slug":"acme"}' | jq -r .id)

# (4) Convidar o Admin inicial da organização (FR-002a) — contexto = org criada
curl -X POST localhost:8000/invitations -H "Authorization: Bearer $TOKEN" \
  -H "X-Org-Context: $ORG" -H 'Content-Type: application/json' \
  -d '{"email":"admin@acme.com","role":"org_admin"}'
# -> e-mail com o token de convite (best-effort). Pegue o token (em dev, do log/serviço).

# (5) Aceitar convite (público): define senha e ativa o vínculo
curl -X POST localhost:8000/invitations/accept -H 'Content-Type: application/json' -d '{
  "token":"<token do e-mail>","full_name":"Admin ACME","password":"<senha 12+>"}'

# (6) Login do Admin da organização e operar dentro do seu tenant
```

## 5. Verificações-chave (mapeiam aos Success Criteria)

- **SC-007**: repetir o passo (1) ⇒ **409** (bootstrap já feito).
- **SC-003**: errar a senha `MAX_LOGIN_ATTEMPTS` vezes ⇒ login passa a **401** (bloqueado);
  esperar `LOCKOUT_DURATION_MINUTES` **ou** `POST /users/{id}/unlock` (admin) **ou** redefinir
  senha ⇒ volta a autenticar.
- **SC-004**: após `POST /auth/logout`, reusar o token ⇒ **401**; idem após expirar.
- **SC-005**: aceitar convite expirado/revogado ⇒ **400** genérico.
- **SC-001 / SC-008 / SC-ISO**: com dois tenants, usar token do tenant A com
  `X-Org-Context` do tenant B (ou acessar recurso por id do tenant B) ⇒ **404** genérico + audit.

## 6. Frontend

```bash
cd wtnadmin
npm install
npm start            # http://localhost:4200  (login, esqueci/redefinir senha,
                     # aceitar convite, gestão de organizações, gestão de usuários/convites)
```

## 7. Testes (Definition of Done)

```bash
# Backend — pytest + SQLite in-memory, override central de get_db
pytest wtnapp/test/
pytest wtnapp/test/test_tenant_isolation.py   # OBRIGATÓRIO — gate inegociável

# Frontend
cd wtnadmin && npm test
```

Cobertura mínima esperada (Princípio VI):
- **Happy path** de cada história (US1–US5).
- **Falhas principais**: credencial inválida, conta bloqueada, convite expirado/revogado,
  permissão negada, org suspensa, bootstrap duplicado.
- **Isolamento de tenant** dedicado: leitura/listagem/alteração cross-tenant ⇒ 404/403 + audit,
  para cada recurso escopado (organização, vínculo, convite); Consultor multi-org só vê suas
  orgs; e validação de que a RLS rejeita query sem `app.tenant_id` setado.
- **Auditoria**: cada ação sensível gera exatamente 1 registro, sem PII/segredos, append-only.
