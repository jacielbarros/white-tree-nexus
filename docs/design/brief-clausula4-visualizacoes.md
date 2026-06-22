# Brief Claude Design — Telas com visualização (Cláusula 4)

Duas telas da Cláusula 4 do SGSI que **não** entraram no primeiro handoff e que ganham com uma
**visualização de domínio** (não bastam form + tabela): **Partes Interessadas** (mapa de Mendelow)
e **Análise de Contexto** (PESTEL/SWOT). As demais telas da Cláusula 4 (Diagnóstico, Escopo, Visão
Consolidada) já foram migradas reusando o design system existente.

> Use junto com o handoff já existente em `docs/design/` (tokens, tema claro+escuro, IBM Plex
> Sans/Mono, paleta verde-petróleo `--wtn-primary`). O objetivo é **manter consistência** com o que
> já está implementado: page-header (`wtn-page-header`), cards (`wtn-card`), tags de status
> (`wtn-tag--success/info/warning/danger/neutral`), chips de prioridade (`wtn-prio--*`), campos
> estilizados, tabelas como a da matriz do Gap, estados vazios e a sidebar agrupada.

---

## Tela 1 — Partes Interessadas (ISO/IEC 27001:2022, Cláusula 4.2)

**Objetivo:** mapear partes interessadas e visualizar o **engajamento recomendado** pela matriz de
**Mendelow (Poder × Interesse)**, em vez da tabela plana atual.

**Dados disponíveis (já existem no backend):**
- Por parte: `name`, `type` (`internal` | `external`), `power` (`alto`|`medio`|`baixo`),
  `interest` (`alto`|`medio`|`baixo`), `strategy` (derivada), `requirements[]`
  (`type`, `description`, `how_addressed`).
- **Estratégia derivada (Mendelow), pela regra do servidor:**
  - Poder **alto** + Interesse **alto** → **Gerenciar de perto**
  - Poder **alto** + interesse não-alto → **Manter satisfeito**
  - Interesse **alto** + poder não-alto → **Manter informado**
  - demais → **Monitorar**

**O que visualizar:**
- Um **grid Poder × Interesse** (eixo X = Interesse, eixo Y = Poder). Como a escala tem 3 níveis
  (alto/médio/baixo), prefira um **grid 3×3** com **fundo por quadrante** correspondendo às 4
  estratégias de Mendelow (a fronteira é "alto vs não-alto"). Cada parte aparece como **chip/ponto**
  posicionado na célula (poder, interesse), colorido/rotulado pela estratégia.
- Clicar num chip abre detalhes da parte (tipo, requisitos) — pode ser um painel lateral (como o
  painel de edição da matriz do Gap, 348px) ou um popover.
- Form de **adicionar parte** (Nome, Tipo, Poder, Interesse) integrado, leve.
- Uma **legenda** das 4 estratégias.
- Opcional: lista/tabela como visão alternativa (toggle grid/lista).

**Estados:** vazio ("nenhuma parte mapeada" + CTA adicionar), carregando, e leitura-apenas quando o
documento estiver em vigor.

**Prompt pronto:**
> Desenhe a tela **"Partes Interessadas"** de uma plataforma SaaS de compliance ISO/IEC 27001
> (tema enterprise sóbrio, claro+escuro, verde-petróleo, IBM Plex). É a Cláusula 4.2. O foco é uma
> **matriz de Mendelow (Poder × Interesse)**: um grid 3×3 (eixos Poder e Interesse em alto/médio/
> baixo) com o fundo de cada região indicando uma das 4 estratégias — **Gerenciar de perto**
> (poder alto + interesse alto), **Manter satisfeito** (poder alto), **Manter informado** (interesse
> alto), **Monitorar** (demais). Cada parte interessada é um chip posicionado na célula correspondente,
> com o nome e um indicador do tipo (interno/externo); ao clicar, mostra um painel lateral com os
> requisitos da parte. Inclua um formulário compacto para adicionar parte (Nome, Tipo, Poder,
> Interesse), uma legenda das estratégias, estado vazio e versão responsiva (em telas estreitas, a
> matriz vira lista agrupada por estratégia). Reaproveite o design system existente (cards, tags,
> campos, painel lateral).

---

## Tela 2 — Análise de Contexto (ISO/IEC 27001:2022, Cláusula 4.1)

**Objetivo:** registrar questões internas/externas usando **PESTEL** e **SWOT**, com layout que
torne a análise legível por categoria — não uma linha de form + tabela única.

**Dados disponíveis (já existem):**
- `intended_outcomes` (texto), `methodology` (texto), `draft_status`, fluxo de documento controlado
  (**Salvar / Enviar para revisão / Aprovar**).
- `issues[]`: cada questão tem `origin` (`internal`|`external`), `framework` (`pestel`|`swot`),
  `category` (texto livre), `description`, `impact` (`alto`|`medio`|`baixo`).

**O que visualizar:**
- **Bloco PESTEL:** 6 grupos — Político, Econômico, Social, Tecnológico, Ambiental, Legal — como
  colunas/cards; cada questão é um item com `description` + selo de `impact` (alto/médio/baixo).
- **Bloco SWOT:** quadrante 2×2 — **Forças / Fraquezas** (origem interna) e **Oportunidades /
  Ameaças** (origem externa); questões posicionadas por origem.
- Cabeçalho do documento com `intended_outcomes`/`methodology` e as ações de ciclo de vida
  (Salvar/Enviar para revisão/Aprovar) + tag de status.
- Form leve de **adicionar questão** (origem, framework, categoria, descrição, impacto).

**Estados:** vazio por bloco, carregando, leitura-apenas em vigor; selo de impacto com as cores
semânticas (alto = danger, médio = warning, baixo = neutral/info).

**Prompt pronto:**
> Desenhe a tela **"Análise de Contexto"** de uma plataforma SaaS de compliance ISO/IEC 27001
> (enterprise sóbrio, claro+escuro, verde-petróleo, IBM Plex). É a Cláusula 4.1 e usa dois frameworks:
> **PESTEL** (6 categorias: Político, Econômico, Social, Tecnológico, Ambiental, Legal — como
> cards/colunas) e **SWOT** (quadrante 2×2: Forças/Fraquezas internas, Oportunidades/Ameaças
> externas). Cada "questão" tem descrição e um nível de impacto (alto/médio/baixo) mostrado como selo
> colorido (alto=vermelho, médio=âmbar, baixo=neutro). No topo, os campos "Resultados pretendidos" e
> "Metodologia/fontes" e as ações de documento controlado (Salvar, Enviar para revisão, Aprovar) com
> uma tag de status. Inclua um formulário compacto para adicionar questão (origem, framework,
> categoria, descrição, impacto), estados vazios por bloco e layout responsivo. Reaproveite o design
> system existente (cards, tags de status, campos, page-header).

---

## Depois do design
Exporte o handoff (como no primeiro) e me avise onde ficou — eu implemento reusando os tokens e
padrões já no `wtnadmin/`, com specs (Vitest) e isolando a lógica (signals/computed). Ambas as telas
já têm backend pronto (`/context/stakeholders`, `/context/analysis`), então é só camada de UI.
