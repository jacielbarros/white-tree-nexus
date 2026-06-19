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

## Fase MVP (nesta ordem)

| # | Feature | Prompt |
|---|---------|--------|
| 0 | Fundação multi-tenant | [`00-fundacao-multi-tenant.md`](00-fundacao-multi-tenant.md) |
| 1 | Diagnóstico e Contexto da Organização | [`01-diagnostico-contexto.md`](01-diagnostico-contexto.md) |
| 2 | Gap Analysis ISO 27001:2022 (+ seed do Anexo A) | [`02-gap-analysis.md`](02-gap-analysis.md) |
| 3 | Statement of Applicability (SoA) | [`03-soa.md`](03-soa.md) |
| 4 | Plano de Ação | [`04-plano-de-acao.md`](04-plano-de-acao.md) |
| 5 | Gestão de Evidências | [`05-gestao-evidencias.md`](05-gestao-evidencias.md) |

## Evolução pós-MVP (prompts a criar quando chegar a vez)

Gestão de Riscos · Auditoria Interna · Revisão pela Direção · Dashboard Executivo ·
Recursos de IA (opt-in por organização).

## Fluxo por feature

```
/speckit.specify   ← cola o bloco do arquivo da feature
/speckit.clarify   ← (opcional) resolve ambiguidades
/speckit.plan      ← decide a stack, guiado pela constitution
/speckit.tasks
/speckit.implement
```
