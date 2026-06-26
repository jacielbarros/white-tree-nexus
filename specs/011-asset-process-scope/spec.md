# Feature Specification: Gestão de Ativos / Processos / Escopo do SGSI

**Feature Branch**: `011-asset-process-scope`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "Especificar e implementar o Módulo 3 — Gestão de Ativos / Processos / Escopo: registrar, classificar, organizar e manter ativos, processos e elementos de escopo do SGSI, servindo de base para os próximos módulos de ameaças, vulnerabilidades, riscos, plano de tratamento, SoA e evidências."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Esta feature toca
  dados de domínio ⇒ DEVE especificar isolamento de tenant, auditoria e tratamento de dados
  sensíveis. Sem stack/tecnologia aqui (isso é do /speckit.plan).
-->

## Clarifications

### Session 2026-06-26

- Q: Como Responsável, Dono e Custodiante devem ser representados em cada item? → A: Referência a membros da organização (usuários com vínculo no tenant), via seletor de membros; custodiantes/donos que não são usuários do sistema são representados como item do tipo "pessoa/equipe" e ligados por relacionamento.
- Q: Qual o escopo da integração com o Gap Analysis nesta feature? → A: Implementar o vínculo item→gap e exibir "Gaps relacionados" na tela de detalhe do item; a exibição reversa (ativos/processos na tela do Gap) fica deferida para feature futura e o módulo Gap não é alterado nesta feature.
- Q: Como proteger os campos potencialmente sensíveis (observações LGPD/compliance, indicadores de dados pessoais/sensíveis) no MVP? → A: Sem cifragem de campo no MVP; proteção por RBAC + isolamento de tenant + regra "sem PII bruta nas observações"; campos armazenados em texto, preservando a busca textual sobre observações.
- Q: Qual o formato e a regra de numeração do código interno automático? → A: Prefixo derivado do tipo + número sequencial por tipo dentro da organização (ex.: ATV-0001, ATV-0002, PROC-0001), único no tenant; o código é imutável após a criação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inventariar e classificar ativos e processos do SGSI (Priority: P1)

Um consultor ou administrador da organização cadastra os ativos, sistemas, bases de dados,
processos de negócio, fornecedores, pessoas/equipes, infraestrutura, documentos críticos e
serviços relevantes ao SGSI. Para cada item informa tipo, descrição, área, responsáveis e a
classificação de Confidencialidade, Integridade e Disponibilidade (CIA), e indica se o item está
dentro, fora ou em análise no escopo do SGSI. O sistema gera um código interno automático, calcula
a criticidade a partir da CIA (permitindo ajuste manual registrado) e aplica as regras de
obrigatoriedade conforme a situação de escopo.

**Why this priority**: É o valor central do módulo e a base de todos os próximos (ameaças,
vulnerabilidades, riscos, tratamento, SoA, evidências). Sem o inventário classificado e escopado
não há sobre o que avaliar risco nem declarar aplicabilidade. Entregue sozinho, já produz um
inventário de ativos e processos utilizável e exportável conceitualmente.

**Independent Test**: Com uma organização autenticada, cadastrar itens de diferentes tipos,
classificá-los por CIA, marcar a situação de escopo e confirmar que as validações condicionais
(responsável e CIA obrigatórios dentro do escopo; justificativa obrigatória fora do escopo) são
aplicadas e que cada item recebe código interno único na organização.

**Acceptance Scenarios**:

1. **Given** um usuário autorizado na tela de Ativos e Processos, **When** ele cria um item
   informando nome e tipo válidos, **Then** o sistema persiste o item, gera um código interno
   automático único na organização e registra criação no histórico.
2. **Given** um item marcado como "dentro do escopo", **When** o usuário tenta salvar sem
   responsável ou sem a classificação completa de C, I e A, **Then** o sistema recusa com mensagem
   clara indicando os campos obrigatórios pendentes.
3. **Given** um item marcado como "fora do escopo", **When** o usuário tenta salvar sem
   justificativa de exclusão, **Then** o sistema recusa com mensagem clara exigindo a justificativa.
