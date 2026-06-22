# Feature Specification: Orientação de Avaliação por Item (Gap Analysis)

**Feature Branch**: `007-gap-item-guidance`

**Created**: 2026-06-22

**Status**: Draft

**Input**: Enriquecer cada item da matriz do Gap Analysis (7 cláusulas 4–10 + 93 controles do Anexo A)
com orientação de avaliação estruturada em português (referência, objetivo, como avaliar, evidências
esperadas, nota), mais uma legenda global das escalas de Status e Prioridade. Conteúdo canônico da
plataforma, somente leitura para a organização e editável por administrador da plataforma.

---

## Visão Geral

Hoje cada item da matriz do Gap Analysis exibe apenas o código de referência e o nome. Avaliar
"Atende / Atende Parcialmente / Não atende / N/A" sem orientação gera **subjetividade** e depende do
conhecimento de cada avaliador. Esta feature adiciona, por item, uma **orientação de avaliação**
(referência, objetivo, como avaliar, evidências esperadas e uma nota opcional) e, na tela, uma
**legenda global** das escalas de Status e Prioridade. Essa orientação é **conteúdo canônico da
plataforma** (igual para todas as organizações), exibida em **somente leitura** para quem avalia, e
**editável apenas por um administrador da plataforma** (Super Admin), com trilha append-only e
auditoria. Não altera o fluxo de avaliação existente — apenas o enriquece.

---

## Clarifications

### Session 2026-06-22

- Q: Como o catálogo de uma organização (já adotado) resolve a orientação canônica? → A: **Por
  vínculo ao item do seed (join)** — a orientação fica **somente no item base do catálogo
  compartilhado** e a matriz da organização a resolve por referência (`seed_item_id`/`ref_code`),
  **sem duplicar** conteúdo. Edição do administrador reflete em todas as organizações
  automaticamente. (Pode exigir garantir o vínculo `seed_item_id` no item do catálogo da organização.)
- Q: Forma dos campos `como_avaliar` e `evidencias_esperadas`? → A: **Lista de strings** (itens
  curtos) — cada pergunta/evidência é um item simples, renderizado como bullets; sem objetos ricos.
- Q: Escopo de conteúdo no MVP? → A: **Todos os 100 itens** — orientação autoral em PT-BR para os 93
  controles do Anexo A + as 7 cláusulas (4–10), entregue por tema (A.5/A.6/A.7/A.8 + cláusulas).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Avaliar um item com orientação ao lado (Priority: P1)

Quem conduz o Gap Analysis seleciona um controle na matriz e vê, no painel lateral, a orientação de
avaliação daquele item: o objetivo do controle, perguntas práticas de "como avaliar" e exemplos de
evidências esperadas — tudo em português, antes de registrar o status. Isso reduz a dúvida sobre o
que cada item exige.

**Why this priority**: É o valor central da feature — torna a avaliação mais consistente e menos
dependente de especialista. Sem isso, o item continua "código + nome".

**Independent Test**: Com o catálogo adotado e a orientação populada, selecionar um controle (ex.:
A.8.24) exibe referência, objetivo, lista de "como avaliar" e lista de "evidências esperadas", sem
alterar os campos de avaliação (status, constatações, etc.).

**Acceptance Scenarios**:

1. **Given** a organização tem o catálogo do Gap adotado e a orientação da plataforma populada,
   **When** o avaliador seleciona um item na matriz, **Then** o painel exibe a orientação daquele
   item (referência, objetivo, como avaliar, evidências esperadas e nota, quando houver), em
   **somente leitura**.
2. **Given** um item ainda não possui orientação cadastrada (ex.: item personalizado criado pela
   organização, sem correspondência no catálogo da plataforma), **When** o avaliador o seleciona,
   **Then** o painel indica "sem orientação disponível" sem erro e sem bloquear a avaliação.
3. **Given** o avaliador está vendo a orientação, **When** ele edita os campos de avaliação do item
   (status, constatações, ações), **Then** a orientação permanece inalterável por ele (read-only) e
   o salvamento da avaliação funciona normalmente.

---

### User Story 2 — Administrar (editar) a orientação da plataforma (Priority: P2)

