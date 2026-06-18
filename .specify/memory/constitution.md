# White Tree Nexus Constitution

*Princípios fundantes que governam todo o desenvolvimento da plataforma.
Este documento é a fonte de verdade para decisões de design, arquitetura e qualidade.
Deve ser lido e seguido antes de qualquer especificação, planejamento ou implementação.*

> **Codinome provisório:** "White Tree Nexus". Faça find-replace pelo nome real do produto
> quando definir a marca. Diretórios de referência: `wtnapp/` (backend), `wtnadmin/` (admin web).

---

## Identidade do Produto

A **White Tree Nexus** é uma **plataforma SaaS multi-tenant de Gestão de SGSI e Compliance
ISO/IEC 27001:2022**, destinada a consultores, empresas e auditores conduzirem toda a
jornada de implementação do SGSI: contexto da organização, gap analysis, gestão de riscos,
Statement of Applicability (SoA), plano de ação, evidências, auditoria interna e preparação
para certificação.

Princípios de identidade que guiam todas as decisões:

- **Isolamento absoluto entre organizações (tenants)** — dado de uma organização nunca é
  visível, listável ou alterável por usuário de outra organização. Esta é a invariante
  catastrófica do produto: um vazamento cross-tenant compromete a confiança de todos os
  clientes simultaneamente.
- **Integridade e cadeia de custódia das evidências** — a plataforma é o sistema de registro
  (system of record) de um SGSI auditável. Evidências, decisões de risco e registros de
  conformidade precisam ser versionados, rastreáveis e atribuíveis a quem os criou/alterou.
- **Rastreabilidade operacional** — toda ação sensível é registrada em trilha de auditoria
  imutável, dissociada de dados sensíveis.

A White Tree Nexus **não é** uma ferramenta genérica de formulários, planilhas ou gestão de
tarefas. É um sistema de compliance auditável. Essa distinção deve guiar todas as decisões de
produto e segurança.

---

## Princípio Fundante

> **Corretude e segurança prevalecem sobre velocidade de entrega.**

Quando houver tensão entre entregar rápido e entregar certo, o padrão é sempre entregar certo.
Num sistema de compliance multi-tenant, uma falha de isolamento ou de integridade de evidência
não tem patch retroativo — ela compromete a credibilidade de auditorias e certificações já
emitidas com base nos dados. Prefira uma feature a menos a uma feature com falha silenciosa.

---

## Core Principles

### I. Isolamento de Tenant — Inviolável

**Toda** leitura e escrita de dados de domínio é escopada pela organização (tenant) do usuário
autenticado. Nenhum endpoint retorna, lista ou permite alterar dado pertencente a outra
organização. O escopo de tenant **não pode** depender de o desenvolvedor lembrar de filtrar em
cada query — deve ser aplicado num ponto único e não-contornável (dependency/helper central,
e idealmente reforçado na camada de banco). Tentativas de acesso cross-tenant retornam
`404`/`403` (sem revelar existência do recurso em outro tenant) e geram audit log.
Isolamento de tenant **deve ter teste automatizado dedicado** — não é suficiente "confiar" que
a query filtra.

### II. Autorização por Papel + Escopo de Tenant

O acesso é controlado por RBAC granular sobre papéis (Super Admin da plataforma, Admin da
organização, Consultor, Cliente, Gestor, Dono de processo, Dono de controle, Auditor interno,
Colaborador convidado). Permissões são verificadas via factory `require_permission(...)`.
O JWT carrega o(s) tenant(s) e o papel do usuário; o Super Admin da plataforma é o único papel
cross-tenant e suas ações são especialmente auditadas. Todo JWT carrega `jti` (UUID4); logout
revoga o `jti` no Redis com TTL = tempo restante do token (política **fail-open** se Redis
indisponível — disponibilidade > segurança absoluta em falha de infra, mas logar como warning).

### III. Auditoria e Rastreabilidade Obrigatórias

Toda operação sensível (login, mudança de papel/permissão, acesso a dado de outra organização,
criação/edição de risco, SoA, evidência, constatação de auditoria, exportação de relatório)
**deve chamar `AuditService.log_from_request()`.** O audit log usa sessão própria para persistir
mesmo em rollback da transação principal. Trilha de auditoria é **imutável** (append-only): nunca
editar nem apagar registros. Nunca incluir dados sensíveis (senhas, OTPs, tokens, chaves, PII em
texto claro, conteúdo confidencial de evidência) em campos de audit log.

### IV. Integridade e Versionamento de Evidências

Evidências e artefatos de compliance (SoA, registros de risco, constatações) são **versionados**:
toda alteração preserva o histórico e registra autor, data e ação (envio, aprovação, rejeição,
alteração). O ciclo de aprovação/rejeição de evidência é rastreável de ponta a ponta. Operações
de compliance não destroem o registro anterior — elas geram nova versão.

### V. Proteção de Dados Sensíveis

Dados sensíveis e confidenciais do cliente (registros de risco, conteúdo de evidências, PII
coletada no diagnóstico) são cifrados em repouso quando aplicável, e **nunca** aparecem em logs,
respostas de erro, telemetria ou comentários de código. Mensagens de erro ao usuário não expõem
stack traces, nomes de tabelas, nem a existência de recursos de outro tenant.

### VI. Test-First para Lógica de Negócio

Testes cobrem o que **deveria** ser implementado segundo a spec, não apenas o que foi
implementado. Backend: pytest com SQLite in-memory e override centralizado de `get_db`.
Frontend: Vitest + Angular TestBed. Happy path, casos de falha principais **e teste de
isolamento de tenant** são obrigatórios. TDD é preferido; no mínimo, escrever testes antes de
marcar a feature como pronta.