4. **Given** um item com C=Alta, I=Média e A=Baixa, **When** o usuário não informa criticidade
   manual, **Then** o sistema calcula a criticidade geral como "Alta" (maior valor entre C, I e A).
5. **Given** um item com criticidade calculada automaticamente, **When** o usuário sobrescreve a
   criticidade manualmente, **Then** o sistema preserva o valor ajustado e registra que houve ajuste
   manual (com autor e data).
6. **Given** um item existente, **When** o usuário solicita arquivamento, **Then** o sistema exige
   justificativa e, ao confirmar, marca o item como arquivado sem removê-lo fisicamente.
7. **Given** já existe um item com determinado nome dentro de um tipo, **When** o usuário tenta
   criar outro item com o mesmo nome e mesmo tipo, **Then** o sistema sinaliza a possível
   duplicidade e só permite prosseguir com identificador distinto ou justificativa.

---

### User Story 2 - Visão de gestão: listagem com filtros, busca e dashboard do módulo (Priority: P2)

Um gestor abre a página do módulo e vê, no topo, cards de resumo (total de itens, ativos, processos,
fornecedores/terceiros, itens dentro do escopo, itens críticos, itens sem responsável, itens sem
classificação CIA completa) e, abaixo, uma listagem com filtros e busca textual que permite localizar
rapidamente itens por tipo, situação de escopo, criticidade, classificação CIA, presença de dados
pessoais/sensíveis, situação de revisão e pendências de governança.

**Why this priority**: Sem visão consolidada e filtros, o inventário cresce e perde utilidade
gerencial. Esta história transforma o cadastro em ferramenta de acompanhamento e priorização e
sustenta a futura geração de relatórios.

**Independent Test**: Com itens previamente cadastrados, abrir a página do módulo e verificar que os
cards refletem as contagens corretas e que cada filtro e a busca textual retornam exatamente o
subconjunto esperado, somente do tenant ativo.

**Acceptance Scenarios**:

1. **Given** itens cadastrados de vários tipos e situações de escopo, **When** o usuário abre a
   página do módulo, **Then** os cards de resumo exibem as contagens corretas (total, ativos,
   processos, fornecedores, dentro do escopo, críticos, sem responsável, sem CIA completa).
2. **Given** a listagem carregada, **When** o usuário aplica um ou mais filtros (ex.: tipo +
   criticidade + situação de escopo), **Then** a tabela mostra apenas os itens que satisfazem todos
   os filtros selecionados.
3. **Given** a listagem carregada, **When** o usuário busca por um termo, **Then** o sistema retorna
   itens cujo nome, descrição, área, responsável ou observações contenham o termo.
4. **Given** filtros de pendência (sem responsável, sem CIA completa, revisão vencida), **When**
   aplicados, **Then** a listagem mostra somente itens com a respectiva pendência.
5. **Given** um dashboard do módulo, **When** o usuário o consulta, **Then** ele apresenta ao menos
   distribuição por tipo, por criticidade, por situação de escopo, itens com dados pessoais, itens
   críticos sem revisão, itens sem responsável e itens por situação de revisão.

---

### User Story 3 - Tela de detalhe, relacionamentos entre itens e vínculo com gaps (Priority: P3)

Ao abrir um item, o usuário vê uma tela de detalhe com dados gerais, classificação CIA, escopo,
responsáveis e seções para relacionar o item a outros itens (ex.: um processo utiliza um sistema; um
sistema armazena uma base de dados) e para vincular o item a gaps já existentes do Gap Analysis. A
tela também exibe seções preparadas (placeholder) para ameaças, vulnerabilidades, riscos, controles
e evidências, que serão preenchidas nos módulos seguintes.

**Why this priority**: Os relacionamentos e o vínculo com gaps são o que torna o inventário um mapa
do SGSI e não apenas uma lista. Preparam a rastreabilidade ponta a ponta exigida pelos próximos
módulos, mas dependem de US1 já existir.

**Independent Test**: Com dois itens e ao menos um gap existentes, criar um relacionamento direcional
entre os itens e vincular um item a um gap; confirmar que o relacionamento aparece nas telas de
detalhe de ambos os itens e que o gap vinculado aparece na tela de detalhe do item.

