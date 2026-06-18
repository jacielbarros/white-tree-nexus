# Backend Instructions — wtnapp

> Codinome provisorio. Find-replace `wtnapp` pelo nome real do diretorio backend.

## Project Overview

`wtnapp` e o backend FastAPI da White Tree Nexus (SaaS multi-tenant de gestao de SGSI
ISO 27001:2022). Expoe endpoints para autenticacao, RBAC, gestao de organizacoes (tenants),
diagnostico, gap analysis, SoA, plano de acao, evidencias, riscos e auditoria interna.

## Technology Stack

- **Python 3.13** com virtual environment
- **FastAPI** — framework web
- **Pydantic v2** — validacao e serializacao (`.model_dump()`, `from_attributes = True`)
- **SQLAlchemy** — ORM com sessoes **sincronas**
- **Alembic** — migracoes de banco
- **JWT** via `python-jose` (HS512)
- **passlib + bcrypt** — hashing de senhas
- **slowapi** — rate limiting nos endpoints de autenticacao
- **Redis** — revogacao de token (jti) e rate limit; fail-open se indisponivel
- **pytest + TestClient** — testes com SQLite in-memory

## Architecture

```
wtnapp/
  main.py              # FastAPI app, CORS, health check, exception handlers, routers
  settings.py          # Configuracao via .env (load_dotenv)
  database/
    database.py        # engine, SessionLocal, get_db() centralizado
  models/              # SQLAlchemy models (<domain>_model.py) — todos com tenant_id
  schemas/             # Pydantic schemas (<domain>_schema.py)
  routers/             # Endpoints (<domain>.py) — logica de negocio vive aqui
  services/            # Logica reutilizavel (audit_service, crypto_service, notification_service)
  helpers/             # Utilitarios (permissions.py, tenant_scope.py, settings_helper.py)
  core/security/       # Gestao de chaves / cifragem de campos sensiveis
  utils/               # Integracoes externas (email SMTP, storage de evidencias, IA)
  test/                # Testes pytest
  alembic/             # Migracoes
```

## Key Patterns

### get_db() — Centralizado

Definido **uma unica vez** em `database/database.py`. NAO criar `get_db()` local.

```python
from wtnapp.database.database import get_db
db_dependency = Annotated[Session, Depends(get_db)]
```

### Isolamento de Tenant — Invariante Critica

Todo modelo de dominio tem `tenant_id`. O filtro por tenant vive em `helpers/tenant_scope.py`,
ponto unico e nao-contornavel. NUNCA filtrar tenant ad-hoc no router.

```python
from wtnapp.helpers.tenant_scope import scoped_query
items = scoped_query(db, Risk, user).all()   # ja filtra por tenant_id do usuario
```

Acesso cross-tenant ⇒ 404/403 (sem revelar existencia) + audit log. Cada feature tem
teste de isolamento dedicado.

### Router Pattern

```python
from wtnapp.database.database import get_db
router = APIRouter(prefix="/my-domain", tags=["my-domain"])
db_dependency = Annotated[Session, Depends(get_db)]
```

### RBAC (Perfis de Acesso)

```python
from wtnapp.helpers.permissions import require_permission
manage_dep = Annotated[dict, Depends(require_permission("manage_risks"))]

@router.post("/")
async def create_risk(user: manage_dep, ...): ...
```

Papeis: Super Admin da plataforma (unico cross-tenant), Admin da organizacao, Consultor,
Cliente, Gestor, Dono de processo, Dono de controle, Auditor interno, Colaborador convidado.
Super Admin tem bypass de permissao, mas NAO de auditoria.

### Audit Logs

```python
from wtnapp.services.audit_service import AuditService
AuditService.log_from_request(
    db=db, request=request, operation="CREATE", entity_type="risk",
    entity_id=str(risk.id), details={"title": risk.title}, user_id=user.get("user_id"),
)
```

- Sessao separada (persiste mesmo com rollback), falha silenciosa
- Trilha append-only: nunca editar/apagar
- NUNCA logar PII, senhas, tokens, chaves ou conteudo confidencial de evidencia

### DB Write Pattern

```python
db.add(obj); db.commit(); db.refresh(obj)  # refresh so quando retorna o objeto
```

### Error Handling

- `HTTPException` direto nos routers
- Handler global de `IntegrityError` → HTTP 409
- Health check `/healthy` verifica conexao com banco
- Mensagens de erro nunca expoem stack/tabela nem existencia de recurso de outro tenant

## Commands

```bash
source <venv>/Scripts/activate
uvicorn wtnapp.main:app --reload
pytest wtnapp/test/
alembic revision --autogenerate -m "descricao"
alembic upgrade head
```

## Testing

- SQLite in-memory com dependency overrides
- Override unico de `get_db` (centralizado)
- **Teste de isolamento de tenant obrigatorio** por feature
- `@pytest.mark.asyncio` para helpers async

## What to Avoid

- NAO executar query de dominio sem escopo de tenant
- NAO criar `get_db()` local nos routers
- NAO inventar camada de repositorio
- NAO usar `pydantic-settings` (configuracao em `settings.py` com `load_dotenv()`)
- NAO introduzir `AsyncSession`
- NAO esquecer de registrar novos routers em `main.py`
- NAO adicionar middleware sem requisito explicito
- NAO logar PII/dados sensiveis nos audit logs
- NAO editar/apagar audit logs ou historico de evidencias