O administrador da plataforma acessa uma área administrativa e edita os textos de orientação de um
item (objetivo, como avaliar, evidências esperadas, nota, referência) e os textos da legenda global.
Cada alteração é registrada (quem, quando, valor anterior → novo) e passa a valer **para todas as
organizações**.

**Why this priority**: É como o conteúdo é mantido e evolui ao longo do tempo (correções, melhorias,
novos exemplos). O conteúdo inicial pode vir pré-carregado, mas a curadoria contínua exige esta
capacidade.

**Independent Test**: Autenticado como administrador da plataforma, editar o "objetivo" de um item;
o novo texto aparece na matriz de qualquer organização; o histórico mostra o valor anterior e o novo,
com autor e data.

**Acceptance Scenarios**:

1. **Given** um administrador da plataforma, **When** ele edita um campo de orientação de um item e
   salva, **Then** a alteração é persistida, registrada em trilha append-only (autor, data, valor
   anterior → novo) e auditada, e passa a ser exibida em **todas** as organizações.
2. **Given** um usuário **sem** privilégio de plataforma (incluindo Admin de organização), **When**
   ele tenta acessar/editar a orientação pela via administrativa, **Then** o sistema nega (403) e
   registra a tentativa em audit log.
3. **Given** o administrador edita a legenda global de Status, **When** salva, **Then** a nova
   definição é exibida na tela para todas as organizações.

---

### User Story 3 — Entender as escalas pela legenda global (Priority: P3)

O avaliador consulta, na tela do Gap, uma **legenda** que define objetivamente cada nível de Status
(Não atende / Atende Parcialmente / Atende Totalmente / Não Aplicável) e de Prioridade (Crítica /
Alta / Média / Baixa), para classificar de forma consistente.

**Why this priority**: Reduz subjetividade de forma barata e transversal, mas é complementar ao
conteúdo por item (US1).

**Independent Test**: Abrir a tela do Gap e visualizar a legenda com as 4 definições de Status e as 4
de Prioridade.

**Acceptance Scenarios**:

1. **Given** o avaliador na tela do Gap, **When** ele abre a legenda, **Then** vê as definições de
   cada nível de Status e de Prioridade, em português.

---

### Tenant Isolation Scenarios *(mandatory)*

> **Nota de design:** a orientação e a legenda são **conteúdo de plataforma compartilhado**
> (intencionalmente iguais para todas as organizações) — **não** são dado de uma organização. O
> isolamento aqui protege (a) o acesso de **edição** (só plataforma) e (b) garante que nenhum
> endpoint desta feature exponha ou altere dado de **avaliação** de uma organização.

1. **Given** um usuário autenticado de qualquer organização (papel não-plataforma), **When** ele
   tenta editar a orientação ou a legenda pela via administrativa, **Then** o sistema nega (403) e
   registra a tentativa — edição é exclusiva do administrador da plataforma.
2. **Given** o administrador da plataforma edita a orientação, **When** a edição ocorre, **Then** a
   operação **não** tem contexto de organização e **não** lê nem altera nenhum dado de avaliação de
   qualquer organização (apenas o conteúdo canônico compartilhado).
3. **Given** um usuário da Organização A, **When** ele lê a matriz, **Then** vê a mesma orientação
   canônica que a Organização B, porém **nenhum** dado de avaliação da Organização B é exposto por
   esta feature (os dados de avaliação por item permanecem isolados por tenant, como no Módulo 2).

### Edge Cases

- **Item sem orientação**: item personalizado da organização (sem correspondência no catálogo da
  plataforma) ⇒ painel mostra "sem orientação disponível", sem erro.
- **Organização que adotou o catálogo antes da orientação existir**: passa a ver a orientação assim
  que ela for populada na plataforma, **sem precisar readotar** o catálogo.
- **Edição concorrente** por administradores: a trilha registra todas as alterações; o valor corrente
  reflete a última gravação (last-write-wins), com histórico preservado.
- **Campo de lista vazio** (sem perguntas de "como avaliar" ou sem "evidências esperadas"): a seção
  correspondente é omitida no painel, sem placeholder vazio.