**Acceptance Scenarios**:

1. **Given** dois itens cadastrados, **When** o usuário cria um relacionamento informando item de
   origem, tipo de relacionamento, item de destino e descrição opcional, **Then** o relacionamento é
   registrado e exibido na tela de detalhe de ambos os itens (saída na origem e entrada no destino).
2. **Given** um item e um gap existentes, **When** o usuário vincula o item ao gap, **Then** o gap
   passa a aparecer na seção "Gaps relacionados" da tela de detalhe do item.
3. **Given** um item vinculado a um gap, **When** o usuário gerencia o vínculo a partir da tela do
   item, **Then** ele pode adicionar e remover o vínculo, sem que a tela do Gap Analysis seja alterada
   nesta feature (exibição reversa de ativos na tela do Gap é deferida).
4. **Given** a tela de detalhe de um item, **When** o usuário a abre, **Then** as seções "Ameaças
   vinculadas", "Vulnerabilidades vinculadas", "Riscos vinculados", "Controles relacionados" e
   "Evidências" são exibidas como placeholders indicando que serão preenchidas nos módulos seguintes.
5. **Given** um relacionamento ou vínculo a gap, **When** o item de origem ou destino é arquivado,
   **Then** o relacionamento permanece rastreável e o sistema indica que um dos lados está arquivado.

---

### User Story 4 - Histórico, rastreabilidade e revisão periódica (Priority: P4)

Um responsável por compliance precisa confiar que toda alteração relevante (escopo, criticidade,
responsável, arquivamento) fica registrada com autor, data, valor anterior e novo valor, e exige
justificativa quando crítica. Cada item tem data de última revisão e próxima revisão, e o sistema
classifica e permite filtrar a situação de revisão (em dia, próxima do vencimento, vencida, não
definida).

**Why this priority**: É o que dá valor de auditoria e governança ao inventário ao longo do tempo.
Depende do cadastro (US1) e complementa a visão de gestão (US2), mas não é pré-requisito para o
primeiro inventário funcionar.

**Independent Test**: Alterar a situação de escopo, a criticidade e o responsável de um item e
confirmar que cada alteração gera registro de histórico com autor, data, valor anterior e novo valor,
exigindo justificativa nas alterações marcadas como críticas; definir datas de revisão e confirmar
que a situação de revisão é derivada e filtrável corretamente.

**Acceptance Scenarios**:

1. **Given** um item existente, **When** o usuário altera escopo, criticidade ou responsável,
   **Then** o sistema cria um registro de histórico com usuário, data/hora, campo alterado, valor
   anterior e novo valor.
2. **Given** uma alteração crítica (exclusão de escopo, mudança de criticidade ou arquivamento),
   **When** o usuário confirma, **Then** o sistema exige e registra a justificativa da alteração.
3. **Given** um item com próxima revisão definida no passado, **When** a listagem é consultada,
   **Then** o item aparece com situação de revisão "vencida" e pode ser isolado por filtro.
4. **Given** um item sem próxima revisão definida, **When** a listagem é consultada, **Then** o item
   aparece com situação "não definida" e pode ser isolado por filtro.
5. **Given** o histórico de um item, **When** o usuário o consulta, **Then** os registros são exibidos
   em ordem cronológica e nenhum registro anterior pode ser editado ou apagado (trilha append-only).

---

### User Story 5 - Criar item a partir da Análise de Contexto (Priority: P5)

Para evitar redigitação, o usuário pode iniciar o cadastro de um item aproveitando informações já
registradas na Análise de Contexto (escopo preliminar, áreas internas, partes interessadas,
requisitos, processos e sistemas citados), por meio de uma ação de "criar item a partir do contexto"
que pré-preenche os campos compatíveis.

**Why this priority**: É um acelerador de produtividade que reforça a coerência entre a Cláusula 4 e
o inventário, mas o módulo é plenamente utilizável sem ele (cadastro manual cobre o MVP).

**Independent Test**: Com uma Análise de Contexto preenchida, acionar "criar item a partir do
contexto", escolher um elemento de origem (ex.: uma área ou um processo citado) e confirmar que o
formulário de novo item é pré-preenchido com os campos compatíveis, restando ao usuário completar e
salvar.

