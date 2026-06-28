# Feature Specification: Módulo de Gestão de Riscos (Ameaças/Vulnerabilidades, Avaliação 6.1.2 e Plano de Tratamento 6.1.3)

**Feature Branch**: `012-risk-management`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "Especificar e implementar o MÓDULO DE GESTÃO DE RISCOS, que cobre num único módulo três fases encadeadas — Fase 1: Ameaças e Vulnerabilidades (identificação); Fase 2: Avaliação de Riscos (análise e avaliação, cláusula 6.1.2); Fase 3: Plano de Tratamento de Riscos (cláusula 6.1.3) — produzindo o insumo que alimentará a SoA definitiva. Um módulo é decisão de engenharia; na experiência da esteira guiada as três fases continuam sendo passos distintos."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Esta feature toca
  dados de domínio ⇒ DEVE especificar isolamento de tenant, auditoria e tratamento de dados
  sensíveis. Sem stack/tecnologia aqui (isso é do /speckit.plan).
-->

## Clarifications

### Session 2026-06-26

- Q: Como o impacto inerente do risco deve derivar da classificação CIA dos ativos vinculados? → A: Maior valor — `max(C,I,A)` dos ativos vinculados, mapeado para a escala de impacto de 5 níveis, com override manual justificado; avaliação por dimensão (C/I/D separadas) é refinamento futuro.
- Q: Ao selecionar controles no tratamento, como este módulo deve alimentar a SoA? → A: Expor o vínculo controle ← risco (razão "tratamento de risco" + riscos tratados) de forma **read-only**; este módulo **não grava nem muta** itens da SoA — a SoA só é escrita pela futura feature de finalização.
- Q: No cenário de risco, os ativos vinculados são obrigatórios? → A: Ativos são **opcionais** (0..n); sem ativos o impacto é informado manualmente (cenário simples). Ameaça e vulnerabilidade são sempre obrigatórias.
- Q: Como a aceitação de um risco pelo dono deve ser registrada? → A: Um usuário autorizado (`manage_risk`) registra a aceitação atribuída ao membro indicado como dono, com justificativa, em trilha append-only; sem fluxo separado de "login do dono".

## User Scenarios & Testing *(mandatory)*

<!--
  As três fases (Ameaças/Vulnerabilidades → Avaliação → Tratamento) são UM módulo de engenharia,
  mas continuam sendo PASSOS DISTINTOS na esteira guiada. As user stories abaixo são fatias
  independentemente testáveis; cada uma entrega valor por si só.
-->

### User Story 1 - Avaliar e registrar os riscos do SGSI (Fase 2 — cláusula 6.1.2) (Priority: P1)

Um consultor ou administrador da organização registra os riscos do SGSI como cenários: um ou mais
ativos (do módulo de Ativos), uma ameaça e uma vulnerabilidade (do catálogo da organização), com a
possibilidade de cenários mais simples quando aplicável. Para cada risco o sistema deriva o impacto
inerente a partir da classificação CIA do(s) ativo(s) (permitindo override manual justificado),
recebe a probabilidade, calcula o nível de risco pela matriz da metodologia (default 5x5) e sinaliza
se o risco está acima ou abaixo do critério de aceitação. O registro é listável com filtros e busca e
tem uma visão de matriz/heat map 5x5.

