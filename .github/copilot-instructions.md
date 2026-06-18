# White Tree Nexus — Copilot Instructions

> Codinome provisório "White Tree Nexus" — find-replace pelo nome real. Prefixo `wtn`.

A White Tree Nexus e uma plataforma SaaS **multi-tenant** de Gestao de SGSI e Compliance
ISO/IEC 27001:2022. Este e um **monorepo** com modulos independentes.

## Modulos

| Diretorio | Modulo | Stack | Instrucoes |
|-----------|--------|-------|------------|
| `wtnapp/` | Backend API | Python, FastAPI, SQLAlchemy | [backend.instructions.md](instructions/backend.instructions.md) |
| `wtnadmin/` | Admin/Web | Angular 21, PrimeNG 21, Signals | [admin.instructions.md](instructions/admin.instructions.md) |

## Como usar

Identifique em qual diretorio esta o arquivo sendo editado e siga as instrucoes
especificas do modulo correspondente. **Antes de qualquer mudanca, observe os principios
inegociaveis em `.specify/memory/constitution.md`** — em especial o isolamento de tenant.

## Convencoes Globais

- Comentarios e mensagens de usuario em **portugues** (sem acentos em arquivos .md de config)
- Commits descritivos em portugues
- Variaveis de ambiente sensiveis em `.env` (nunca commitadas)
- Cada modulo tem seu proprio `.gitignore` para artefatos de build

## Invariante Critica — Isolamento de Tenant

Todo dado de dominio e escopado pela organizacao (tenant) do usuario. Nenhum endpoint
retorna/altera dado de outra organizacao. O filtro por tenant vive num ponto unico
(`helpers/tenant_scope.py`), nunca ad-hoc no router. Acesso cross-tenant ⇒ 404/403 +
audit log. Toda feature tem teste de isolamento dedicado.

## Recomendacoes Tecnicas Nao Implementadas

Sempre que voce (ou o usuario) identificar uma melhoria/refactor que **nao sera aplicado
agora** (por escopo, prioridade ou risco), registre-a em `docs/recomendacoes_pendentes.md`.
Antes de propor nova recomendacao, **leia esse arquivo primeiro** para nao duplicar.
Quando implementada, mova-a para a secao "Implementadas" (com a data) ou remova-a.

## Fluxo Geral do Sistema

1. **Consultor/Admin da organizacao** configura o contexto da organizacao e conduz o
   diagnostico, gap analysis e SoA via painel Angular.
2. **Backend** gerencia autenticacao (JWT), RBAC, escopo de tenant, auditoria e persistencia.
3. **Donos de processo/controle e auditores** registram evidencias, riscos e constatacoes.
4. **Gestores/Alta direcao** acompanham o progresso via dashboards e relatorios (PDF/Excel).