**Acceptance Scenarios**:

1. **Given** uma Análise de Contexto com áreas/processos/partes registrados, **When** o usuário aciona
   "criar item a partir do contexto", **Then** o sistema oferece os elementos de contexto compatíveis
   como ponto de partida para um novo item.
2. **Given** um elemento de contexto selecionado, **When** o usuário confirma, **Then** o formulário de
   novo item é pré-preenchido com os campos compatíveis (ex.: nome/área/descrição) e segue exigindo as
   validações de US1 antes de salvar.
3. **Given** a Análise de Contexto não está preenchida ou não há elementos compatíveis, **When** o
   usuário aciona a ação, **Then** o sistema informa claramente a ausência de origem e mantém o
   cadastro manual disponível.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler, listar, editar,
   arquivar, relacionar ou inferir um item de ativo/processo, um relacionamento, um vínculo com gap
   ou um histórico que pertence à Organização B, **Then** o sistema nega (404/403 sem revelar
   existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas itens, relacionamentos, vínculos e históricos da Organização A são
   visíveis e manipuláveis.
3. **Given** um Super Admin da plataforma autenticado, **When** ele acessa itens de uma organização,
   **Then** o acesso exige contexto explícito de organização, respeita auditoria e não lista itens de
   múltiplos tenants em uma única visão operacional.
4. **Given** um relacionamento entre itens, **When** uma das pontas referencia outro tenant, **Then**
   o sistema impede a criação do relacionamento cross-tenant (apenas itens do mesmo tenant podem ser
   relacionados entre si).

### Edge Cases

- Item sem nenhum relacionamento, vínculo de gap ou histórico além da criação: telas mostram estados
  vazios claros sem bloquear o uso.
- Item "em análise" no escopo: o sistema destaca as pendências (responsável e/ou CIA ausentes) sem
  bloquear o salvamento, pois a situação ainda não está decidida.
- Mudança de situação de escopo: ao passar de "fora" para "dentro", o sistema passa a exigir
  responsável e CIA; ao passar para "fora", passa a exigir justificativa de exclusão.
- Criticidade calculada vs. ajustada: se a CIA mudar depois de um ajuste manual, o sistema sinaliza
  divergência entre a criticidade calculada e a ajustada e permite recalcular ou manter o ajuste.
- Tentativa de exclusão física: não é permitida no MVP; somente arquivamento lógico com justificativa.
- Duplicidade de nome no mesmo tipo: bloqueada salvo identificador distinto ou justificativa explícita.
- Item com dados pessoais/sensíveis: o módulo registra apenas os indicadores e observações de
  compliance, não o dado pessoal em si; observações não devem conter PII bruta.
- Organização (tenant) suspensa: leitura e escrita de itens ficam bloqueadas, preservando os
  registros existentes.
- Item de gap ou elemento de contexto vinculado deixa de existir/é arquivado: o vínculo permanece
  rastreável e o sistema indica a indisponibilidade do alvo sem quebrar a tela.
- Relacionamento de um item consigo mesmo: bloqueado (origem e destino devem ser itens distintos).

## Requirements *(mandatory)*

### Functional Requirements

**Cadastro, tipos e identificação**

- **FR-001**: O sistema MUST permitir cadastrar, visualizar, editar, listar e arquivar (logicamente)
  itens de ativo/processo/escopo de uma organização, sem exclusão física no MVP.
- **FR-002**: Cada item MUST ter um campo "tipo" com ao menos as opções: ativo de informação,
  sistema/aplicação, base de dados, processo de negócio, infraestrutura, serviço, fornecedor/terceiro,
  documento/política, pessoa/equipe, ambiente físico e outro.
- **FR-003**: O sistema MUST gerar automaticamente um código/identificador interno para cada item,
  no formato prefixo-derivado-do-tipo + número sequencial por tipo dentro da organização (ex.:
  ATV-0001, ATV-0002, PROC-0001), único no tenant e exibido na listagem e no detalhe. O código MUST
  ser imutável após a criação (não muda se o tipo do item for alterado depois).
- **FR-004**: Cada item MUST suportar ao menos os campos: nome, código interno, tipo, descrição,
  unidade/área relacionada, responsável, dono do ativo/processo, custodiante (quando aplicável),
  status do registro (ativo/em revisão/arquivado), situação de escopo, justificativa de inclusão ou
  exclusão de escopo, localização/ambiente (quando aplicável), referências a sistema/processo/
  fornecedor relacionados (quando aplicável), indicadores de dados pessoais e dados sensíveis,
  observações de LGPD/compliance, criticidade geral, classificação de Confidencialidade, Integridade
  e Disponibilidade, datas de criação, última revisão e próxima revisão, e autoria de criação e
  última atualização.

**Classificação CIA e criticidade**

- **FR-005**: O sistema MUST permitir classificar Confidencialidade, Integridade e Disponibilidade
  em quatro níveis: Baixa, Média, Alta e Crítica.
- **FR-006**: O sistema MUST calcular automaticamente a criticidade geral como o maior valor entre C,
  I e A, e MUST permitir ajuste manual da criticidade registrando que houve ajuste (autor e data).
- **FR-007**: O sistema MUST sinalizar quando a criticidade ajustada manualmente divergir da
  criticidade que seria calculada pela CIA corrente.

**Escopo do SGSI**

- **FR-008**: Cada item MUST poder ser marcado como "dentro do escopo", "fora do escopo" ou "em
  análise".
- **FR-009**: Quando o item estiver "fora do escopo", o sistema MUST exigir justificativa de exclusão.
- **FR-010**: Quando o item estiver "dentro do escopo", o sistema MUST exigir responsável e a
  classificação completa de C, I e A.
- **FR-011**: Quando o item estiver "em análise", o sistema MUST destacar as pendências (responsável
  e/ou CIA ausentes) sem bloquear o salvamento.
- **FR-012**: A marcação de escopo deste módulo MUST ser tratada como inventário operacional do
  escopo e MUST NOT substituir a Declaração de Escopo (Cláusula 4.3) do módulo de Contexto; ela a
  complementa.

**Relacionamentos entre itens**

- **FR-013**: O sistema MUST permitir relacionar dois itens entre si por meio de uma estrutura
  flexível com item de origem, tipo de relacionamento, item de destino e descrição opcional.
- **FR-014**: O sistema MUST oferecer ao menos os tipos de relacionamento: depende de, suporta,
  utiliza, armazena, processa, é responsável por, é operado por, é regulado por, está vinculado a,
  substitui e outro.
- **FR-015**: O sistema MUST exibir os relacionamentos de saída e de entrada na tela de detalhe dos
  itens envolvidos.
- **FR-016**: O sistema MUST impedir relacionar um item consigo mesmo e MUST impedir relacionamentos
  entre itens de tenants diferentes.

**Integração com Gap Analysis e Contexto**

- **FR-017**: O sistema MUST permitir vincular um item a um ou mais gaps existentes do Gap Analysis da
  mesma organização e exibir os gaps relacionados na tela de detalhe do item.
- **FR-018**: A exibição reversa dos ativos/processos relacionados na tela do Gap Analysis está
  **fora do escopo** desta feature (deferida para feature futura); esta feature MUST NOT alterar o
  módulo Gap Analysis. O vínculo é criado, consultado e removido a partir da tela do item.
- **FR-019**: O sistema MUST oferecer uma ação de "criar item a partir do contexto" que pré-preencha
  campos compatíveis a partir de elementos da Análise de Contexto (áreas, partes interessadas,
  requisitos, processos/sistemas citados, escopo preliminar) quando houver dados disponíveis.

**Preparação para módulos futuros**

- **FR-020**: A tela de detalhe MUST exibir seções preparadas (placeholder) para "Ameaças
  vinculadas", "Vulnerabilidades vinculadas", "Riscos vinculados", "Controles relacionados" e
  "Evidências", indicando que serão preenchidas nos módulos seguintes.
- **FR-021**: A modelagem MUST prever, sem implementar nesta feature, a futura vinculação de cada
  item a ameaças, vulnerabilidades, riscos, controles, evidências e plano de tratamento.
- **FR-022**: A feature MUST NOT implementar gestão de riscos, cálculo avançado de risco, SoA
  definitivo, CMDB avançado, scanner automático de ativos, assinatura eletrônica ou workflow pesado de
  aprovação neste escopo; o SoA existente MUST NOT ser usado como fonte principal deste módulo (é
  tratado como Catálogo de Controles / Pré-SoA).

**Histórico, rastreabilidade e revisão**

- **FR-023**: O sistema MUST registrar histórico de toda criação, edição, alteração de escopo,
  alteração de criticidade, alteração de responsável e arquivamento, gravando usuário, data/hora,
  campo alterado, valor anterior, novo valor e motivo quando aplicável.
- **FR-024**: O sistema MUST exigir justificativa em alterações relevantes (exclusão de escopo,
  mudança de criticidade e arquivamento) e MUST NOT permitir arquivamento sem justificativa.
- **FR-025**: O histórico MUST ser append-only: registros anteriores não podem ser editados nem
  apagados.
- **FR-026**: Cada item MUST manter data da última revisão e próxima revisão, e o sistema MUST derivar
  a situação de revisão em: em dia, próxima do vencimento, vencida e não definida.
- **FR-027**: A listagem MUST permitir filtrar itens por situação de revisão, incluindo revisão
  vencida e sem próxima revisão definida.

**Listagem, filtros, busca e dashboard**

- **FR-028**: A página principal MUST exibir cards de resumo com: total de itens, quantidade de
  ativos, de processos, de fornecedores/terceiros, de itens dentro do escopo, de itens críticos, de
  itens sem responsável e de itens sem classificação CIA completa.
- **FR-029**: A listagem MUST permitir filtrar por tipo, status do registro, situação de escopo
  (dentro/fora/em análise), responsável, criticidade, Confidencialidade, Integridade,
  Disponibilidade, presença de dados pessoais, presença de dados sensíveis, revisão vencida, sem
  responsável, sem classificação CIA completa e gaps relacionados.
- **FR-030**: A listagem MUST oferecer busca textual por nome, descrição, área, responsável e
  observações.
- **FR-031**: O módulo MUST oferecer um dashboard com, no mínimo: distribuição por tipo, distribuição
  por criticidade, itens dentro/fora/em análise no escopo, itens com dados pessoais, itens críticos
  sem revisão, itens sem responsável e itens por situação de revisão.

**Validações**

- **FR-032**: O sistema MUST validar que nome, tipo e situação de escopo são obrigatórios em todo item.
- **FR-033**: O sistema MUST impedir duplicidade de nome dentro do mesmo tipo na mesma organização,
  salvo quando houver identificador distinto ou justificativa explícita.

**Preparação para PDF e assinatura (sem implementar agora)**

- **FR-034**: Os dados MUST ser organizados de forma a permitir, em feature futura, a geração dos
  relatórios: Inventário de Ativos e Processos, Escopo Operacional do SGSI, Itens Críticos, Revisões
  Pendentes e Relacionamentos entre ativos/processos; a assinatura eletrônica MUST NOT ser
  implementada nesta etapa.

**Terminologia e usabilidade**

- **FR-035**: A interface MUST usar terminologia clara para consultores e PMEs (ex.: "Ativos e
  Processos", "Escopo do SGSI", "Responsável", "Criticidade", "Confidencialidade", "Integridade",
  "Disponibilidade", "Revisão", "Gaps relacionados", "Riscos vinculados"), evitando linguagem
  excessivamente técnica.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado desta feature é escopado pela organização do usuário.
  Recursos afetados: item de ativo/processo/escopo, relacionamento entre itens, vínculo item↔gap,
  vínculo/origem de contexto e registro de histórico do item. Acesso cross-tenant ⇒ 404/403 sem
  revelar existência + audit log. Relacionamentos só podem unir itens do mesmo tenant.
- **SEC-002 (Papéis e permissões)**: Leitura (listar, ver detalhe, dashboard, filtros) exige uma
  permissão de visualização do módulo (ex.: `view_asset`); criação, edição, classificação,
  marcação de escopo, relacionamento, vínculo com gap, definição de revisão e arquivamento exigem uma
  permissão de gestão do módulo (ex.: `manage_asset`). Distribuição inicial sugerida (alinhada ao
  padrão dos módulos existentes): Super Admin, Admin da organização e Consultor podem gerir; demais
  papéis vinculados (Gestor, Dono de processo, Dono de controle, Auditor interno, Cliente) visualizam;
  Colaborador convidado não acessa. Super Admin só atua com contexto explícito de organização e é
  auditado.
- **SEC-003 (Auditoria)**: Geram audit log: criação, edição, alteração de escopo, alteração de
  criticidade, alteração de responsável, arquivamento, criação/remoção de relacionamento, vínculo/
  desvínculo de gap, e tentativas não autorizadas ou cross-tenant. Cada registro grava operação,
  tipo de entidade, identificador da entidade, usuário e organização, e **nunca** PII, dados sensíveis
  ou conteúdo confidencial. Apenas listar itens/metadados não gera audit log por si só.
- **SEC-004 (Dados sensíveis)**: A feature trata indicadores e observações de privacidade
  (dados pessoais/sensíveis e observações de LGPD/compliance), mas **não** armazena o dado pessoal em
  si. Os indicadores são metadados de classificação; as observações de compliance são texto livre que
  MUST NOT conter PII bruta e não devem ser expostas em logs, erros ou auditoria. **No MVP não há
  cifragem em nível de campo**: a proteção dos campos potencialmente sensíveis se dá por RBAC +
  isolamento de tenant + a regra "sem PII bruta nas observações"; os campos são armazenados em texto
  para preservar a busca textual (FR-030). A adoção de cifragem em repouso de campos específicos pode
  ser reavaliada em feature futura caso a política de dados evolua.
- **SEC-005 (Evidências/versionamento)**: O histórico de alterações do item é o artefato versionável
  desta feature e é **append-only**, preservando autor, data, ação, valor anterior e novo valor;
  registros anteriores não são editados nem apagados por operações comuns. O arquivamento é lógico e
  reversível conforme política, sem destruir histórico.
- **SEC-006 (Degradação)**: Falha em infra externa (ex.: storage, e-mail) não deve impedir o cadastro
  e a consulta básica de itens; ações dependentes de infra indisponível falham com mensagem clara
  (fail-closed apenas na ação afetada). Isolamento de tenant é **sempre** fail-closed.

### Key Entities *(include if feature involves data)*

- **Item de Ativo/Processo/Escopo**: Registro central do módulo (ativo, sistema, base de dados,
  processo, infraestrutura, serviço, fornecedor, documento/política, pessoa/equipe, ambiente físico ou
  outro). Pertence a uma Organization via `tenant_id`. Carrega identificação (código interno, nome,
  tipo, descrição, área), responsáveis (responsável, dono, custodiante), situação de escopo +
  justificativa, classificação CIA + criticidade (calculada/ajustada), indicadores de dados pessoais/
  sensíveis + observações de compliance, status do registro e datas de criação/revisão.
- **Relacionamento entre Itens**: Associação direcional flexível (item de origem, tipo de
  relacionamento, item de destino, descrição opcional) entre dois itens do mesmo tenant. Suporta o
  mapa de dependências do SGSI.
- **Vínculo Item↔Gap**: Associação entre um item e um gap existente do Gap Analysis da mesma
  organização, evidenciando que o item endereça ou comprova o tratamento do gap.
- **Origem de Contexto (referência)**: Referência opcional ao elemento da Análise de Contexto que
  originou o item (para a ação "criar item a partir do contexto"), preservando coerência com a
  Cláusula 4.
- **Histórico/Evento do Item**: Registro append-only de cada alteração relevante (usuário, data/hora,
  campo alterado, valor anterior, valor novo, justificativa quando aplicável). Pertence à Organization
  via `tenant_id`.
- **Responsáveis (responsável/dono/custodiante)**: Referenciam membros da organização (usuários com
  vínculo no tenant), selecionados por seletor de membros, sustentando os KPIs de "sem responsável" e
  o filtro por responsável. Custodiantes/donos que não são usuários do sistema são representados como
  item do tipo "pessoa/equipe" e ligados por relacionamento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um usuário autorizado consegue cadastrar e classificar (CIA + escopo) um item completo
  em menos de 3 minutos.
- **SC-002**: 100% dos itens marcados "dentro do escopo" salvos possuem responsável e classificação
  CIA completa; 100% dos itens "fora do escopo" salvos possuem justificativa de exclusão.
- **SC-003**: 100% dos itens recebem código interno único dentro da organização, sem colisões.
- **SC-004**: A criticidade geral corresponde ao maior valor entre C, I e A em 100% dos itens sem
  ajuste manual; itens com ajuste manual exibem indicação de ajuste em 100% dos casos.
- **SC-005**: Os cards de resumo e cada filtro/busca retornam contagens e resultados corretos para o
  tenant ativo em 100% dos casos de teste.
- **SC-006**: 100% das alterações relevantes (escopo, criticidade, responsável, arquivamento) geram
  registro de histórico append-only com autor, data, valor anterior e novo valor; alterações críticas
  registram justificativa.
- **SC-007**: A situação de revisão (em dia, próxima do vencimento, vencida, não definida) é derivada
  corretamente e filtrável em 100% dos casos de teste.
- **SC-008**: Relacionamentos entre itens e vínculos com gaps aparecem corretamente nas telas de
  detalhe envolvidas em 100% dos casos; nenhum relacionamento cross-tenant ou de item consigo mesmo é
  permitido.
- **SC-009**: O arquivamento é sempre lógico (nenhum registro é removido fisicamente) e nunca ocorre
  sem justificativa, em 100% dos casos.
- **SC-010**: As seções de ameaças, vulnerabilidades, riscos, controles e evidências aparecem como
  placeholders preparados em 100% das telas de detalhe.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar item, relacionamento,
  vínculo ou histórico de uma organização à qual não pertence — verificado por teste automatizado de
  isolamento de tenant.

## Assumptions

- A feature reutiliza a fundação multi-tenant, autenticação, RBAC, `tenant_scope` e audit log já
  existentes, além do padrão de trilha append-only adotado nos módulos anteriores.
- Responsável, dono e custodiante referenciam **membros da organização** (usuários com vínculo no
  tenant), selecionados por seletor de membros (mesmo padrão das atribuições do Motor de Workflow);
  custodiantes/donos que não sejam usuários do sistema são representados como itens do tipo
  "pessoa/equipe" e ligados por relacionamento. (Confirmado em clarificação 2026-06-26.)
- O código interno usa prefixo derivado do tipo do item + número sequencial **por tipo** dentro da
  organização (ex.: ATV-0001, ATV-0002, PROC-0001), único no tenant e imutável após a criação
  (confirmado em clarificação 2026-06-26). O mapa exato de prefixos por tipo é decisão de planejamento.
- Níveis CIA ordenados Baixa < Média < Alta < Crítica para o cálculo do maior valor; a criticidade
  geral usa a mesma escala.
- O limiar de "próxima do vencimento" (dias antes da próxima revisão) é configurável; valor padrão
  definido no planejamento (sugestão: 30 dias).
- O vínculo com gaps usa o catálogo de gaps **da própria organização** (cópia editável por tenant do
  Gap Analysis), não o catálogo-base de plataforma.
- A exibição reversa de itens na tela do gap está fora do escopo desta feature (deferida); o módulo
  Gap Analysis não é alterado aqui. O vínculo item↔gap é gerenciado integralmente pela tela do item.
- A situação de escopo deste módulo é operacional e independente do ciclo de documento controlado da
  Declaração de Escopo (4.3); não há aprovação/versão de documento controlado neste módulo no MVP.
- Os relatórios em PDF e a assinatura eletrônica são preparados estruturalmente, mas implementados em
  feature futura, reutilizando o motor de documentos imprimíveis/assináveis já existente.
- O SoA atual é tratado como Catálogo de Controles / Pré-SoA e não é fonte primária deste módulo.