---

## Arquitetura — Regras que não dobram

Estas convenções existem por razões técnicas deliberadas. Não as viole sem discussão
explícita documentada na spec da feature.

### Backend (Python / FastAPI / SQLAlchemy)

- **Sem repository layer.** Queries SQLAlchemy ficam nos routers. Lógica reutilizável
  vai em `services/` ou `helpers/`.
- **Sem `AsyncSession`.** Backend usa SQLAlchemy síncrono intencionalmente.
- **`get_db()` centralizado** de `<backend>/database/database.py`. Nunca criar local.
- **Escopo de tenant centralizado.** A resolução do tenant do usuário e o filtro por tenant
  vivem num único helper/dependency reutilizável — nunca espalhados ad-hoc por router.
- **Todo novo router registrado em `main.py`** via `app.include_router(...)`.
- **Configuração via `settings.py` + `load_dotenv()`** — não usar `pydantic-settings`.
- **Sem middleware** além de CORS, rate limiting e (quando justificado na spec) resolução de
  tenant. Não adicionar middleware sem requisito explícito.
- **Pydantic v2:** `.model_dump()`. ORM schemas com `class Config: from_attributes = True`.
- **Logging:** módulo `logging` em código novo.
- **Schema:** atualizar modelo SQLAlchemy **e** criar migration Alembic para qualquer
  mudança de tabela. Não remover `create_all()` do startup.

### Frontend Admin (Angular 21)

- **Sem NgModules.** Standalone é o padrão (não declarar `standalone: true` explicitamente).
- **`input()` / `output()`** — nunca `@Input()` / `@Output()` decorators.
- **`inject()`** — nunca injeção via construtor.
- **Control flow nativo:** `@if`, `@for`, `@switch` — nunca `*ngIf`, `*ngFor`.
- **`ChangeDetectionStrategy.OnPush`** em todos os componentes.
- **Estado com Signals** (`signal()`, `computed()`). Evitar `BehaviorSubject` para estado local.
- **Classes de componente sem sufixo `Component`** no nome da classe.
- **Reactive Forms com `NonNullableFormBuilder`.**

---

## Definição de "Pronto" (Definition of Done)

Uma feature só está pronta quando todos estes itens são verdadeiros:

1. Implementa exatamente o que está na spec — sem comportamentos não especificados.
2. Testes cobrem happy path, casos de falha principais **e isolamento de tenant**.
3. Novos endpoints têm audit log onde aplicável e escopo de tenant aplicado.
4. Nenhum dado sensível/PII exposto em logs, respostas de erro, telemetria ou comentários.
5. Router registrado em `main.py` (backend) ou componente na rota correta (frontend).
6. Migrations Alembic geradas para qualquer mudança de schema.
7. Spec atualizada se a implementação divergiu do plano por razão técnica legítima.

---

## Princípios de Produto SaaS

- **Backward compatibility por padrão.** Mudanças em APIs e schemas devem ser aditivas.
  Breaking changes exigem versionamento ou plano de migração.
- **Configurabilidade via `.env`.** Parâmetros operacionais (expiry de tokens, rate limits,
  cotas por plano) devem ser configuráveis sem mudança de código. Configuração específica por
  tenant fica no banco, não em `.env`.
- **Falhas de infra externa (Redis, SMTP, storage de evidências) tratadas graciosamente.**
  Definir explicitamente na spec se a feature tem comportamento degradado (fail-open) ou
  bloqueia (fail-closed), com justificativa. **Exceção:** isolamento de tenant é sempre
  fail-closed — nunca degrade segurança de tenant por falha de infra.
- **Recursos de IA (quando habilitados)** não treinam modelos com dados do tenant e não vazam
  conteúdo de um tenant para outro. Por padrão usar os modelos Claude mais recentes
  (ex.: `claude-opus-4-8`, `claude-sonnet-4-6`). Funcionalidades de IA são opt-in por organização.
- **Mensagens de erro ao usuário** não expõem stack traces, nomes de tabelas, ou
  detalhes de implementação interna.

---

## Idioma e Estilo

- Comentários e strings voltadas ao usuário podem misturar Português e Inglês.
  **Preserve o idioma predominante do arquivo que você está editando.**
- Nomes de variáveis, funções e classes: inglês.
- Mensagens de erro da API e textos de UI: Português (público-alvo brasileiro de GRC/compliance).

---

## O Que Nunca Fazer

- Executar query de dado de domínio sem escopo de tenant.
- Vazar a existência de um recurso de outro tenant (mensagens/erros distintos).
- Logar PII, senhas, OTPs, tokens, chaves, ou conteúdo confidencial de evidência.
- Editar ou apagar registros de audit log / histórico de evidência (são append-only).
- Criar `get_db()` local em um router.
- Usar `AsyncSession` no backend.
- Usar `@Input()`/`@Output()` decorators ou NgModules no Angular.
- Omitir audit log em operações sensíveis.
- Implementar comportamentos não descritos na spec sem documentar a divergência.
- Remover rate limiting de endpoints de autenticação.
- Degradar isolamento de tenant por falha de infra (tenant é sempre fail-closed).

---

## Governance

Esta constitution é a autoridade máxima — sobrepõe preferências individuais e hábitos
de desenvolvimento. Todo PR/review deve verificar conformidade com estes princípios.

Mudanças nos **Princípios de Segurança** (Core Principles I–V) e nas **Regras de Arquitetura**
exigem discussão explícita documentada. Mudanças em **Princípios de Produto** podem ser
propostas em specs de features específicas e ratificadas aqui quando aprovadas.

**Version**: 1.0.0 | **Ratified**: 2026-06-18 | **Last Amended**: 2026-06-18
