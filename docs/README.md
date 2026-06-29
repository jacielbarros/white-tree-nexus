# Prompts de `/speckit.specify` — White Tree Nexus

Cada arquivo aqui é o **prompt de entrada de uma feature** para o `/speckit.specify`.
Todos são **agnósticos de stack** de propósito: o QUÊ vive na spec; o COMO (FastAPI +
Angular, modelo de dados, estratégia de tenant) é decidido no `/speckit.plan`, guiado
pela [constitution](../.specify/memory/constitution.md).

## Regras de ouro

- **Uma spec por feature.** Não tente specar vários módulos num único `specify` — isso
  quebra o rastreamento requisito→implementação.
- **A fundação multi-tenant vem primeiro.** É a espinha (organizações, auth, RBAC,
  isolamento de tenant, auditoria) de que todos os módulos dependem.
- **Pré-requisitos importam.** Cada módulo assume que os anteriores já foram
  especificados/implementados (vínculos de evidência, controles, etc.).
- **Padrões transversais.** O padrão **"Documento Controlado SGSI" (cláusula 7.5)** —
  versionamento, aprovação, classificação, retenção e rastreabilidade — é compartilhado por todos
  os módulos. Definição canônica em
  [`iso27001-documento-controlado.md`](iso27001-documento-controlado.md). Os prompts dos módulos
  foram **enriquecidos a partir do estudo de caso real** em `material_de_contexto/`.
- **Motor de Workflow de Preenchimento** (atribuível + assinável) — outra capacidade transversal:
  template → atribuição → preenchimento → assinatura (avançada, Lei 14.063/2020) → snapshot imutável,
  com trilha/wizard. Consumido pelo Diagnóstico e pelo Gap Analysis. Design + prompt em
  [`feature-003-workflow-preenchimento.md`](feature-003-workflow-preenchimento.md).

## Fase MVP (nesta ordem)

| # | Feature | Prompt |
|---|---------|--------|
| 0 | Fundação multi-tenant | [`00-fundacao-multi-tenant.md`](00-fundacao-multi-tenant.md) |
| 1 | Diagnóstico e Contexto da Organização | [`01-diagnostico-contexto.md`](01-diagnostico-contexto.md) |
| 2 | Gap Analysis ISO 27001:2022 (+ seed do Anexo A) | [`02-gap-analysis.md`](02-gap-analysis.md) |
| 3 | Gestão de Ativos / Processos / Escopo — **implementada** ([`specs/011-asset-process-scope/`](../specs/011-asset-process-scope/)) | — |
| 4 | Gestão de Riscos: Ameaças & Vulnerabilidades → Avaliação (6.1.2) → Tratamento (6.1.3) — **implementada** ([`specs/012-risk-management/`](../specs/012-risk-management/)) | — |
| 5 | Statement of Applicability (SoA) — consolida o tratamento de risco; hoje em **Pré-SoA** sobre o Gap até a versão definitiva ([`specs/005-soa-declaracao-aplicabilidade/`](../specs/005-soa-declaracao-aplicabilidade/)) | [`03-soa.md`](03-soa.md) |
| 6 | Evidências / Auditoria / Melhoria Contínua (PDCA) | [`05-gestao-evidencias.md`](05-gestao-evidencias.md) |

> _Sequência revisada para a ordem lógica da ISO (risco **antes** da SoA, pois a SoA é output do
> tratamento de risco — 6.1.3 d). O **Plano de Ação** (prompt [`04-plano-de-acao.md`](04-plano-de-acao.md))
> foi absorvido pelo **Plano de Tratamento de Riscos** nesta esteira._

> **Status atual — fonte de verdade: [`CLAUDE.md`](../CLAUDE.md).** Implementadas: Fundação (001),
> Diagnóstico/Contexto (002), Motor de Workflow (003), Gap Analysis (004), SoA/Pré-SoA (005),
> Dashboard de Conformidade (006), Orientação do Gap (007), Evidências do Gap (008), Documentos
> imprimíveis/assináveis (009–010), Ativos/Processos/Escopo (011) e Gestão de Riscos (012). Este
> índice preserva os **prompts de specify originais**; a **sequência e o status vivem no `CLAUDE.md`**.

## Evolução pós-MVP (prompts a criar quando chegar a vez)

Auditoria Interna · Revisão pela Direção · Dashboard Executivo ·
Recursos de IA (opt-in por organização).

**Capacidade transversal mapeada:** **Central de Templates de Comunicação** (parametrizar
convite/redefinição/atribuição/OTP/assinatura por organização, com padrões da plataforma) — design +
prompt de specify em
[`feature-templates-comunicacao-specify.md`](feature-templates-comunicacao-specify.md).

**Backlog do MVP — Revisão de UX / Design System** (transversal, todas as telas do `wtnadmin/`):
redesenhar a interface (hoje crua, PrimeNG sem customização) com direção **enterprise sóbrio**,
mantendo PrimeNG + tema customizado (claro + escuro). Brief + **prompt pronto para o Claude Design**
em [`feature-ux-revamp.md`](feature-ux-revamp.md).

**Backlog do MVP — Dashboard de Conformidade + Motor de Rastreabilidade/Timeline** (transversais):
o **Dashboard** (home da organização; tela-âncora da Revisão de UX) e o **Motor de Rastreabilidade/
Timeline** (linha do tempo de eventos via `audit_logs`, painel de versões, conformidade no tempo;
**sem upload/tags — isso é o Módulo 5**). Escopo, reuso e **prompts `/speckit.specify` prontos** em
[`feature-dashboard-rastreabilidade.md`](feature-dashboard-rastreabilidade.md).

## Fluxo por feature

```
/speckit.specify   ← cola o bloco do arquivo da feature
/speckit.clarify   ← (opcional) resolve ambiguidades
/speckit.plan      ← decide a stack, guiado pela constitution
/speckit.tasks
/speckit.implement
```