- **Item descontinuado** no catálogo: a orientação acompanha o item; itens descontinuados seguem o
  comportamento já existente do Módulo 2.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir associar, a cada item do catálogo da plataforma (cláusulas 4–10
  e 93 controles do Anexo A), uma **orientação de avaliação** com os campos: **referência** (rótulo
  factual), **objetivo** (texto curto), **como avaliar** (**lista de strings** — perguntas curtas),
  **evidências esperadas** (**lista de strings**) e **nota** (texto opcional). As listas são itens
  simples (sem objetos/atributos por item), renderizadas como tópicos.
- **FR-002**: Ao selecionar um item na matriz, o sistema MUST exibir a orientação correspondente em
  **somente leitura** para o usuário da organização, sem alterar o fluxo nem os campos de avaliação.
- **FR-003**: A orientação MUST cobrir os 93 controles do Anexo A e as 7 cláusulas (4–10); itens sem
  orientação cadastrada MUST ser tratados graciosamente ("sem orientação disponível").
- **FR-004**: O sistema MUST exibir uma **legenda global** com as definições de cada nível de
  **Status** (Não atende / Atende Parcialmente / Atende Totalmente / Não Aplicável) e de
  **Prioridade** (Crítica / Alta / Média / Baixa).
- **FR-005**: A orientação e a legenda são **conteúdo canônico da plataforma** — uma alteração vale
  para **todas** as organizações; nenhuma organização edita esse conteúdo neste escopo. A matriz da
  organização resolve a orientação **por vínculo ao item base do catálogo compartilhado** (não há
  cópia da orientação no item da organização), de modo que edições propagam sem readoção.
- **FR-006**: Apenas um **administrador da plataforma** MUST poder editar os textos de orientação e
  da legenda, por uma área administrativa, **sem** contexto de organização.
- **FR-007**: Toda edição de orientação/legenda MUST registrar uma entrada em **trilha append-only**
  contendo autor, data e **valor anterior → novo**, e MUST gerar **audit log**.
- **FR-008**: A leitura da orientação/legenda **não** gera audit log (é consulta de conteúdo de
  referência), mas **tentativas de edição não autorizadas** MUST ser auditadas.
- **FR-009**: O sistema MUST distinguir claramente **"evidência existente"** (o que a organização já
  registrou para o item — dado da organização, já existente no Módulo 2) de **"evidências
  esperadas"** (orientação canônica do que comprovaria o controle).
- **FR-010**: O painel da matriz MUST ser estruturado para acomodar, em feature seguinte, uma seção
  de **evidências anexadas** por item (sem implementá-la agora).
- **FR-011**: Todos os textos de orientação e legenda MUST ser **originais em português**; o sistema
  **MUST NOT** reproduzir o texto normativo da ISO/IEC 27001 nem a guidance da ISO/IEC 27002
  (restrição de direito autoral). É permitido usar apenas códigos e títulos curtos dos controles.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: A orientação e a legenda são **conteúdo de plataforma
  compartilhado** (sem vínculo a uma organização) — por design, iguais para todos os tenants. Nenhum
  endpoint desta feature lê, lista ou altera **dado de avaliação** de uma organização. Os dados de
  avaliação por item (status, constatações, etc.) permanecem escopados por tenant pelo Módulo 2 e
  **não** são tocados aqui. Acesso de **edição** por não-plataforma ⇒ **403** + audit.
- **SEC-002 (Papéis e permissões)**: **Leitura** da orientação/legenda: qualquer papel que já enxerga
  a matriz do Gap (permissão `view_gap`). **Edição**: exclusivamente o **Super Admin da plataforma**
  (operação de plataforma, sem contexto de organização). Opcional futuro: permissão dedicada de
  curadoria de conteúdo separada do Super Admin.
- **SEC-003 (Auditoria)**: Operações que geram audit log: **edição** de orientação e de legenda
  (operação, ator, entidade/identificador do item ou da legenda) e **tentativas de edição negadas**.
  Registros **nunca** incluem PII/dado sensível — o conteúdo de orientação é texto de referência
  genérico. As ações do Super Admin são especialmente logadas.
- **SEC-004 (Dados sensíveis)**: Não trata PII nem dado confidencial de cliente. O conteúdo é
  orientação genérica de avaliação. Não requer cifragem em repouso.
- **SEC-005 (Evidências/versionamento)**: A orientação **não** é um documento controlado versionado
  (como SoA); seu valor corrente é mutável in-place pela plataforma. A **rastreabilidade** é garantida
  por **trilha append-only** (autor/data/antes→novo), que nunca é editada ou apagada.
