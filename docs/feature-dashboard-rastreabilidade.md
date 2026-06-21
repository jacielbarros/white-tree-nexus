# Backlog do MVP — Dashboard de Conformidade + Motor de Rastreabilidade/Timeline (transversais)

> **Status:** backlog (planejado). Duas capacidades **transversais e complementares**: o **Dashboard**
> é a *fotografia* (estado atual) e o **Motor de Rastreabilidade/Timeline** é o *filme* (histórico
> PDCA). Ambos agregam sobre os módulos existentes.
>
> **Achado-chave:** a maior parte já existe como dado — são, em essência, **camada de leitura/agregação
> + UI**. Não exigem novo modelo de domínio, salvo **uma** peça nova: um endpoint de **leitura** da
> trilha de auditoria (`audit_logs` hoje é só-escrita).

## Decisões travadas (definidas com o usuário)

1. **Item 2 = trilha/timeline sobre eventos + versões, SEM upload de arquivo.** Arquivos de evidência
   e **tags** (crítica/informativa/pendente) ficam no **Módulo 5 (Evidências)** e, quando existirem,
   aparecem na mesma timeline. Evita construir evidência duas vezes.
2. **Sequenciamento:** Dashboard (Item 1) **primeiro**, integrado à Revisão de UX; Rastreabilidade
   (Item 2) **logo em seguida**; depois Plano de Ação (#4) e Evidências (#5).
3. **O Dashboard é a tela-âncora da Revisão de UX** — desenhado junto, no **Claude Design**
   (ver [feature-ux-revamp.md](feature-ux-revamp.md)).

## Reuso (o que já existe — não reinventar)

| Necessidade | Já existe | Falta |
|---|---|---|
| Status por módulo | `draft_status` + `current_version_id` (Contexto/Gap/SoA) | agregar |
| % de progresso | `services/gap_metrics_service.py`; completude da SoA; completude de formulários | expor |
| Responsável / prazo | `form_assignments` (deadline_at/respondente); `responsible`/`deadline` por item | agregar |
| Versões (quem/quando/por quê) | `document_versions` (version_number, *_by, change_nature, emitted_at, next_review_at) | UI unificada |
| Eventos / timeline | `audit_logs` (operation/entity_type/actor/created_at; append-only) | **API de leitura** + UI |
| Conformidade no tempo | baselines do Gap (`content_snapshot.dashboard.overall_adherence` + data) | derivar série |
| Alerta "revisão vencida" | `controlled_document_service.review_overdue()` + `next_review_at` | surfacar |

---

## Item 1 — Dashboard de Conformidade (home da organização)

**Escopo:** primeira tela ao entrar na organização. Um **card por módulo** (Contexto, Gap Analysis,
SoA; cresce com Plano de Ação/Evidências) com: status (rascunho/em revisão/aprovado), **% de
progresso/aderência**, responsável, prazo, alerta de **revisão vencida** e **atalho para a próxima
ação**. Opcional: mini-gráfico de conformidade ao longo do tempo.

**Card como atalho (decisão de UX):** o **card inteiro navega para a tela do módulo** (atalho
principal); o **botão de "próxima ação" faz o deep-link específico** (ex.: "Concluir 1 controle" abre
o controle pendente) e *para a propagação* do clique do card; cards "não iniciado" levam à landing do
módulo e o botão "Iniciar" dispara a 1ª ação. Acessibilidade: card como alvo navegável (link/`role`
com `aria-label`), botão interno separado — sem aninhar `<button>` dentro de `<a>`.

**Backend:** um único endpoint **`GET /dashboard`** que **compõe serviços já existentes**
(`gap_metrics_service`, summary da SoA, overview de contexto, `form_assignments`) — **sem tabela
nova**. A "próxima ação" reusa a ideia heurística do `services/suggestion_service.py`.

**Frontend:** `pages/dashboard/` vira a home (`/app` redireciona para `dashboard` em vez de
`organizations`), com `permissionGuard` e contexto de org ativo. Desenho no Claude Design (UX revamp).

**Critérios observáveis:** status por módulo correto (derivado do artefato); % bate com as métricas;
prazos/responsáveis vêm das atribuições; "revisão vencida" aparece quando aplicável; **isolamento de
tenant** (dashboard de A nunca mostra dado de B).

### Prompt `/speckit.specify` (Item 1) — pronto

```
Dashboard de Conformidade da plataforma SaaS multi-tenant de Gestão de SGSI ISO/IEC 27001:2022.
É a PÁGINA INICIAL de cada organização: uma visão única e atualizada do estado de conformidade.
Capacidade TRANSVERSAL (agrega sobre os módulos existentes), respeitando o isolamento de tenant
(acesso cross-tenant negado 404/403 e auditado).

== Conteúdo ==
Um CARD por módulo do SGSI (Contexto/Cláusula 4, Gap Analysis, Statement of Applicability; e, quando
existirem, Plano de Ação e Evidências). Cada card exibe:
- STATUS da etapa: rascunho / em revisão / aprovado-em vigor (e "obsoleto/precisa revisão").
- PROGRESSO em porcentagem (preenchimento/aderência/completude conforme o módulo).
- RESPONSÁVEL pela etapa e PRAZO de conclusão (quando houver atribuição), com destaque visual quando
  a próxima ANÁLISE CRÍTICA estiver vencida.
- ATALHO para a próxima ação recomendada do módulo. O CARD INTEIRO é um atalho que abre a tela do
  módulo; o botão de próxima ação faz o atalho específico para o passo pendente.
Opcional: um indicador de CONFORMIDADE AO LONGO DO TEMPO (evolução da aderência).

== Requisitos observáveis ==
- O dashboard só mostra dados da organização ativa do usuário; cross-tenant é negado e auditado.
- Status, progresso, responsável e prazo refletem o estado real de cada módulo (sem dado inventado).
- Módulos ainda não iniciados aparecem com status/atalho adequados (ex.: "iniciar").
- A visualização é somente leitura; cada atalho leva à tela do módulo correspondente.

Fora de escopo: edição de dados dos módulos (cada módulo já tem suas telas); upload de evidências.
NÃO especificar stack — reusar no /plan os serviços de métricas/overview/atribuições já existentes,
sem novo modelo de domínio. É a tela-âncora da Revisão de UX (desenho no Claude Design).
```

---

## Item 2 — Motor de Rastreabilidade & Timeline (apoio ao PDCA)

**Escopo:** (a) **timeline por módulo** = leitura de `audit_logs` filtrada pelo conjunto de
`entity_type` da etapa (ex.: soa, soa_item, soa_version); (b) **painel de versões** unificado sobre
`document_versions` (quem/quando/natureza da alteração); (c) **gráfico de conformidade ao longo do
tempo** derivado das baselines do Gap (e versões da SoA). **Sem upload de arquivo e sem tags.**

**Única peça nova no backend:** **`GET /audit`** (e/ou `/audit/timeline`) — leitura **paginada**,
**tenant-scoped**, gated por **nova permissão `view_audit`**. A `audit_logs` já é desenhada sem PII;
a leitura **nunca** cruza tenant. Sugestão de papéis: **Admin da organização + Auditor interno**
(confirmar no clarify).

**Reuso:** `audit_logs`, `document_versions`, `controlled_document_service` (versões/`review_overdue`),
baselines do Gap (série). Nada de novo modelo de domínio.

**Boundary explícito:** classificação por **tags** (crítica/informativa/pendente) e **arquivos de
evidência** pertencem ao **Módulo 5 (Evidências)**. Quando o Módulo 5 existir, suas evidências entram
nesta mesma timeline. Aqui só há **leitura de eventos e versões**.

**Critérios observáveis:** a timeline de um módulo lista os eventos reais (aprovação, emissão de
versão, mudança de política, etc.) com autor e carimbo de tempo; o painel de versões mostra a cadeia
imutável (quem/quando/natureza); a curva de conformidade reflete as baselines emitidas; **somente
papéis autorizados** veem a trilha; **isolamento de tenant** total.

### Prompt `/speckit.specify` (Item 2) — pronto

```
Motor de Rastreabilidade e Timeline (apoio ao ciclo PDCA) da plataforma SaaS multi-tenant de Gestão
de SGSI ISO/IEC 27001:2022. Capacidade TRANSVERSAL que torna VISÍVEL e CONSULTÁVEL o histórico de
conformidade já registrado pela plataforma — pensado para auditorias externas. Respeita isolamento de
tenant (cross-tenant negado 404/403 e auditado).

== Linha do tempo por módulo ==
Para cada módulo (Contexto, Gap Analysis, SoA, e futuros), uma LINHA DO TEMPO dos eventos relevantes
já registrados na trilha de auditoria: aprovações, emissões/alterações de versão, mudanças de política
de classificação, submissões para revisão, etc. Cada item mostra QUEM e QUANDO (sem conteúdo sensível
nem PII).

== Painel de versões por documento ==
Para cada documento controlado (Análise de Contexto, Escopo, Mapa de Partes, baseline do Gap, SoA),
um PAINEL DE VERSÕES imutável mostrando, por versão: número, quem elaborou/revisou/aprovou, data de
emissão, próxima análise crítica e a NATUREZA da alteração — garantindo transparência total.

== Conformidade ao longo do tempo ==
Um gráfico que mostra a evolução da conformidade (ex.: aderência geral do Gap) a partir das versões/
baselines já emitidas, apoiando o "Check/Act" do PDCA.

== Papéis e permissões ==
A consulta à trilha de auditoria é restrita (ex.: Admin da organização e Auditor interno); demais
papéis não acessam a trilha bruta. A leitura é somente leitura e jamais cruza organizações.

== Requisitos observáveis ==
- A timeline e o painel de versões só mostram dados da organização do usuário; cross-tenant negado.
- A trilha é IMUTÁVEL (append-only) e a leitura nunca expõe PII/segredos.
- Cada evento exibido é rastreável até a etapa/documento correspondente.
- A curva de conformidade reflete fielmente as versões/baselines emitidas.

Fora de escopo: UPLOAD de arquivos de evidência e CLASSIFICAÇÃO por tags (crítica/informativa/
pendente) — pertencem ao Módulo de Evidências (Módulo 5), que depois aparece nesta mesma timeline.
NÃO especificar stack — reusar no /plan a trilha `audit_logs` (expondo leitura paginada, tenant-scoped,
gated por nova permissão view_audit), os documentos versionados (document_versions) e as baselines do
Gap; sem novo modelo de domínio.
```

---

## Sequenciamento no backlog do MVP

Dashboard (com a Revisão de UX) → Rastreabilidade/Timeline → Plano de Ação (#4) → Evidências (#5).
Ambos ficam mais ricos conforme #4 e #5 chegam, mas já entregam valor com Contexto/Gap/SoA.

## Próximos passos
1. Rodar o **Claude Design** (prompt em [feature-ux-revamp.md](feature-ux-revamp.md)) com o **Dashboard**
   como tela-âncora.
2. `/speckit.specify` do **Dashboard** (prompt acima) — feature transversal.
3. `/speckit.specify` do **Motor de Rastreabilidade/Timeline** (prompt acima) — feature transversal,
   logo após o dashboard.
