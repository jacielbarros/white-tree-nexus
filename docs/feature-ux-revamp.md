# Backlog do MVP — Revisão de UX / Design System (transversal)

> **Status:** backlog (planejado). Capacidade **transversal** — afeta todas as telas do `wtnadmin/`.
> **Como executar:** o trabalho de design será feito no **Claude Design**, colando o prompt da
> seção [Prompt para o Claude Design](#prompt-para-o-claude-design). A implementação no Angular/PrimeNG
> entra depois, como feature própria (Spec Kit) ou como tarefa de refino contínuo.
>
> **Inclui o Dashboard de Conformidade** (home da organização) como **tela-âncora** desta revisão —
> escopo funcional do dashboard e do motor de rastreabilidade/timeline em
> [feature-dashboard-rastreabilidade.md](feature-dashboard-rastreabilidade.md).

## Problema

A interface atual está **crua**: usa o preset **PrimeNG Material sem nenhuma customização**
(`wtnadmin/src/styles.scss` está vazio). Sintomas:

- **Navegação:** topbar plana com 12+ links espremidos numa linha só, sem agrupamento, ícones,
  hierarquia ou estado responsivo. Não comunica os "módulos" do produto.
- **Sem design system:** nenhum token de cor/tipografia/espaçamento próprio; cada página define
  estilos inline soltos (`styles: [...]`), gerando inconsistência entre telas.
- **Sem identidade:** o produto é uma plataforma de **compliance ISO 27001 / SGSI** (público:
  consultores, auditores, gestores de risco) e a UI não transmite confiança/sobriedade.
- **Padrões ausentes:** não há cabeçalho de página padronizado, estados vazios, estados de
  carregamento, semântica de status consistente, nem tema escuro coerente.

## Decisões travadas (definidas com o usuário)

| Decisão | Escolha |
|---|---|
| Direção visual | **Enterprise sóbrio e confiável** (corporativo limpo, paleta contida, foco em confiança e densidade de dados controlada) |
| Sistema de design | **Manter PrimeNG 21 + tema customizado** (redesenhar via design tokens + tema próprio, reaproveitando os componentes; sem reescrever do zero) |
| Tema | **Claro + escuro** (tokens para os dois modos desde o início) |
| Escopo do output | **Design system + telas-chave** (tokens/componentes + mockups das telas mais importantes; o restante segue o padrão) |

## Inventário de telas (superfície atual)

### Públicas (fora do shell, sem autenticação)
1. **Login** (`pages/login/`)
2. **Esqueci a senha** (`pages/password/forgot-password`)
3. **Redefinir senha** (`pages/password/reset-password`)
4. **Aceite de convite** (`pages/invite-accept/`) — usuário novo (define senha) vs. existente (só confirma)
5. **Responder formulário por token** (`pages/form-respond/`) — respondente **externo**, com **OTP** e
   **assinatura eletrônica avançada**; rota pública `/respond/:token`

### Dentro do shell (autenticadas)
| Módulo | Tela | Componente |
|---|---|---|
| **Início** | **Dashboard de Conformidade (home da org)** — card por módulo c/ status, %, prazo, responsável, atalho p/ próxima ação | `pages/dashboard/` *(a criar — ver [feature-dashboard-rastreabilidade.md](feature-dashboard-rastreabilidade.md))* |
| Administração | Organizações | `pages/organizations/` |
| Administração | Usuários + convites | `pages/users/` |
| Contexto (Cláusula 4) | Diagnóstico | `pages/diagnostic/` |
| Contexto (Cláusula 4) | Análise de Contexto (PESTEL/SWOT) | `pages/context-analysis/` |
| Contexto (Cláusula 4) | Partes Interessadas (Mendelow Poder×Interesse) | `pages/stakeholders/` |
| Contexto (Cláusula 4) | Declaração de Escopo | `pages/scope/` |
| Contexto (Cláusula 4) | Visão Consolidada + sugestões | `pages/context-overview/` |
| Workflow | Templates de formulário (builder) | `pages/form-templates/` |
| Workflow | Formulários / Atribuições (ciclo de vida + wizard/timeline) | `pages/form-assignments/` |
| Workflow | Preenchimento | `pages/form-fill/` |
| Gap Analysis | Matriz + condução atribuível | `pages/gap-analysis/` |
| Gap Analysis | Dashboard de aderência + lacunas | `pages/gap-dashboard/` |
| Gap Analysis | Catálogo editável + adoção do seed | `pages/gap-catalog/` |
| Gap Analysis | Baselines (congelar/aprovar/comparar) | `pages/gap-baselines/` |
| SoA | Declaração de Aplicabilidade (matriz por tema, consolidar, divergência) | `pages/soa/` |
| SoA | Versões da SoA (revisar/aprovar, exportar PDF) | `pages/soa-versions/` |

### Rearquitetura de navegação proposta (a maior melhoria de UX)
Substituir a topbar plana por **sidebar agrupada por módulo** + topbar enxuta (marca, seletor de
organização, usuário/logout, alternância de tema):

- **Início** — Dashboard de Conformidade (home da organização; tela-âncora)
- **Administração** — Organizações · Usuários
- **Contexto (Cláusula 4)** — Diagnóstico · Análise de Contexto · Partes Interessadas · Escopo · Visão
- **Workflow** — Templates · Formulários
- **Gap Analysis** — Matriz · Dashboard · Catálogo · Baselines
- **SoA** — Declaração de Aplicabilidade · Versões

---

## Prompt para o Claude Design

> Copie tudo abaixo da linha e cole no Claude Design. É auto-contido.

---

Você é um designer de produto sênior. Crie um **design system enterprise** e os **mockups das
telas-chave** para uma plataforma SaaS de **gestão de SGSI e compliance ISO/IEC 27001:2022**
chamada **White Tree Nexus**.

### Contexto do produto
- **O que é:** plataforma multi-tenant que acompanha a jornada de implementação do SGSI de várias
  organizações (diagnóstico de contexto → gap analysis → declaração de aplicabilidade → plano de
  ação → evidências).
- **Quem usa:** consultores de segurança da informação, auditores internos, gestores de risco,
  donos de controle e clientes/admins de organização. Pessoas que passam horas na ferramenta lendo
  e editando dados estruturados de conformidade.
- **Sentimento desejado:** **sobriedade, confiança, rigor, calma.** É uma ferramenta de
  auditoria/compliance — nada de exuberância. Densidade de informação **controlada** (legível, não
  poluída). Pense em algo entre Linear e um GRC corporativo sério (Vanta/Drata), mas mais sóbrio.
- **Idioma da UI:** **Português do Brasil** (todos os textos dos mockups em PT-BR).

### Restrições técnicas (obrigatórias)
- Frontend é **Angular 21 + PrimeNG 21** com o preset **Material** do `@primeuix/themes`.
- **NÃO** propor troca de biblioteca: o design deve ser **implementável reestilizando o PrimeNG via
  design tokens + tema customizado** (sobrescrita das CSS variables do PrimeNG, ex.: `--p-*`, e
  tokens próprios `--wtn-*`). Use componentes que existem no PrimeNG (Button, Select/Dropdown,
  InputText, Textarea, Card, Dialog, Tag, Table, Tabs, Toast, Timeline, etc.).
- **Tema claro E escuro**: entregue a paleta completa de tokens nos dois modos, com contraste
  **WCAG AA** garantido.
- Entregue os mockups como **HTML + CSS** (usando CSS variables para os tokens), prontos para servir
  de referência de implementação.

### Parte 1 — Design system (entregar como especificação + amostras)
1. **Tokens de cor** (claro + escuro): superfícies (background, surface, card, border), texto
   (primário, secundário, muted), **cor de marca/primária** (escolha um tom sóbrio — sugestão: um
   verde-petróleo/teal escuro ou azul corporativo, alinhado ao nome "White Tree"), e uma escala
   **semântica de status** reutilizável (success, warning, danger, info, neutral).
2. **Semântica de status do domínio** (crítica — mapeie cores aos estados reais):
   - Status de avaliação de gap: **Atende** (success) · **Parcialmente atende** (warning) ·
     **Não atende** (danger) · **N/A** (neutral/info) · **Não avaliado** (muted/cinza).
   - Prioridade de lacuna: **Crítico** · **Alto** · **Médio** · **Baixo**.
   - Status de workflow: rascunho · pendente · em preenchimento · enviado · assinado · concluído ·
     devolvido · cancelado.
3. **Tipografia:** escala (display, h1–h4, body, small, caption), fonte sem-serifa legível e
   profissional, pesos. Bom para leitura de tabelas densas.
4. **Espaçamento, raio e elevação:** escala de espaçamento (4/8px base), radius sóbrio (pequeno,
   não muito arredondado), sombras sutis.
5. **Especificação de componentes** (estados default/hover/focus/disabled, claro+escuro):
   botões (primário/secundário/text/danger), inputs/select/textarea com label e mensagem de erro,
   card, **tag/badge de status** (usando a semântica acima), **tabela densa** com cabeçalho fixo,
   dialog/modal, **toast** (sucesso/erro/aviso/info), tabs, **timeline/wizard** (passos do workflow),
   **estado vazio** (empty state) e **estado de carregamento** (skeleton/spinner).
6. **Padrão de cabeçalho de página:** título + descrição curta + ações à direita, consistente em
   todas as telas.
7. **Acessibilidade:** foco visível, contraste AA, navegação por teclado, tamanho de alvo.

### Parte 2 — Navegação / layout (shell)
Hoje a navegação é uma topbar plana com 12+ links numa linha — refazer.
- **Sidebar vertical agrupada por módulo** + topbar enxuta.
- **Topbar:** marca "White Tree Nexus", **seletor de organização** (multi-tenant — troca o contexto),
  identidade do usuário, sair, **alternância de tema claro/escuro**.
- **Sidebar (grupos e itens, com ícones):**
  - **Início:** Dashboard de Conformidade (home)
  - **Administração:** Organizações · Usuários
  - **Contexto (Cláusula 4):** Diagnóstico · Análise de Contexto · Partes Interessadas · Escopo · Visão
  - **Workflow:** Templates · Formulários
  - **Gap Analysis:** Matriz · Dashboard · Catálogo · Baselines
  - **SoA:** Declaração de Aplicabilidade · Versões
- Mostrar estado ativo, agrupamento colapsável e versão responsiva (sidebar colapsa em telas
  estreitas).

### Parte 3 — Mockups das telas-chave (claro + escuro)
1. **Login** (tela pública, centrada, com a marca) — e por consistência indicar o padrão das demais
   telas de auth (esqueci senha, redefinir, aceite de convite).
2. **Shell + Dashboard de Conformidade (HOME — tela-âncora):** a nova navegação (sidebar + topbar)
   tendo como conteúdo o **dashboard**: um **card por módulo** (Contexto, Gap Analysis, SoA; e,
   futuramente, Plano de Ação e Evidências), cada card com **status** (rascunho/em revisão/aprovado),
   **% de progresso/aderência**, **responsável**, **prazo** (com destaque para "revisão vencida") e um
   **atalho para a próxima ação**. Pode incluir um indicador de **conformidade ao longo do tempo**
   (mini-gráfico). É a primeira tela que o usuário vê ao entrar na organização.
3. **Gap Analysis — Matriz:** grade de itens das duas dimensões (**Cláusulas 4–10** e **93 controles
   do Anexo A**, agrupados por tema: Organizacional/Pessoas/Físico/Tecnológico), cada item com código
   de referência (ex.: "A.8.12"), nome e **tag de status**. Dialog de edição do item (status,
   justificativa de N/A, constatações, ações, prioridade, responsável). Seção de **condução atribuível**
   (atribuir a um membro/externo, com linha do tempo do workflow).
4. **Gap Analysis — Dashboard:** indicador de **aderência geral** (%), distribuição por status,
   aderência por dimensão, e **lista priorizada de lacunas** (itens "parcial" + "não atende").
5. **Formulário (preenchimento/atribuição):** um formulário de fase com campos por seção, **wizard/
   linha do tempo** do ciclo de vida (pendente → em preenchimento → enviado → assinado → concluído) e
   a etapa de **assinatura eletrônica avançada** (identidade + carimbo de tempo + selo de integridade).

### Entregáveis
- Especificação dos tokens (claro + escuro) e dos componentes.
- Mockups HTML/CSS das telas da Parte 3, nos dois temas, anotados com os tokens usados.
- Guia curto de aplicação (como mapear os tokens para as CSS variables do PrimeNG).

---

## Próximos passos (após o Claude Design)
1. Revisar tokens + mockups com o time.
2. Implementar o tema no `wtnadmin/`: `styles.scss` (tokens globais + overrides do PrimeNG) e o
   novo shell (sidebar agrupada). Migrar os estilos inline das páginas para os tokens.
3. Aplicar o padrão de cabeçalho de página, estados vazios/carregamento e semântica de status em
   todas as telas, módulo a módulo.