- **SEC-006 (Degradação)**: Sem dependências de infra externa nesta feature. Indisponibilidade da
  orientação (ex.: conteúdo ainda não populado) **não** bloqueia a avaliação — a matriz opera com
  "sem orientação disponível".

### Key Entities *(include if feature involves data)*

> A orientação é **conteúdo de plataforma** (sem `tenant_id`), espelhando a natureza já compartilhada
> do catálogo-base do Gap (Módulo 2). Os dados de avaliação por organização permanecem como no
> Módulo 2 (com `tenant_id`).

- **Orientação do item (plataforma)**: estende o item do **catálogo-base compartilhado** do Gap com
  os campos de orientação (referência, objetivo, **como avaliar [lista de strings]**, **evidências
  esperadas [lista de strings]**, nota). Sem `tenant_id`. Exibida na matriz da organização por
  **vínculo** do item do catálogo da organização ao item base correspondente (via `seed_item_id`/
  `ref_code`) — **sem cópia** da orientação no item da organização.
- **Legenda global (plataforma)**: definições textuais das escalas de Status e de Prioridade. Sem
  `tenant_id`. Conteúdo único da plataforma.
- **Trilha de edição da orientação (append-only, plataforma)**: registra cada alteração de orientação
  ou legenda — autor (administrador da plataforma), data, campo, valor anterior → novo. Imutável.
- **Avaliação do item (organização — já existente, Módulo 2)**: status, constatações, ações,
  prioridade, responsável, prazo, **evidência existente**, justificativa de exclusão, observações —
  com `tenant_id`. **Não alterado** por esta feature, apenas referenciado para distinguir "evidência
  existente" de "evidências esperadas".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em 100% dos itens com orientação cadastrada, o avaliador vê referência, objetivo, "como
  avaliar" e "evidências esperadas" ao selecionar o item — verificável abrindo qualquer item populado.
- **SC-002**: A orientação cobre os **93 controles do Anexo A** e as **7 cláusulas** (4–10) — 100% de
  cobertura do catálogo base.
- **SC-003**: Uma edição feita por administrador da plataforma passa a ser exibida para **qualquer**
  organização sem nenhuma ação da organização (sem readoção de catálogo).
- **SC-004**: 100% das edições de orientação/legenda ficam registradas com autor, data e valor
  anterior → novo, recuperáveis no histórico.
- **SC-005**: A avaliação de itens continua funcionando mesmo quando a orientação não está disponível
  para um item (degradação graciosa), sem erro.
- **SC-ISO (mandatory)**: Nenhum usuário sem privilégio de plataforma consegue editar a orientação ou
  a legenda (resposta 403 + auditada), e nenhum endpoint desta feature expõe dado de avaliação de uma
  organização à qual o usuário não pertence — verificado por teste automatizado.

## Assumptions

- O conteúdo inicial de orientação dos 93 controles + 7 cláusulas será **autorado originalmente em
  português** e pré-carregado no catálogo base (paráfrase própria; sem reprodução do texto normativo).
- A orientação reside no **catálogo-base compartilhado** do Gap (mesma natureza sem `tenant_id` já
  usada no Módulo 2) e é resolvida para a matriz da organização por **vínculo** do item adotado ao
  item base (`seed_item_id`/`ref_code`), sem duplicar o conteúdo por organização. Se o item do
  catálogo da organização ainda não guardar esse vínculo, o /plan deve garanti-lo (ex.: backfill por
  `ref_code`).
- O "administrador da plataforma" é o **Super Admin** já existente (único papel cross-tenant); a
  edição é uma operação de plataforma, sem `X-Org-Context`.
- A legenda global é conteúdo de plataforma; sua personalização por organização está **fora de
  escopo** (deferida).
- Reusa a fundação multi-tenant (auth + RBAC + auditoria) e o Módulo 2 (Gap Analysis) já implementados;
  os campos de avaliação por item (incluindo "evidência existente") já existem e não são alterados.
- "Evidências esperadas" (orientação) é a contraparte das **evidências anexadas** da feature seguinte
  (Módulo de Evidências); aqui apenas se prepara o terreno (FR-010), sem anexar arquivos.