**Why this priority**: É o coração do módulo e a resposta direta às perguntas centrais do SGSI
("quais são os riscos? qual a probabilidade e o impacto? quais estão acima do critério de
aceitação?"). É o insumo do tratamento e, adiante, da SoA definitiva. Entregue sozinho — usando a
metodologia 5x5 padrão e o catálogo-semente já disponível — já produz um Registro de Riscos
utilizável.

**Independent Test**: Com uma organização autenticada e ativos cadastrados, criar riscos informando
ativos + ameaça + vulnerabilidade, confirmar que o impacto é derivado da CIA (com override
justificado), informar a probabilidade, e verificar que o nível inerente é calculado pela matriz e
que o sistema marca corretamente os riscos acima/abaixo do critério de aceitação, exibindo-os na
listagem e no heat map 5x5.

**Acceptance Scenarios**:

1. **Given** ativos cadastrados e o catálogo de ameaças/vulnerabilidades disponível, **When** o
   usuário cria um risco informando título, descrição, ativos, ameaça e vulnerabilidade, **Then** o
   sistema persiste o risco, gera um identificador interno automático único na organização e registra
   a criação no histórico.
2. **Given** um risco com ativos vinculados, **When** o usuário não informa impacto manual, **Then** o
   sistema deriva o impacto inerente a partir da classificação CIA do(s) ativo(s) (maior valor entre C,
   I e A) mapeada para a escala de impacto da metodologia.
3. **Given** um risco com impacto derivado da CIA, **When** o usuário sobrescreve o impacto
   manualmente, **Then** o sistema exige justificativa, preserva o valor ajustado e registra que houve
   override (autor, data, valor anterior e novo).
4. **Given** probabilidade e impacto definidos, **When** o usuário salva o risco, **Then** o sistema
   calcula o nível inerente pela matriz da metodologia e marca se o risco está acima ou abaixo do
   critério de aceitação configurado.
5. **Given** um Registro de Riscos com vários riscos, **When** o usuário aplica filtros (ex.: nível +
   status + dono + acima do critério) ou busca textual, **Then** a listagem mostra apenas os riscos que
   satisfazem os critérios, somente do tenant ativo.
6. **Given** o Registro de Riscos, **When** o usuário abre a visão de matriz/heat map, **Then** o
   sistema distribui os riscos nas células probabilidade × impacto 5x5, coloridas pelo nível.
7. **Given** um cenário mais simples sem ativos vinculados, **When** o usuário cria o risco, **Then** o
   sistema exige a entrada manual do impacto (não há CIA de onde derivar) e segue calculando o nível.

---

### User Story 2 - Identificar ameaças e vulnerabilidades e vinculá-las a ativos (Fase 1) (Priority: P2)

Um consultor adota o catálogo-semente de ameaças e de vulnerabilidades da plataforma (baseado em
ISO/IEC 27005, conteúdo PT-BR original), cria itens próprios da organização, arquiva logicamente os
que não se aplicam, e vincula ameaças e vulnerabilidades aos ativos do módulo de Ativos — preenchendo
as seções "Ameaças vinculadas" e "Vulnerabilidades vinculadas" da tela de detalhe do ativo. Quando
aplicável, uma vulnerabilidade pode referenciar um gap/controle ausente do catálogo de Gap da própria
organização.

**Why this priority**: É a Fase 1 da esteira e a matéria-prima dos cenários de risco da US1. Entregue
sozinha, já produz catálogos de ameaças e vulnerabilidades adotados e vinculados aos ativos, com valor
de inventário. Tem prioridade logo abaixo da US1 porque a US1 pode operar com o catálogo-semente
mínimo; a gestão completa do catálogo (custom/arquivar/vínculos) agrega profundidade.

**Independent Test**: Com uma organização autenticada, adotar o catálogo-semente (idempotente), criar
uma ameaça e uma vulnerabilidade próprias, arquivar um item, vincular ameaça e vulnerabilidade a um
ativo e confirmar que os vínculos aparecem na tela de detalhe do ativo; re-executar a adoção e
confirmar que não há duplicação nem perda de personalização.

**Acceptance Scenarios**:

1. **Given** uma organização sem catálogo adotado, **When** o usuário adota o catálogo-semente de
   ameaças e vulnerabilidades, **Then** o sistema cria a cópia editável da organização a partir da
   semente compartilhada, preservando o vínculo com a semente de origem.
2. **Given** um catálogo já adotado e personalizado, **When** o usuário re-executa a adoção, **Then** a
   operação é aditiva e idempotente: novos itens da semente são incluídos, personalizações são
   preservadas e nada é duplicado.
3. **Given** o catálogo da organização, **When** o usuário cria uma ameaça própria informando nome,
   descrição e categoria/origem (ex.: humana, ambiental, técnica; deliberada/acidental), **Then** o
   item é persistido como item da organização.
4. **Given** um item de catálogo, **When** o usuário o arquiva, **Then** o sistema exige justificativa e
   marca o item como arquivado sem removê-lo fisicamente; itens arquivados não aparecem por padrão na
   seleção de cenários.
5. **Given** uma ameaça e uma vulnerabilidade do catálogo e um ativo, **When** o usuário vincula a
   ameaça e a vulnerabilidade ao ativo, **Then** os vínculos passam a aparecer nas seções "Ameaças
   vinculadas" e "Vulnerabilidades vinculadas" da tela de detalhe do ativo.
6. **Given** uma vulnerabilidade, **When** o usuário a relaciona a um gap/controle ausente do catálogo
   de Gap da própria organização, **Then** o sistema registra a referência ao gap na vulnerabilidade.

---

### User Story 3 - Planejar o tratamento dos riscos e alimentar a SoA (Fase 3 — cláusula 6.1.3) (Priority: P3)

Para cada risco, o usuário escolhe a opção de tratamento (mitigar / aceitar / transferir / evitar).
Quando "mitigar", seleciona um ou mais controles do Anexo A a partir do catálogo de Gap da própria
organização (A.5–A.8), com prazo e responsável por controle (e a possibilidade de controle adicional/
custom). Em seguida re-pontua probabilidade e impacto (mesma metodologia 5x5) para obter o risco
residual; o sistema compara inerente × residual e sinaliza se o residual atende ao critério de
aceitação. Riscos "aceitos" exigem justificativa e aceitação do dono do risco. O Plano de Tratamento
consolidado é um artefato aprovável e versionável (Documento Controlado), aprovado pelo Admin
(assinatura avançada opcional). A seleção de controles fica disponível como insumo da SoA definitiva
(vínculo controle ← risco), sem finalizar a SoA neste módulo.

**Why this priority**: É a Fase 3 e o que transforma a avaliação em decisão e plano (6.1.3), além de
produzir o insumo da SoA. Depende de existirem riscos avaliados (US1), por isso vem depois.

**Independent Test**: Com riscos avaliados, definir tratamento "mitigar" com pelo menos um controle do
catálogo de Gap da org (com responsável e prazo), re-pontuar prob/impacto e confirmar o nível residual
e a sinalização frente ao critério; aceitar um risco com justificativa e aceitação do dono; consolidar,
submeter e aprovar o Plano de Tratamento como versão imutável; confirmar que cada controle selecionado
expõe o vínculo controle ← risco e a razão "tratamento de risco" para consumo futuro da SoA, sem que a
SoA seja reescrita aqui.

**Acceptance Scenarios**:

1. **Given** um risco avaliado, **When** o usuário escolhe a opção de tratamento "mitigar", **Then** o
   sistema exige a seleção de ao menos um controle (do catálogo de Gap da org ou custom) com
   responsável e prazo.
2. **Given** um tratamento "mitigar" com controles selecionados, **When** o usuário re-pontua
   probabilidade e impacto, **Then** o sistema calcula o nível residual pela metodologia, compara
   inerente × residual e sinaliza se o residual atende ao critério de aceitação.
3. **Given** um risco cuja opção de tratamento é "aceitar", **When** o usuário registra a aceitação,
   **Then** o sistema exige justificativa e a aceitação do dono do risco e registra a aceitação do
   risco residual (autor, data, justificativa).
4. **Given** riscos avaliados, **When** o usuário consolida e submete o Plano de Tratamento e o Admin o
   aprova, **Then** o sistema cria uma versão imutável do plano (Documento Controlado), com assinatura
   avançada opcional, e marca o plano como em vigor.
5. **Given** o plano ainda contém riscos não avaliados, **When** o Admin tenta aprová-lo, **Then** o
   sistema bloqueia a aprovação (gate duro a jusante) com mensagem clara indicando as pendências.
6. **Given** um controle selecionado no tratamento de um risco, **When** o usuário consulta o vínculo,
   **Then** o sistema expõe a associação controle ← risco e a razão de aplicabilidade "tratamento de
   risco" (com os riscos tratados) como insumo da SoA definitiva, sem finalizar nem reescrever a SoA.
7. **Given** um controle de tratamento que referencia um item do catálogo de Gap da org, **When** o
   usuário abre o controle, **Then** o sistema mostra a vinculação ao item correspondente do Anexo A
   (A.5–A.8) da própria organização.

---

### User Story 4 - Configurar a metodologia de risco da organização (cláusula 6.1.2 a) (Priority: P4)

Um administrador define a metodologia de risco da organização: escala de probabilidade (5 níveis,
rótulos + ordem), escala de impacto (5 níveis, rótulos + ordem), a matriz de combinação
probabilidade × impacto → nível de risco (faixas de severidade/cor), o critério de aceitação por nível
de risco e o conceito de dono do risco. O módulo já vem com um default de matriz qualitativa 5x5
consistente, de modo que avaliar risco sem metodologia explicitamente definida apenas avisa e usa o
default (pré-requisito "suave").

**Why this priority**: Garante uma metodologia consistente e repetível (exigência da 6.1.2 a), mas como
existe um default 5x5 que cobre o MVP, a personalização é um refinamento e não bloqueia a US1.

**Independent Test**: Com uma organização autenticada, abrir a configuração da metodologia, alterar
rótulos das escalas, ajustar a matriz e o critério de aceitação, salvar e confirmar que novos riscos
passam a calcular nível e aceitação conforme a configuração; sem nenhuma configuração, confirmar que o
sistema avisa e aplica o default 5x5.

**Acceptance Scenarios**:

1. **Given** uma organização sem metodologia configurada, **When** o usuário avalia um risco, **Then** o
   sistema avisa que está usando a metodologia padrão 5x5 e calcula normalmente (sem bloquear).
2. **Given** a tela de metodologia, **When** o administrador edita rótulos/ordem das escalas de
   probabilidade e impacto (5 níveis cada), **Then** o sistema persiste a configuração da organização.
3. **Given** a tela de metodologia, **When** o administrador define a matriz probabilidade × impacto →
   nível e o critério de aceitação por nível (ex.: aceitar automaticamente riscos ≤ "médio"), **Then** o
   sistema passa a usar essa configuração no cálculo de nível e na marcação de aceitação.
4. **Given** riscos já avaliados, **When** a metodologia (matriz/critério) é alterada, **Then** o sistema
   recalcula o nível e a marcação de aceitação a partir da probabilidade e impacto já registrados e
   sinaliza os riscos cuja classificação mudou, sem apagar o histórico.
5. **Given** o conceito de dono do risco, **When** o administrador o configura, **Then** o dono é
   sempre uma referência a um membro da organização.

---

### User Story 5 - Acompanhar o módulo pelo dashboard de riscos e pela esteira (Priority: P5)

Um gestor abre o dashboard do módulo de riscos e vê o heat map 5x5 (distribuição por probabilidade ×
impacto), a distribuição por nível, os top riscos (acima do critério de aceitação), riscos sem
tratamento, riscos aceitos, riscos por ativo e por dono, e a comparação agregada inerente × residual.
O Dashboard de Conformidade (esteira) reflete o readiness deste módulo (status, próxima ação,
bloqueios), reaproveitando a camada de agregação já existente.

**Why this priority**: Transforma o registro em ferramenta de gestão e priorização e conecta o módulo à
esteira guiada. Depende de existirem riscos (US1) e, idealmente, tratamentos (US3) para a comparação
inerente × residual.

**Independent Test**: Com riscos avaliados e ao menos alguns tratados, abrir o dashboard de riscos e
verificar que o heat map, as distribuições e os recortes (top riscos, sem tratamento, aceitos, por
ativo, por dono, inerente × residual) refletem corretamente os dados do tenant ativo; abrir o Dashboard
de Conformidade e verificar que o card do módulo de riscos mostra status, próxima ação e bloqueios.

**Acceptance Scenarios**:

1. **Given** riscos avaliados, **When** o usuário abre o dashboard de riscos, **Then** o heat map 5x5
   exibe a contagem de riscos por célula probabilidade × impacto, colorida pelo nível.
2. **Given** riscos com diferentes níveis e status, **When** o dashboard é consultado, **Then** ele
   apresenta distribuição por nível, top riscos acima do critério, riscos sem tratamento, riscos aceitos,
   riscos por ativo e por dono.
3. **Given** riscos com tratamento e residual definidos, **When** o dashboard é consultado, **Then** ele
   apresenta a comparação agregada inerente × residual.
4. **Given** o Dashboard de Conformidade (esteira), **When** o usuário o consulta, **Then** o card do
   módulo de riscos reflete o readiness (status, progresso, próxima ação e bloqueios), reaproveitando a
   camada de agregação existente, e respeita a permissão de visualização do módulo.

---

### User Story 6 - Histórico, rastreabilidade e auditoria das decisões de risco (Priority: P6)

Um responsável por compliance precisa confiar que toda decisão relevante de risco fica registrada de
forma append-only: criação/edição de risco, mudança de probabilidade/impacto/nível, troca de dono,
decisão de tratamento, seleção de controle, aceitação de risco e aprovação do plano — cada registro com
usuário, data, campo, valor anterior e novo, e justificativa quando aplicável.

**Why this priority**: É o que dá valor de auditoria e defensabilidade às decisões de risco (exigência
da ISO). Depende das fases existirem, mas não é pré-requisito para o primeiro registro funcionar.

**Independent Test**: Alterar probabilidade/impacto, trocar o dono, decidir um tratamento, selecionar um
controle, aceitar um risco e aprovar o plano; confirmar que cada operação gera registro de histórico com
autor, data, valor anterior e novo, exigindo justificativa nas mudanças relevantes (aceitação, mudança
de nível, aprovação); confirmar que nenhum registro anterior pode ser editado ou apagado.

**Acceptance Scenarios**:

1. **Given** um risco existente, **When** o usuário altera probabilidade, impacto, nível, dono ou status,
   **Then** o sistema cria um registro de histórico com usuário, data/hora, campo alterado, valor
   anterior e novo valor.
2. **Given** uma mudança relevante (aceitação de risco, mudança de nível, decisão de tratamento,
   aprovação do plano), **When** o usuário a confirma, **Then** o sistema exige e registra a justificativa.
3. **Given** o histórico de um risco, **When** o usuário o consulta, **Then** os registros aparecem em
   ordem cronológica e nenhum registro anterior pode ser editado ou apagado (trilha append-only).
4. **Given** a aprovação de um Plano de Tratamento, **When** ela ocorre, **Then** o evento é auditado e a
   versão imutável do plano preserva autor, data e ação.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler, listar, editar, arquivar,
   avaliar, tratar ou inferir um risco, um item de catálogo de ameaça/vulnerabilidade da org, um
   vínculo (ameaça/vuln ↔ ativo, vuln ↔ gap, controle ↔ risco), uma configuração de metodologia, um
   plano de tratamento ou um histórico que pertence à Organização B, **Then** o sistema nega (404/403
   sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da Organização
   A, **Then** apenas riscos, catálogos, vínculos, metodologia, planos e históricos da Organização A são
   visíveis e manipuláveis.
3. **Given** um Super Admin da plataforma, **When** ele acessa dados de risco de uma organização, **Then**
   o acesso exige contexto explícito de organização, é auditado e não lista dados de múltiplos tenants em
   uma única visão operacional.
4. **Given** um cenário de risco, **When** ele referencia ativos, ameaças, vulnerabilidades ou controles,
   **Then** o sistema só permite referenciar itens do **mesmo tenant** (catálogos da própria org,
   ativos da própria org, gaps da própria org), bloqueando referências cross-tenant.
5. **Given** os catálogos-semente de ameaças e vulnerabilidades (conteúdo de plataforma, sem tenant),
   **When** uma organização os adota, **Then** a cópia adotada é tenant-scoped e a semente permanece
   somente-leitura e compartilhada, sem vazar personalizações entre organizações.

### Edge Cases

- **Metodologia ausente**: avaliar risco sem metodologia definida apenas avisa e usa o default 5x5
  (gate suave); nunca bloqueia a avaliação por falta de configuração.
- **Cenário sem ativos** (cenário simples): não há CIA de onde derivar o impacto; o sistema exige a
  entrada manual de impacto e segue calculando o nível.
- **Ativo com CIA incompleta**: se um ativo vinculado não tem C, I e A completos, o sistema avisa e
  permite informar o impacto manualmente (não deriva de classificação incompleta).
- **Override de impacto vs. CIA**: se a CIA do ativo mudar depois de um override manual de impacto, o
  sistema sinaliza divergência entre o impacto derivado e o ajustado e permite recalcular ou manter.
- **Mudança de metodologia com riscos existentes**: o nível e a marcação de aceitação são recalculados a
  partir da prob/impacto já registrados; riscos cuja classificação mudou são sinalizados para revisão;
  o histórico não é apagado.
- **Residual pior que o inerente**: permitido (re-pontuação livre), mas o sistema sinaliza o aumento e
  destaca que o tratamento não reduziu o risco.
- **Residual ainda acima do critério**: permitido; o sistema sinaliza que o risco residual não atende ao
  critério de aceitação e o lista como "risco residual pendente".
- **Mitigar sem controle**: bloqueado — tratamento "mitigar" exige ao menos um controle com responsável
  e prazo.
- **Aceitar risco acima do critério**: permitido, mas exige justificativa e aceitação explícita do dono
  do risco (registro de aceitação do risco residual).
- **Ativo, ameaça, vulnerabilidade ou gap vinculado arquivado/descontinuado**: o vínculo e o risco
  permanecem rastreáveis; o sistema indica a indisponibilidade do alvo sem quebrar a tela.
- **Aprovação do plano com riscos não avaliados**: bloqueada (gate duro a jusante) com mensagem clara;
  rascunhar e navegar continuam livres (gate suave).
- **Exclusão física**: não permitida; somente arquivamento lógico com justificativa, tanto de itens de
  catálogo quanto de riscos.
- **Organização (tenant) suspensa**: leitura e escrita de riscos, catálogos, metodologia e planos ficam
  bloqueadas, preservando os registros existentes.
- **Re-adoção do catálogo-semente**: aditiva e idempotente; itens novos entram, personalizações e itens
  próprios da org são preservados, nada é duplicado.

## Requirements *(mandatory)*

### Functional Requirements

**Metodologia de risco (configuração — cláusula 6.1.2 a)**

- **FR-001**: O sistema MUST oferecer, por organização, uma configuração de metodologia de risco
  consistente e repetível, com um **default de matriz qualitativa 5x5** já funcional.
- **FR-002**: A metodologia MUST permitir configurar a escala de **probabilidade** com 5 níveis
  (rótulos + ordem) e a escala de **impacto** com 5 níveis (rótulos + ordem).
- **FR-003**: A metodologia MUST permitir configurar a **matriz** de combinação probabilidade × impacto
  → **nível de risco**, com faixas de severidade/cor (ex.: Baixo, Médio, Alto, Crítico).
- **FR-004**: A metodologia MUST permitir configurar o **critério de aceitação por nível** de risco
  (ex.: aceitar automaticamente riscos ≤ "médio"), usado para marcar cada risco como acima/abaixo do
  critério.
- **FR-005**: A metodologia MUST tratar o **dono do risco** como referência a um **membro da
  organização**.
- **FR-006**: A metodologia é um pré-requisito **suave**: avaliar risco sem metodologia explicitamente
  definida MUST apenas avisar e usar o default 5x5, sem bloquear a avaliação.
- **FR-007**: O sistema MUST NOT incluir, no MVP, apetite/critério de aceitação **por categoria** (C vs.
  I vs. D) — isso é refinamento futuro.
- **FR-008**: Ao alterar a metodologia (matriz/critério), o sistema MUST recalcular o nível e a marcação
  de aceitação dos riscos existentes a partir da probabilidade e impacto já registrados e MUST sinalizar
  os riscos cuja classificação mudou, sem apagar o histórico.

**Fase 1 — Catálogo de ameaças e vulnerabilidades**

- **FR-009**: O sistema MUST fornecer um **catálogo-semente** de ameaças e um de vulnerabilidades como
  **conteúdo de plataforma compartilhado** (sem `tenant_id`, somente leitura), com base de referência
  ISO/IEC 27005 e **conteúdo PT-BR original** (sem reproduzir texto normativo).
- **FR-010**: O sistema MUST permitir que a organização **adote** os catálogos-semente, criando uma
  **cópia editável por organização** (tenant-scoped). A adoção MUST ser **aditiva e idempotente**:
  re-executar inclui itens novos, preserva personalizações e não duplica.
- **FR-011**: Cada **ameaça** MUST suportar ao menos: nome, descrição e categoria/origem (ex.: humana,
  ambiental, técnica; deliberada/acidental). Cada **vulnerabilidade** MUST suportar ao menos: nome,
  descrição e categoria.
- **FR-012**: O sistema MUST permitir **criar itens próprios** da organização (ameaças e
  vulnerabilidades) e **arquivar logicamente** itens (com justificativa), sem exclusão física; itens
  arquivados não aparecem por padrão na seleção de cenários.
- **FR-013**: O sistema MUST permitir **vincular** ameaças e vulnerabilidades a **ativos** do módulo de
  Ativos da mesma organização, e exibir esses vínculos nas seções "Ameaças vinculadas" e
  "Vulnerabilidades vinculadas" da tela de detalhe do ativo.
- **FR-014**: O sistema MUST permitir que uma **vulnerabilidade** referencie um **gap/controle ausente**
  do catálogo de **Gap da própria organização**, quando aplicável.

**Fase 2 — Avaliação de riscos (cláusula 6.1.2)**

- **FR-015**: O sistema MUST permitir registrar um risco como **cenário** composto por um ou mais
  **ativos** + uma **ameaça** + uma **vulnerabilidade**, admitindo cenários mais simples (ex.: sem
  ativos) quando aplicável.
- **FR-016**: O sistema MUST gerar automaticamente um **identificador interno** único na organização
  para cada risco (ex.: prefixo + sequência, como RSK-0001), exibido na listagem e no detalhe.
- **FR-017**: Cada risco MUST suportar ao menos: identificador interno, título, descrição, ativos
  relacionados, ameaça, vulnerabilidade, probabilidade, impacto, nível inerente, dono do risco
  (membro), status (ex.: identificado / avaliado / em tratamento / aceito / encerrado), datas e
  responsáveis de criação/atualização e justificativas das mudanças relevantes.
- **FR-018**: O sistema MUST **derivar o impacto inerente** a partir da **classificação CIA** do(s)
  ativo(s) vinculado(s) — por padrão o **maior valor entre C, I e A** — mapeada para a escala de impacto
  da metodologia, e MUST permitir **override manual** do impacto **registrado e justificado** (autor,
  data, valor anterior e novo).
- **FR-019**: O sistema MUST calcular o **nível de risco inerente** via matriz da metodologia
  (probabilidade × impacto) e marcar se o risco está **acima ou abaixo do critério de aceitação**.
- **FR-020**: O Registro de Riscos MUST ser **listável** com filtros (ex.: nível, status, dono, ativo,
  ameaça, vulnerabilidade, acima/abaixo do critério, com/sem tratamento, aceitos) e **busca textual**
  (título, descrição).
- **FR-021**: O sistema MUST oferecer uma visão de **matriz / heat map 5x5**, distribuindo os riscos nas
  células probabilidade × impacto, coloridas pelo nível.

**Fase 3 — Plano de tratamento (cláusula 6.1.3)**

- **FR-022**: Para cada risco, o sistema MUST permitir escolher a **opção de tratamento**: **mitigar**,
  **aceitar**, **transferir** ou **evitar**.
- **FR-023**: Quando "mitigar", o sistema MUST permitir **selecionar um ou mais controles do Anexo A** a
  partir do **catálogo de Gap da própria organização** (controles A.5–A.8), **com prazo e responsável por
  controle**, e MUST permitir adicionar **controle adicional/custom**.
- **FR-024**: Após definir o tratamento, o sistema MUST permitir **re-pontuar probabilidade e impacto**
  (mesma metodologia 5x5) para obter o **nível residual**, MUST comparar **inerente × residual** e MUST
  sinalizar se o residual **atende ao critério de aceitação**.
- **FR-025**: Riscos cuja opção é **aceitar** MUST exigir **justificativa de aceitação** e o registro da
  **aceitação atribuída ao dono do risco**, gravando a **aceitação do risco residual** (membro-dono,
  usuário que registrou, data, justificativa). A aceitação é registrada por um usuário autorizado
  (`manage_risk`) em nome do dono; não há fluxo separado de login/assinatura do dono no MVP.
- **FR-026**: O **Plano de Tratamento consolidado** MUST ser um artefato **aprovável e versionável**,
  reutilizando o mecanismo de **Documento Controlado / versão-baseline** já existente, com **aprovação
  pelo Admin** e **assinatura avançada opcional** (reusando o motor existente).
- **FR-027**: A aprovação do Plano de Tratamento MUST aplicar **gate duro a jusante**: aprovar exige
  riscos **avaliados** (probabilidade, impacto e dono presentes); o sistema MUST bloquear a aprovação
  com riscos pendentes e indicar as pendências.
- **FR-028**: A **versão** do Plano de Tratamento MUST ser **imutável** (snapshot do conteúdo) e
  preservar autor, data e ação, em trilha append-only.

**Integração com a SoA (alimentar, não finalizar)**

- **FR-029**: Cada controle selecionado no tratamento MUST produzir e expor um **vínculo controle ←
  risco** (somente leitura), associando o controle à razão de aplicabilidade **"tratamento de risco"** e
  aos **riscos tratados**, como **insumo da SoA definitiva**. Esse vínculo é **derivado/consultável** a
  partir deste módulo; o módulo **MUST NOT gravar nem mutar** itens/registros da SoA.
- **FR-030**: Esta feature MUST NOT **finalizar, gravar nem reescrever a SoA**; ela apenas produz e expõe
  o vínculo controle ← risco e a razão de aplicabilidade, deixando a base pronta para a futura feature de
  **finalização da SoA**, que será a única responsável por escrever os itens da SoA. O SoA atual MUST ser
  tratado como **Catálogo de Controles / Pré-SoA**.

**Integração com Ativos e Gap**

- **FR-031**: O módulo MUST **preencher os placeholders existentes na tela de detalhe do ativo**
  ("Ameaças vinculadas", "Vulnerabilidades vinculadas", "Riscos vinculados", "Controles relacionados")
  com os vínculos reais criados aqui.
- **FR-032**: Os controles de tratamento MUST referenciar itens do **Anexo A do catálogo de Gap da
  própria organização** (não o catálogo-base de plataforma).
- **FR-033**: Os cenários de risco MUST referenciar **ativos** da própria organização; o módulo MUST NOT
  alterar o modelo de Ativos além de consumir e exibir os vínculos nos placeholders já existentes.

**Esteira guiada e gates**

- **FR-034**: O sistema MUST aplicar **gates suaves por padrão**: o usuário pode navegar, explorar e
  rascunhar qualquer fase a qualquer momento; quando um pré-requisito não está pronto (ex.: metodologia
  ausente, sem ativos, sem tratamento), o sistema **avisa** e **deixa seguir**.
- **FR-035**: O sistema MUST aplicar **gate duro apenas na aprovação/congelação do artefato a jusante**
  (aprovar o Plano de Tratamento exige riscos avaliados); a finalização da SoA (feature futura) exigirá
  tratamento aprovado.
- **FR-036**: A esteira MUST continuar exibindo as três fases (Ameaças/Vulnerabilidades → Avaliação →
  Tratamento) como **passos distintos**, ainda que sejam um único módulo de engenharia.
- **FR-037**: O **Dashboard de Conformidade** (esteira) MUST refletir o **readiness** deste módulo
  (status, próxima ação, bloqueios), reaproveitando a **camada de agregação já existente**.

**Dashboard do módulo de riscos**

- **FR-038**: O módulo MUST oferecer um dashboard com, no mínimo: **heat map 5x5** (distribuição por
  probabilidade × impacto), **distribuição por nível**, **top riscos** (acima do critério de aceitação),
  **riscos sem tratamento**, **riscos aceitos**, **riscos por ativo** e **por dono**, e **comparação
  agregada inerente × residual**. Cards e tabelas simples bastam.

**Histórico, rastreabilidade e auditoria**

- **FR-039**: O sistema MUST registrar **histórico append-only** de: criação/edição de risco, mudança de
  probabilidade/impacto/nível, troca de dono, decisão de tratamento, seleção de controle, aceitação de
  risco e aprovação do plano — cada registro com usuário, data, campo, valor anterior, novo valor e
  justificativa quando aplicável.
- **FR-040**: O sistema MUST exigir **justificativa** nas mudanças relevantes (aceitação de risco,
  mudança de nível e aprovação do plano) e MUST NOT permitir essas operações sem justificativa.
- **FR-041**: O histórico MUST ser **append-only**: registros anteriores não podem ser editados nem
  apagados.

**Validações mínimas**

- **FR-042**: O sistema MUST validar que **título e descrição** são obrigatórios no risco, e que
  **ameaça e vulnerabilidade** são obrigatórias no cenário.
- **FR-043**: Um risco **avaliado / dentro do escopo de avaliação** MUST exigir **probabilidade,
  impacto e dono**.
- **FR-044**: O tratamento **"mitigar"** MUST exigir ao menos **um controle com responsável e prazo**.
- **FR-045**: O risco **"aceito"** MUST exigir **justificativa** e **aceitação do dono**.
- **FR-046**: O sistema MUST NOT permitir exclusão física; somente **arquivamento lógico com
  justificativa** (itens de catálogo e riscos).

**Preparação para relatórios PDF e assinatura (sem implementar agora)**

- **FR-047**: Os dados MUST ser organizados para permitir, em feature futura, a geração dos relatórios:
  **Registro de Riscos**, **Matriz/Heat map**, **Plano de Tratamento**, **Riscos Aceitos** e **Riscos
  Residuais Pendentes**. A **assinatura eletrônica** MUST NOT ser implementada nesta etapa, exceto a
  **assinatura avançada opcional** já prevista na aprovação do Plano de Tratamento (FR-026), reusando o
  motor existente.

**Restrições de escopo**

- **FR-048**: A feature MUST NOT implementar a **SoA definitiva**, **análise quantitativa** (Monte Carlo,
  valor monetário), **fórmula de eficácia de controle** (o residual é re-pontuação simples), **scanners/
  automação** de coleta de ameaças/vulnerabilidades, nem **workflow pesado de aprovação** além do
  Documento Controlado já existente.

**Terminologia e usabilidade**

- **FR-049**: A interface MUST usar terminologia clara para consultores e PMEs (ex.: "Ameaças",
  "Vulnerabilidades", "Risco", "Probabilidade", "Impacto", "Nível de risco", "Critério de aceitação",
  "Dono do risco", "Tratamento", "Mitigar/Aceitar/Transferir/Evitar", "Risco residual", "Plano de
  Tratamento"), evitando linguagem excessivamente técnica.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado desta feature é escopado pela organização do usuário.
  Recursos afetados: configuração de metodologia de risco, cópia da organização dos catálogos de
  ameaças e vulnerabilidades, vínculos (ameaça/vuln ↔ ativo, vuln ↔ gap), risco/cenário, tratamento,
  controle selecionado (vínculo controle ← risco), plano de tratamento (e versões) e histórico de
  risco. Acesso cross-tenant ⇒ 404/403 sem revelar existência + audit log. Cenários, vínculos e
  controles só podem referenciar itens do **mesmo tenant** (ativos, catálogos e gaps da própria org).
  Os **catálogos-semente** de ameaças/vulnerabilidades são **conteúdo de plataforma sem `tenant_id`**
  (somente leitura); a cópia adotada é tenant-scoped.
- **SEC-002 (Papéis e permissões)**: Leitura (listar riscos, ver detalhe, dashboard, heat map,
  consultar catálogos/metodologia) exige uma permissão de **visualização** do módulo (ex.: `view_risk`);
  criar/editar risco, avaliar, adotar/editar catálogo, vincular ameaças/vulnerabilidades, definir
  tratamento, selecionar controle, configurar metodologia, aceitar risco e consolidar plano exigem uma
  permissão de **gestão** (ex.: `manage_risk`); a **aprovação do Plano de Tratamento** exige uma
  permissão de aprovação do **Admin da organização** (ex.: `approve_risk_plan`), no mesmo padrão de
  `approve_gap_baseline`/`approve_soa`. A **edição do catálogo-semente** (conteúdo de plataforma) é
  restrita ao **Super Admin** (sem contexto de org), no mesmo padrão da orientação do Gap. Distribuição
  sugerida: Super Admin, Admin da organização e Consultor gerem; Gestor, Dono de processo, Dono de
  controle, Auditor interno e Cliente visualizam; Colaborador convidado não acessa. Super Admin só atua
  com contexto explícito de organização e é auditado.
- **SEC-003 (Auditoria)**: Geram audit log: criação/edição de risco, mudança de probabilidade/impacto/
  nível, override de impacto, troca de dono, decisão de tratamento, seleção/remoção de controle,
  aceitação de risco, consolidação e aprovação do plano, adoção/edição/arquivamento de catálogo,
  vínculo/desvínculo (ameaça/vuln ↔ ativo, vuln ↔ gap, controle ← risco), alteração de metodologia e
  tentativas não autorizadas ou cross-tenant. Cada registro grava operação, tipo de entidade,
  identificador da entidade, usuário e organização, e **nunca** PII, dados sensíveis ou conteúdo
  confidencial. Apenas listar/visualizar não gera audit log por si só (à exceção de tentativas
  não autorizadas).
- **SEC-004 (Dados sensíveis)**: A feature **não** armazena PII bruta. Descrições de risco, justificativas
  e observações são texto livre que MUST NOT conter PII bruta e não devem ser expostas em logs, erros ou
  auditoria. **No MVP não há cifragem em nível de campo** (mesma decisão do módulo de Ativos): a proteção
  se dá por **RBAC + isolamento de tenant + regra "sem PII bruta"**. A adoção de cifragem em repouso de
  campos específicos pode ser reavaliada em feature futura.
- **SEC-005 (Evidências/versionamento)**: A feature cria/altera artefatos versionáveis: o **Plano de
  Tratamento** (Documento Controlado com versão imutável/baseline e assinatura avançada opcional) e o
  **histórico append-only** de cada risco. Ambos preservam autor, data e ação; versões e registros
  anteriores não são editados nem apagados. O arquivamento (de catálogo e de riscos) é lógico e não
  destrói histórico.
- **SEC-006 (Degradação)**: Falha em infra externa (ex.: e-mail/OTP da assinatura opcional, storage) não
  deve impedir o cadastro, a avaliação e a consulta de riscos; ações dependentes de infra indisponível
  falham com mensagem clara (fail-closed apenas na ação afetada — ex.: a assinatura avançada do plano).
  Isolamento de tenant é **sempre** fail-closed.

### Key Entities *(include if feature involves data)*

- **Configuração de Metodologia de Risco**: Por organização (`tenant_id`), define a escala de
  probabilidade (5 níveis: rótulos + ordem), a escala de impacto (5 níveis: rótulos + ordem), a matriz
  probabilidade × impacto → nível de risco (faixas de severidade/cor) e o critério de aceitação por
  nível. Possui um default 5x5. Uma configuração por organização.
- **Catálogo-semente de Ameaças / de Vulnerabilidades (plataforma)**: Conteúdo compartilhado, **sem
  `tenant_id`**, somente leitura (base ISO/IEC 27005, PT-BR original). Editável apenas pelo Super Admin.
- **Ameaça da Organização / Vulnerabilidade da Organização**: Cópia editável por organização
  (`tenant_id`) derivada da semente (com vínculo à semente de origem) ou criada como item próprio.
  Ameaça: nome, descrição, categoria/origem. Vulnerabilidade: nome, descrição, categoria, referência
  opcional a gap/controle ausente do catálogo de Gap da org. Suporta arquivamento lógico.
- **Vínculo Ameaça↔Ativo / Vulnerabilidade↔Ativo**: Associação tenant-scoped entre um item de catálogo e
  um ativo do módulo de Ativos da mesma organização; alimenta os placeholders do detalhe do ativo.
- **Risco (Cenário)**: Registro central (`tenant_id`). Identificador interno automático, título,
  descrição, ativos relacionados, ameaça, vulnerabilidade, probabilidade, impacto (derivado da CIA ou
  override justificado), nível inerente, dono (membro), status, e — após o tratamento — probabilidade/
  impacto/nível **residual**. Marca se está acima/abaixo do critério de aceitação. Suporta arquivamento
  lógico.
- **Tratamento do Risco**: Opção (mitigar/aceitar/transferir/evitar) associada ao risco, com a
  re-pontuação residual e, quando "aceitar", o registro de aceitação (justificativa + aceitação do dono).
- **Controle Selecionado no Tratamento (vínculo controle ← risco)**: Associa um risco a um controle do
  Anexo A do **catálogo de Gap da própria organização** (A.5–A.8) ou a um controle custom, com
  responsável e prazo. É o **insumo da SoA** (razão de aplicabilidade "tratamento de risco" + riscos
  tratados), exposto sem finalizar a SoA.
- **Plano de Tratamento de Riscos (artefato versionável)**: Documento Controlado consolidando os
  tratamentos, aprovável pelo Admin (assinatura avançada opcional), com versão imutável/baseline
  (reusa o mecanismo existente).
- **Histórico/Evento de Risco**: Registro append-only de cada alteração/decisão relevante (usuário,
  data/hora, campo, valor anterior, novo valor, justificativa quando aplicável). Pertence à Organization
  via `tenant_id`.
- **Dono do Risco / Responsáveis**: Referenciam **membros da organização** (usuários com vínculo no
  tenant), selecionados por seletor de membros (mesmo padrão dos demais módulos), sustentando os recortes
  "riscos por dono" e o filtro por dono.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário autorizado consegue registrar e avaliar um risco completo (cenário +
  probabilidade + impacto + dono, com nível e marcação de aceitação calculados) em menos de 5 minutos.
- **SC-002**: 100% dos riscos com ativos vinculados e CIA completa têm o impacto inerente derivado
  corretamente da CIA (maior valor entre C, I e A) quando não há override; 100% dos overrides de impacto
  registram justificativa, autor e data.
- **SC-003**: 100% dos riscos recebem identificador interno único na organização, sem colisões.
- **SC-004**: O nível inerente e a marcação acima/abaixo do critério de aceitação correspondem à matriz e
  ao critério da metodologia vigente em 100% dos casos de teste; ao mudar a metodologia, 100% dos riscos
  são recalculados a partir da prob/impacto registrados e os que mudaram de classificação são sinalizados.
- **SC-005**: A adoção do catálogo-semente é aditiva e idempotente: re-executar não duplica itens nem
  perde personalizações em 100% dos casos de teste.
- **SC-006**: 100% dos vínculos de ameaças, vulnerabilidades, riscos e controles aparecem corretamente
  nas seções correspondentes da tela de detalhe do ativo; nenhuma referência cross-tenant é permitida.
- **SC-007**: 100% dos tratamentos "mitigar" salvos têm ao menos um controle com responsável e prazo;
  100% dos riscos "aceitos" têm justificativa e aceitação do dono registradas.
- **SC-008**: Para 100% dos riscos tratados, o sistema calcula o nível residual e sinaliza corretamente se
  o residual atende ou não ao critério de aceitação, e expõe a comparação inerente × residual.
- **SC-009**: 100% dos controles selecionados no tratamento expõem o vínculo controle ← risco e a razão
  "tratamento de risco" como insumo da SoA, sem que a SoA seja finalizada ou reescrita por este módulo.
- **SC-010**: A aprovação do Plano de Tratamento é bloqueada (gate duro) em 100% dos casos em que existem
  riscos não avaliados, e gera uma versão imutável quando aprovada; navegar e rascunhar nunca são
  bloqueados (gates suaves).
- **SC-011**: 100% das decisões relevantes (criação/edição de risco, mudança de prob/impacto/nível, troca
  de dono, decisão de tratamento, seleção de controle, aceitação, aprovação do plano) geram registro de
  histórico append-only com autor, data, valor anterior e novo; mudanças relevantes registram
  justificativa.
- **SC-012**: O heat map 5x5 e cada distribuição/recorte do dashboard (por nível, top riscos, sem
  tratamento, aceitos, por ativo, por dono, inerente × residual) refletem corretamente os dados do tenant
  ativo em 100% dos casos de teste; o card do módulo na esteira reflete o readiness correto.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar metodologia, catálogo da org,
  vínculo, risco, tratamento, controle selecionado, plano ou histórico de uma organização à qual não
  pertence — verificado por teste automatizado de isolamento de tenant.

## Assumptions

- A feature reutiliza a **fundação multi-tenant**, autenticação, RBAC, `tenant_scope`, audit log e o
  padrão de **trilha append-only** já existentes; reutiliza o **Documento Controlado / versão-baseline**
  (novo tipo de documento para o Plano de Tratamento) e o **motor de assinatura avançada opcional**.
- O padrão **catálogo-semente compartilhado (plataforma) + cópia editável por org (tenant)** segue o já
  adotado no Gap Analysis (adoção aditiva/idempotente); a edição da semente é restrita ao Super Admin,
  no mesmo padrão da orientação do Gap.
- **Impacto inerente derivado da CIA** (definido na clarificação 2026-06-26): por padrão usa o **maior
  valor entre C, I e A** (`max(C,I,A)`) dos ativos vinculados, mapeado para a escala de impacto de 5
  níveis da metodologia por uma **tabela de mapeamento configurável com default** (a CIA do módulo de
  Ativos tem 4 níveis — Baixa < Média < Alta < Crítica — e a escala de impacto tem 5; o mapeamento
  default é decisão de planejamento). O **override** manual é sempre permitido com justificativa
  registrada. A avaliação **por dimensão** (C/I/D separadas) é **refinamento futuro** — coerente com o
  adiamento do apetite por categoria.
- **Cenário simples** (definido na clarificação 2026-06-26): ameaça e vulnerabilidade são
  **obrigatórias** no cenário; os **ativos são opcionais** (0..n). Sem ativos, o impacto é informado
  manualmente (não há CIA de onde derivar).
- O **identificador interno** do risco usa prefixo + número sequencial por organização (ex.: RSK-0001),
  único no tenant e imutável após a criação; o prefixo exato é decisão de planejamento.
- Os **controles de tratamento** referenciam o **catálogo de Gap da própria organização** (cópia
  editável por tenant), não o catálogo-base de plataforma; controles custom são suportados.
- O **vínculo controle ← risco** e a razão de aplicabilidade "tratamento de risco" são **produzidos e
  expostos** por este módulo (reusando os campos forward-compatible já existentes na SoA: razão de
  inclusão "tratamento de risco" e "riscos tratados"), mas a **SoA não é finalizada nem reescrita** aqui.
- A **aceitação do dono do risco** (definida na clarificação 2026-06-26) é registrada por um usuário
  autorizado (`manage_risk`) atribuindo a decisão ao membro indicado como dono, com justificativa, em
  trilha append-only; não há, no MVP, um fluxo separado de "login do dono para aprovar" nem
  atribuição/assinatura via Motor de Workflow.
- O **default 5x5** cobre o MVP; a metodologia personalizada é um refinamento que não bloqueia a
  avaliação (gate suave).
- O **Dashboard de Conformidade** (esteira) é estendido reaproveitando a **camada de agregação já
  existente** para refletir o readiness do módulo de riscos (status, próxima ação, bloqueios), sem novo
  modelo de agregação.
- Os **relatórios em PDF** (Registro de Riscos, Matriz/Heat map, Plano de Tratamento, Riscos Aceitos,
  Riscos Residuais Pendentes) são **preparados estruturalmente** mas implementados em feature futura,
  reutilizando o motor de documentos imprimíveis/assináveis já existente; a única assinatura prevista
  nesta etapa é a **assinatura avançada opcional na aprovação do Plano de Tratamento**.
- O **SoA atual** é tratado como **Catálogo de Controles / Pré-SoA** e não é fonte primária deste módulo.
- O módulo de **Ativos** não é alterado além do consumo/exibição dos vínculos nos placeholders já
  existentes ("Ameaças vinculadas", "Vulnerabilidades vinculadas", "Riscos vinculados", "Controles
  relacionados").
