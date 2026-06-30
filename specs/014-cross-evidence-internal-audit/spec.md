# Feature Specification: Repositório Transversal de Evidências + Auditoria Interna (9.2)

**Feature Branch**: `014-cross-evidence-internal-audit`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "Feature 5a — etapa final da esteira (Evidências/Auditoria/Melhoria
Contínua/PDCA). Cobre (1) repositório transversal de evidências (generalizando a Feature 008 do Gap)
e (2) auditoria interna (cláusula 9.2). NÃO cobre NC/ações corretivas (10.2), análise crítica (9.3)
nem PDCA (10.1) — feature 5b —, mas prepara a base para esses módulos."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Isolamento de tenant,
  auditoria, integridade/cadeia de custódia de evidências e proteção de dados sensíveis são
  inegociáveis. Esta spec descreve O QUÊ; stack/tecnologia ficam no /speckit.plan.
-->

## Visão Geral

Esta feature fecha a base probatória do SGSI. Tem duas fases complementares:

- **Fase 1 — Repositório transversal de evidências.** Promove o anexo de evidências (hoje exclusivo
  da Matriz do Gap, Feature 008) a uma capacidade **transversal**: qualquer artefato do SGSI
  (controle da SoA, risco, ativo/processo, item do Gap, cláusula/requisito) pode ter evidências
  reais da organização anexadas, com integridade (hash), classificação obrigatória, metadados,
  versionamento, inativação lógica, cadeia de custódia append-only e auditoria. As evidências vivem
  num **repositório central pesquisável/filtrável** e aparecem na tela de cada artefato.
- **Fase 2 — Auditoria interna (9.2).** Permite planejar um programa de auditoria, conduzir
  auditoria(s) com escopo/critérios/auditor/período, percorrer um checklist de itens auditados
  (vinculados a controles do Anexo A, cláusulas ou riscos), registrar **constatações** (conforme /
  NC maior / NC menor / oportunidade de melhoria / observação) com evidência anexada e vínculo, e
  congelar um **relatório de auditoria** como Documento Controlado versionado, aprovável e
  exportável em PDF.

O modelo de vínculo de evidência e o modelo de constatação são **extensíveis por design**, para que
a **Feature 5b** (não conformidades, ações corretivas 10.2, análise crítica 9.3, PDCA 10.1) consiga
ligar-se a eles e **promover** constatações de não conformidade a NCs formais — sem implementar a NC
nesta feature.

## Clarifications

### Session 2026-06-30

- Q: Como o repositório transversal de evidências se relaciona com a base de evidências do Gap
  (Feature 008)? → A: Repositório **unificado** — a evidência é objeto de 1ª classe vinculável a
  **1..N** artefatos (vínculo polimórfico) e as evidências do Gap (008) são **migradas** para o store
  unificado, com o item do Gap passando a ser apenas mais um tipo de alvo (preservando histórico,
  hash e autoria).
- Q: A constatação (finding) deve sempre pertencer a um item de checklist, ou pode existir no nível da
  auditoria? → A: A constatação pertence à **auditoria**; o vínculo a um item de checklist é
  **opcional** (achados podem existir sem um item planejado correspondente).
- Q: Como o checklist de itens auditados é populado? → A: Entrada **manual** com **importação
  opcional** a partir do escopo da SoA/Gap — o auditor adiciona itens à mão e pode importar controles
  do Anexo A / cláusulas já no escopo como itens de checklist.
- Q: Como os alvos "controle do Anexo A" e "cláusula" são referenciados nos vínculos (de evidência e
  de constatação)? → A: Apontando para as **linhas de artefato já existentes e tenant-scoped** —
  controle do Anexo A = item da SoA (`soa_item`); cláusula/controle no Gap = item do Gap
  (`gap_catalog_item`); além de risco e ativo. Sem referência a códigos normativos abstratos de
  plataforma.
- Q: Como o conteúdo de evidências confidenciais/restritas é protegido em repouso no MVP? → A: Via
  **proteção do storage + controle de acesso por classificação** (mesmo padrão da Feature 008/asset),
  **sem cifragem de campo/arquivo no nível da aplicação** neste MVP; cifragem fica como evolução. O
  acesso a conteúdo confidencial/restrito permanece barrado por RBAC + política de classificação.
  *(Reconciliação: "sem cifragem de aplicação" = sem esquema **adicional**; a cifragem Fernet do
  storage de evidências já existente é reutilizada e protege o conteúdo em repouso — ver research D3
  e SEC-004.)*

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anexar Evidência a Qualquer Artefato do SGSI (Priority: P1)

Um usuário autorizado abre um artefato do SGSI — um controle da SoA, um risco, um ativo/processo ou
um item do Gap — e anexa um arquivo ou registro documental que comprova/sustenta aquele artefato.
Informa título/descrição, escolhe a classificação obrigatória e confirma. A evidência passa a
aparecer na seção "Evidências anexadas" daquele artefato, com autor, data, tipo, tamanho,
classificação e indicador de integridade, e fica disponível também no repositório central.

**Why this priority**: É o valor central da Fase 1 e a generalização do padrão já validado na
Feature 008. Sem ele, a comprovação documental continua presa ao Gap e o SGSI não tem base probatória
transversal exigida em auditoria/certificação.

**Independent Test**: Com uma organização autenticada, anexar uma evidência válida a cada tipo de
artefato suportado (controle SoA, risco, ativo, item Gap) e verificar que cada evidência aparece no
artefato correto, escopada ao tenant, com metadados completos (autoria, data, tamanho, tipo,
classificação, integridade) — sem alterar o status/avaliação do artefato.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de gerenciar evidências está na tela de um controle da SoA,
   **When** seleciona um arquivo permitido, informa descrição opcional, escolhe a classificação e
   confirma, **Then** a evidência é registrada vinculada àquele controle e aparece em "Evidências
   anexadas".
2. **Given** o mesmo usuário está na tela de um risco (ou ativo, ou item do Gap), **When** anexa uma
   evidência, **Then** a evidência é vinculada ao artefato correto, com o mesmo conjunto de
   metadados, integridade e classificação.
3. **Given** um upload de arquivo vazio, acima do limite, de formato não permitido ou que falha em
   validação de segurança, **When** o usuário confirma, **Then** o sistema recusa com mensagem clara
   e não cria evidência válida.
4. **Given** uma evidência foi anexada, **When** o usuário consulta seus detalhes, **Then** o sistema
   mostra título/nome, descrição (quando houver), autor, data/hora, tipo, tamanho, classificação e
   indicador de integridade (hash).
5. **Given** o formulário de upload, **When** é exibido, **Then** a classificação aparece obrigatória
   com valor padrão "Uso interno", editável antes do envio.
6. **Given** uma evidência confidencial/restrita, **When** um usuário com apenas permissão de
   visualizar tenta baixar o conteúdo, **Then** o acesso ao conteúdo é negado conforme a política de
   classificação, embora os metadados possam estar visíveis.

---

### User Story 2 - Repositório Central de Evidências Pesquisável (Priority: P2)

Um responsável por compliance abre o repositório central de evidências da organização e pesquisa/
filtra por texto, tipo de artefato vinculado, classificação, autor, data e estado (ativa/inativa).
A partir do resultado, abre uma evidência, vê seus metadados, seus vínculos (a quais artefatos está
associada) e — conforme permissão/classificação — baixa o conteúdo.

**Why this priority**: Centralizar a busca evita que evidências fiquem invisíveis dentro de cada
artefato e é pré-requisito para auditoria interna e para os módulos de 5b. Depende da Fase 1
(P1) já existir.

**Independent Test**: Com evidências anexadas a artefatos distintos, abrir o repositório central,
aplicar filtros (classificação, tipo de artefato, autor, estado) e confirmar que o resultado lista
apenas evidências do tenant ativo e respeita as regras de classificação para conteúdo.

**Acceptance Scenarios**:

1. **Given** evidências anexadas a artefatos diferentes, **When** o usuário abre o repositório
   central, **Then** vê a lista de evidências do tenant com seus metadados e contagem/indicação de
   vínculos.
2. **Given** o repositório central, **When** o usuário filtra por classificação, tipo de artefato,
   autor, intervalo de data ou estado, **Then** o resultado reflete os filtros aplicados.
3. **Given** uma evidência vinculada a mais de um artefato, **When** o usuário abre seus detalhes,
   **Then** vê todos os vínculos atuais e pode navegar até cada artefato.
4. **Given** uma evidência inativada, **When** um usuário sem permissão de gerenciar consulta o
   repositório, **Then** ela não aparece na listagem padrão; usuários com permissão de gerenciar
   conseguem incluí-la via filtro de estado/histórico.

---

### User Story 3 - Preservar Cadeia de Custódia e Versionar Evidências (Priority: P2)

Um auditor/responsável por compliance precisa confiar que toda evidência tem histórico rastreável,
não foi apagada silenciosamente e mantém informação para verificar integridade ao longo do tempo.
Ele substitui uma evidência por nova versão, ou a inativa, e verifica que o histórico preserva autor,
data, ação e vínculos, sem destruir o registro anterior.

**Why this priority**: Evidências são registros de compliance; sua utilidade depende da cadeia de
custódia. É invariante de produto (Core Principle IV) e habilita a confiança da auditoria interna.

**Independent Test**: Anexar uma evidência, substituí-la por nova versão e inativá-la; verificar que
a versão anterior permanece no histórico (somente para quem pode gerenciar), a versão corrente é
identificável, o hash de integridade acompanha cada versão e nada é apagado.

**Acceptance Scenarios**:

1. **Given** uma evidência existente, **When** um usuário autorizado a substitui por nova versão e
   confirma a classificação obrigatória, **Then** a versão anterior é preservada no histórico e a
   versão corrente é marcada de forma clara, cada versão com seu hash.
2. **Given** uma evidência anexada por engano, **When** um usuário autorizado a remove, **Then** o
   sistema realiza inativação lógica preservando histórico e vínculos; nunca exclusão física.
3. **Given** uma evidência tem conteúdo visualizado/baixado, substituído ou inativado, **When** a
   ação é concluída ou negada, **Then** o evento fica auditado e na trilha de custódia append-only,
   sem registrar conteúdo sensível do arquivo.
4. **Given** uma evidência substituída, **When** o usuário consulta o artefato e o repositório,
   **Then** apenas a versão corrente aparece na lista principal; versões anteriores ficam no
   histórico para quem pode gerenciar.

---

### User Story 4 - Planejar e Conduzir uma Auditoria Interna (Priority: P3)

Um Admin/Auditor interno cria um programa de auditoria e, dentro dele, uma auditoria com escopo,
critérios, auditor interno responsável (membro da organização) e período/datas. Conduz a auditoria
percorrendo um checklist de itens auditados, cada um vinculado a um controle do Anexo A, a uma
cláusula ou a um risco, e move a auditoria entre os estados planejada → em andamento → concluída.

**Why this priority**: É o núcleo da Fase 2 (cláusula 9.2). Depende do repositório de evidências (P1)
para anexar comprovação às constatações, mas o planejamento/condução é testável de forma
independente.

**Independent Test**: Criar um programa e uma auditoria com escopo/critérios/auditor/período,
adicionar itens de checklist vinculados a controles/cláusulas/riscos, transitar a auditoria pelos
estados, e verificar que tudo é escopado ao tenant e que transições inválidas são recusadas.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de gerenciar auditoria, **When** cria um programa de auditoria
   (objetivo, período/ciclo), **Then** o programa é registrado e escopado ao tenant.
2. **Given** um programa, **When** o usuário cria uma auditoria com escopo, critérios, auditor interno
   (membro) e datas, **Then** a auditoria nasce no estado "planejada".
3. **Given** uma auditoria planejada, **When** o usuário adiciona itens de checklist vinculados a
   controles do Anexo A, cláusulas ou riscos, **Then** os itens ficam associados à auditoria.
4. **Given** uma auditoria planejada, **When** o usuário a inicia, **Then** ela passa a "em
   andamento"; **When** a conclui após registrar constatações, **Then** passa a "concluída".
5. **Given** uma transição de estado inválida (ex.: concluir uma auditoria já concluída), **When**
   solicitada, **Then** o sistema recusa com mensagem clara e mantém o estado consistente.

---

### User Story 5 - Registrar Constatações com Evidência e Vínculo (Priority: P3)

Durante a condução, o auditor registra constatações (findings): conforme, não conformidade maior,
não conformidade menor, oportunidade de melhoria ou observação. Cada constatação descreve o achado,
vincula-se a um controle/cláusula/risco e pode ter evidências anexadas via o repositório transversal.
Constatações de não conformidade são marcadas como **promovíveis** para que a Feature 5b as transforme
em não conformidades formais.

**Why this priority**: Constatações são o produto da auditoria e o gancho para 5b. Dependem da
auditoria (P3) e do repositório de evidências (P1).

**Independent Test**: Em uma auditoria em andamento, registrar uma constatação de cada tipo com
vínculo a controle/cláusula/risco e evidência anexada; verificar que constatações de NC ficam
marcadas como promovíveis e expõem um ponto de vínculo (ainda vazio) para a NC formal de 5b.

**Acceptance Scenarios**:

1. **Given** uma auditoria em andamento, **When** o usuário registra uma constatação escolhendo um
   dos tipos (conforme / NC maior / NC menor / oportunidade de melhoria / observação), descreve o
   achado e vincula a um controle/cláusula/risco, **Then** a constatação é registrada e listada na
   auditoria.
2. **Given** uma constatação, **When** o usuário anexa uma ou mais evidências do repositório, **Then**
   as evidências ficam vinculadas à constatação (vínculo polimórfico) e aparecem nela.
3. **Given** uma constatação do tipo NC maior ou NC menor, **When** registrada, **Then** ela é
   marcada como promovível e exibe um ponto de vínculo reservado para a futura não conformidade
   formal (5b), ainda não preenchido nesta feature.
4. **Given** uma constatação do tipo conforme / oportunidade de melhoria / observação, **When**
   registrada, **Then** ela NÃO é marcada como promovível a NC.
5. **Given** uma constatação registrada, **When** alterada ou removida logicamente por usuário
   autorizado, **Then** o histórico/trilha preserva autor, data e ação (append-only).

---

### User Story 6 - Congelar o Relatório de Auditoria como Documento Controlado (Priority: P4)

Ao concluir a auditoria, o responsável gera um relatório que consolida escopo, critérios, itens
auditados e constatações. O relatório é submetido para revisão, aprovado por quem tem permissão e
congelado como Documento Controlado versionado e imutável, exportável em PDF, com assinatura avançada
opcional na aprovação.

**Why this priority**: É o gate duro da etapa e o entregável formal da auditoria. Reusa o ciclo de
Documento Controlado (versão imutável + aprovação + PDF + assinatura) já existente.

**Independent Test**: Concluir uma auditoria com constatações, gerar o relatório, submetê-lo a
revisão, aprová-lo (com e sem assinatura), e verificar que a versão fica imutável, exportável em PDF
e que aprovação é bloqueada enquanto a auditoria estiver incompleta.

**Acceptance Scenarios**:

1. **Given** uma auditoria com itens e constatações, **When** o usuário gera o relatório, **Then** é
   criado um rascunho consolidando escopo, critérios, itens auditados e constatações.
2. **Given** um relatório em rascunho, **When** submetido para revisão e aprovado por usuário com
   permissão de aprovar relatório, **Then** uma versão imutável é congelada com autor/data, e o
   conteúdo posterior não altera a versão aprovada.
3. **Given** a aprovação, **When** o aprovador opta por assinar, **Then** a assinatura avançada
   opcional é aplicada à versão (selo de integridade), reusando o motor de assinatura existente.
4. **Given** uma versão aprovada, **When** o usuário exporta, **Then** o sistema gera um PDF da versão
   com escopo, critérios, itens e constatações (tipos + vínculos + evidências referenciadas).
5. **Given** uma auditoria sem constatações obrigatórias concluídas (gate de completude), **When** o
   usuário tenta aprovar/congelar o relatório, **Then** a aprovação é bloqueada com mensagem clara.

---

### User Story 7 - Rastreabilidade / Timeline por Artefato (Priority: P5)

Para um controle da SoA, um risco ou um ativo, um usuário abre uma visão de linha do tempo que
agrega os eventos e artefatos associados — evidências anexadas, constatações de auditoria que o
referenciam e marcos relevantes — em ordem cronológica, somente leitura, reusando as trilhas
append-only e os audit logs existentes.

**Why this priority**: Capacidade transversal de leitura que aumenta a confiança e a navegabilidade,
mas não é pré-requisito para a base probatória. Depende de P1 e P5/P4 para ter conteúdo.

**Independent Test**: Para um controle/risco/ativo com evidências e constatações associadas, abrir a
timeline e verificar que os eventos aparecem em ordem cronológica, escopados ao tenant, sem expor
conteúdo sensível.

**Acceptance Scenarios**:

1. **Given** um controle/risco/ativo com evidências e constatações associadas, **When** o usuário
   abre a timeline do artefato, **Then** vê os eventos/artefatos em ordem cronológica.
2. **Given** a timeline, **When** exibida, **Then** ela não mostra conteúdo de arquivo nem dados
   sensíveis, apenas metadados e referências navegáveis.
3. **Given** um artefato sem eventos, **When** a timeline é aberta, **Then** mostra estado vazio
   claro.

---

### User Story 8 - Dashboard do Módulo e Readiness na Esteira (Priority: P5)

Um gestor abre o dashboard do módulo e vê cards simples: evidências por status e por classificação,
auditorias por status e constatações por tipo. O Dashboard de Conformidade reflete o readiness desta
etapa (ex.: existe auditoria concluída/relatório aprovado).

**Why this priority**: Visão executiva e fechamento da esteira; valor incremental sobre o que já foi
construído. Depende das demais histórias para ter dados.

**Independent Test**: Com evidências, auditorias e constatações criadas, abrir o dashboard do módulo
e verificar as contagens por status/classificação/tipo, escopadas ao tenant; verificar o card de
readiness no Dashboard de Conformidade.

**Acceptance Scenarios**:

1. **Given** dados do módulo no tenant, **When** o usuário abre o dashboard do módulo, **Then** vê
   cards de evidências por status/classificação, auditorias por status e constatações por tipo.
2. **Given** uma auditoria concluída com relatório aprovado, **When** o Dashboard de Conformidade é
   carregado, **Then** o card desta etapa reflete o readiness correspondente.
3. **Given** nenhuma auditoria/evidência, **When** os dashboards são abertos, **Then** mostram estado
   vazio claro sem erro.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler, baixar, vincular,
   substituir ou inativar uma evidência, ou ler/alterar um programa, auditoria, constatação ou
   relatório da Organização B, **Then** o sistema nega com resposta genérica (404/403 sem revelar
   existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** opera no contexto da Organização
   A, **Then** apenas evidências, auditorias e constatações da Organização A são visíveis e
   manipuláveis.
3. **Given** um Super Admin da plataforma autenticado, **When** acessa evidências/auditorias de uma
   organização, **Then** o acesso exige contexto explícito de organização, respeita auditoria e não
   lista dados de múltiplos tenants numa única visão operacional.
4. **Given** uma constatação na Organização A que referencia um controle/risco, **When** a
   consolidação do relatório ou a timeline é montada, **Then** nunca agrega evidências, constatações
   ou artefatos de outro tenant.

### Edge Cases

- Artefato vinculado (controle/risco/ativo/item Gap) sem evidências: a tela mostra estado vazio claro
  e continua utilizável.
- Arquivo vazio, acima do limite, formato não permitido ou que falha em validação de segurança: envio
  recusado com mensagem clara, sem evidência válida.
- Envio interrompido no meio: nenhuma evidência incompleta aparece como válida; novo envio é possível.
- Organização suspensa: leitura e escrita de evidências/auditorias ficam bloqueadas; registros
  existentes são preservados.
- Evidência com PII/conteúdo confidencial: tratada como sensível; nunca exposta em logs, erros,
  telemetria ou trilha.
- Uma evidência é vinculada a mais de um artefato e depois inativada: ela some das listas padrão de
  todos os artefatos vinculados, mas permanece no histórico para quem pode gerenciar.
- Um artefato vinculado é arquivado/excluído logicamente em outro módulo (ex.: ativo arquivado): a
  evidência e seus vínculos permanecem rastreáveis; o vínculo aponta para o artefato em seu estado
  atual sem quebrar.
- Uma constatação de não conformidade fica pendente de promoção: até a Feature 5b, ela permanece
  marcada como promovível, com o ponto de vínculo da NC vazio, sem bloquear o relatório.
- Tentar concluir/aprovar um relatório de auditoria incompleto: bloqueado pelo gate duro com mensagem
  clara.
- Item de checklist vinculado a um controle/cláusula/risco que deixou de existir: o vínculo é tratado
  graciosamente (referência preservada), sem quebrar a auditoria.
- Constatação que referencia uma evidência inativada: o relatório/timeline indica claramente o estado
  inativo da evidência sem apagá-la.

## Requirements *(mandatory)*

### Functional Requirements

#### Fase 1 — Repositório transversal de evidências

- **FR-001**: O sistema MUST permitir anexar uma ou mais evidências a artefatos do SGSI de tipos
  distintos por **vínculo polimórfico**, apontando para **linhas de artefato existentes e
  tenant-scoped**: controle da SoA (item da SoA), risco, ativo/processo e item do Gap Analysis. A
  cláusula/requisito normativo é referenciada pelo respectivo item do Gap (cláusulas 4–10), não por
  código normativo abstrato.
- **FR-002**: O modelo de vínculo de evidência MUST ser **extensível** para novos tipos de alvo sem
  redesenho — preparando explicitamente constatação de auditoria (Fase 2 desta feature) e os alvos
  da Feature 5b (não conformidade, ação corretiva).
- **FR-003**: Uma mesma evidência MUST poder estar vinculada a um ou mais artefatos; o repositório
  central MUST exibir os vínculos atuais de cada evidência.
- **FR-004**: Cada evidência e cada versão de evidência MUST registrar, no mínimo: nome/título,
  descrição opcional, organização (tenant), usuário responsável pelo envio, data/hora, tamanho,
  tipo/formato, classificação obrigatória e indicador de integridade (hash).
- **FR-004a**: O formulário de upload MUST apresentar a classificação como obrigatória com valor
  padrão "Uso interno"; o de substituição MUST pré-preencher a classificação corrente, editável antes
  do envio.
- **FR-005**: O sistema MUST aceitar os tipos de arquivo definidos pela política da plataforma
  (ex.: PDFs, imagens/prints, documentos de escritório, planilhas, compactados quando permitidos) e
  MUST recusar arquivos vazios, acima do limite configurado ou não permitidos pela política de
  segurança, com mensagem clara.
- **FR-006**: O sistema MUST calcular e armazenar um hash de integridade por versão de evidência e
  MUST exibir um indicador de integridade.
- **FR-007**: O sistema MUST permitir substituir/versionar uma evidência preservando a versão
  anterior, identificando a versão corrente e exigindo classificação na nova versão; apenas a versão
  corrente aparece nas listas principais.
- **FR-008**: O sistema MUST permitir inativação lógica de evidência por usuário autorizado,
  preservando histórico e vínculos; **MUST NOT** permitir exclusão física.
- **FR-009**: O sistema MUST manter uma trilha de custódia **append-only** por evidência (envio,
  visualização/download, substituição, inativação, criação/remoção de vínculo, tentativa negada),
  sem nunca apagar/editar registros e sem gravar conteúdo do arquivo.
- **FR-010**: A existência de evidências anexadas MUST NOT alterar automaticamente status, prioridade
  ou avaliação de qualquer artefato vinculado.
- **FR-011**: O sistema MUST exibir as evidências anexadas na tela de cada artefato suportado, em uma
  seção dedicada, sem o usuário precisar sair daquela tela.
- **FR-012**: O sistema MUST oferecer um **repositório central** pesquisável e filtrável por, no
  mínimo: texto, tipo de artefato vinculado, classificação, autor, intervalo de data e estado
  (ativa/inativa).
- **FR-013**: O acesso ao **conteúdo** da evidência MUST respeitar a política de classificação/acesso
  já existente (metadados versus download de conteúdo confidencial/restrito).
- **FR-014**: O sistema MUST generalizar o módulo de evidências do Gap (Feature 008) **sem quebrá-lo**:
  o item do Gap passa a ser um dos tipos de alvo do repositório transversal e a experiência atual da
  Matriz do Gap continua funcionando.
- **FR-015**: O sistema MUST exibir mensagem clara quando upload, download, substituição, inativação
  ou vínculo não puder ser concluído.

#### Fase 2 — Auditoria interna (9.2)

- **FR-020**: O sistema MUST permitir criar e gerenciar **programas de auditoria** por organização,
  com objetivo e período/ciclo.
- **FR-021**: O sistema MUST permitir criar **auditorias** dentro de um programa, com escopo,
  critérios, **auditor interno** (referência a membro da organização) e período/datas.
- **FR-022**: Uma auditoria MUST ter estados de ciclo de vida — no mínimo **planejada → em andamento
  → concluída** (e um estado de cancelamento) — com transições válidas controladas; transições
  inválidas são recusadas.
- **FR-023**: O sistema MUST permitir compor um **checklist** de itens auditados, cada um vinculado a
  um controle do Anexo A, a uma cláusula ou a um risco, com critério/pergunta e resultado. A inclusão
  de itens MUST ser **manual**, com **importação opcional** de controles do Anexo A / cláusulas já no
  escopo da SoA/Gap como itens de checklist (a auditoria não é auto-populada).
- **FR-024**: O sistema MUST permitir registrar **constatações** com tipo entre: **conforme**, **não
  conformidade maior**, **não conformidade menor**, **oportunidade de melhoria** e **observação**.
- **FR-025**: Cada constatação MUST pertencer a uma auditoria e MUST poder ser vinculada a um controle
  do Anexo A, cláusula ou risco; o vínculo a um **item de checklist** é **opcional** (a constatação
  pode existir no nível da auditoria, sem item planejado). Cada constatação MUST poder ter uma ou mais
  evidências anexadas via o repositório transversal (vínculo polimórfico evidência↔constatação).
- **FR-026**: Constatações dos tipos **não conformidade maior/menor** MUST ser marcadas como
  **promovíveis** e MUST expor um ponto de vínculo reservado (vazio nesta feature) para a futura não
  conformidade formal da Feature 5b; os demais tipos NÃO são promovíveis.
- **FR-027**: O sistema MUST permitir gerar um **relatório de auditoria** consolidando escopo,
  critérios, itens auditados e constatações.
- **FR-028**: O relatório de auditoria MUST ser tratado como **Documento Controlado**: submissão a
  revisão, aprovação por usuário com permissão, versão imutável com autor/data, exportação em PDF e
  **assinatura avançada opcional** na aprovação — reusando o ciclo de Documento Controlado existente.
- **FR-029**: A aprovação/congelamento do relatório MUST ser bloqueada por um **gate duro de
  completude**: a auditoria deve estar no estado `completed` **e** nenhum item de checklist pode estar
  com resultado `pendente`. Mensagem clara ao bloquear; navegar/editar/rascunhar permanece sob
  **gates suaves**.
- **FR-030**: Alterações e remoções de programa, auditoria, item de checklist e constatação MUST
  preservar trilha **append-only** (autor, data, ação); remoção é lógica, nunca física.

#### Transversal — Timeline, dashboard e readiness

- **FR-040**: O sistema MUST oferecer uma visão de **timeline somente leitura** por artefato
  (controle/risco/ativo) que agrega eventos e artefatos associados (evidências, constatações que o
  referenciam) em ordem cronológica, reusando trilhas append-only e audit logs existentes, sem expor
  conteúdo sensível.
- **FR-041**: O sistema MUST oferecer um **dashboard do módulo** com cards/visões simples: evidências
  por status/classificação, auditorias por status e constatações por tipo.
- **FR-042**: O sistema MUST refletir o **readiness** desta etapa no Dashboard de Conformidade
  (esteira), reusando a camada de agregação existente.

#### Restrições de escopo

- **FR-050**: A feature MUST NOT implementar registro de não conformidade formal, ações corretivas
  (10.2), análise crítica pela direção (9.3) ou melhoria contínua/PDCA (10.1) — escopo da Feature 5b
  — mas MUST deixar os pontos de vínculo preparados (constatação promovível, vínculo de evidência
  extensível).
- **FR-051**: A feature MUST NOT implementar auditoria externa/certificação, motor de KPIs/medição
  (9.1, no máximo indicadores simples), OCR, análise automática por IA das evidências ou exclusão
  física de registros.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado desta feature é escopado à organização. Recursos
  afetados: evidência, versão de evidência, vínculo de evidência (polimórfico), evento/trilha de
  evidência, programa de auditoria, auditoria, item de checklist, constatação, relatório de auditoria
  e suas versões. Acesso cross-tenant ⇒ 404/403 (sem revelar existência) + audit log. Consolidação de
  relatório e timeline nunca agregam dados de outro tenant (fail-closed).
- **SEC-002 (Papéis e permissões)**: Evidências — visualizar metadados/abrir o repositório exige
  permissão de **visualizar evidências** (`view_evidence`); anexar/substituir/inativar/vincular exige
  **gerenciar evidências** (`manage_evidence`); o conteúdo de evidências confidenciais/restritas exige
  permissão elevada conforme a política de classificação. Auditoria interna — visualizar exige
  `view_internal_audit`; planejar/conduzir/registrar constatações exige `manage_internal_audit`;
  aprovar/congelar o relatório exige `approve_audit_report`. Papéis típicos: Admin da organização,
  Consultor, Auditor interno (condução), Gestor/Dono de controle (visualização). Super Admin só com
  contexto explícito de organização e auditoria. (Nota: a permissão de **auditoria interna** é
  distinta da permissão de leitura de **audit logs** planejada para a trilha de rastreabilidade —
  nomes não devem colidir.)
- **SEC-003 (Auditoria/audit log)**: Geram audit log: upload, visualização/download de conteúdo,
  substituição/versionamento, inativação, criação/remoção de vínculo, criação/edição de programa/
  auditoria/constatação, transições de estado, geração/submissão/aprovação/assinatura/exportação do
  relatório, e tentativas não autorizadas ou cross-tenant. Listar metadados no repositório/painel não
  gera audit por si só. Cada registro grava operação, entidade, identificador, usuário, organização e
  resultado — **nunca** conteúdo de arquivo, caminhos internos, tokens, PII ou dados sensíveis.
- **SEC-004 (Dados sensíveis)**: Sim — evidências são documentos reais da organização e podem conter
  PII/conteúdo confidencial. No MVP, a proteção em repouso reusa a cifragem **Fernet já existente** do
  storage de evidências (`utils/evidence_storage.py`, herdada da Feature 008): o conteúdo é cifrado em
  repouso e exige `FIELD_ENCRYPTION_KEY` (fail-closed). Esta feature **não adiciona um novo esquema de
  cifragem de aplicação** além desse. Conteúdo de arquivo e metadados sensíveis nunca são expostos em
  logs, erros, telemetria ou mensagens de validação; o acesso a conteúdo confidencial/restrito é
  barrado por RBAC + política de classificação. A timeline e o repositório exibem apenas metadados/
  referências.
- **SEC-005 (Evidências/versionamento)**: Sim — a feature cria/altera artefatos versionáveis
  (evidência e suas versões, constatação, relatório de auditoria como Documento Controlado). Toda
  alteração preserva autor/data/ação; trilhas de custódia de evidência e de auditoria interna são
  **append-only**; registros anteriores não são apagados; histórico/versões anteriores ficam
  acessíveis conforme permissão.
- **SEC-006 (Degradação)**: Falha no armazenamento/validação de evidência bloqueia o upload/download
  daquele arquivo de forma **fail-closed**, com mensagem clara; os demais artefatos continuam
  utilizáveis. Falha de e-mail/assinatura na aprovação do relatório segue o comportamento já definido
  no motor de Documento Controlado/assinatura (OTP fail-closed). Isolamento de tenant é **sempre
  fail-closed**.

### Key Entities *(include if feature involves data)*

- **Evidência (Evidence)**: objeto central da organização (tenant) que representa um documento/arquivo
  real de comprovação. Atributos-chave: título/nome, descrição, classificação obrigatória, autor,
  data, tipo, tamanho, hash de integridade, estado (ativa/inativa) e ponteiro para a versão corrente.
- **Versão de Evidência (EvidenceVersion)**: registro imutável de uma versão do conteúdo, com hash,
  autor e data; preserva o histórico quando a evidência é substituída.
- **Vínculo de Evidência (EvidenceLink)**: associação **polimórfica** entre uma evidência e uma **linha
  de artefato existente e tenant-scoped** (tipo + identificador): item da SoA (controle Anexo A),
  risco, ativo/processo, item do Gap (cláusula/controle) e — nesta feature — constatação de auditoria;
  extensível para alvos da 5b. Uma evidência pode ter vários vínculos.
- **Evento de Evidência (EvidenceEvent)**: trilha append-only de custódia (envio, visualização/
  download, substituição, inativação, vínculo/desvínculo, tentativa negada). Não grava conteúdo.
- **Programa de Auditoria (AuditProgram)**: agrupador de auditorias por período/ciclo, com objetivo;
  pertence à organização.
- **Auditoria Interna (InternalAudit)**: instância de auditoria com escopo, critérios, auditor interno
  (membro), período/datas e estado de ciclo de vida (planejada/em andamento/concluída/cancelada).
- **Item de Checklist Auditado (AuditChecklistItem)**: item de verificação vinculado a um controle do
  Anexo A, cláusula ou risco, com critério/pergunta e resultado.
- **Constatação (AuditFinding)**: achado que pertence à auditoria (vínculo a item de checklist
  opcional), com tipo (conforme / NC maior / NC menor / oportunidade de melhoria / observação),
  descrição, vínculo a controle/cláusula/risco, evidências
  anexadas (via EvidenceLink) e marcação de **promovível** + ponto de vínculo reservado para a NC
  formal da 5b (vazio nesta feature).
- **Relatório de Auditoria (AuditReport)**: Documento Controlado versionado/aprovável/exportável que
  consolida escopo, critérios, itens auditados e constatações; reusa o ciclo de versões imutáveis e
  assinatura avançada opcional.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários autorizados conseguem anexar uma evidência válida a qualquer um dos tipos de
  artefato suportados (controle SoA, risco, ativo, item Gap) em menos de 1 minuto, com integridade,
  classificação e cadeia de custódia registradas.
- **SC-002**: 100% das evidências e de suas versões possuem hash de integridade e classificação
  registrados; nenhuma evidência válida é criada sem classificação.
- **SC-003**: O repositório central retorna resultados filtrados corretamente por texto, tipo de
  artefato, classificação, autor, data e estado, listando apenas evidências do tenant ativo.
- **SC-004**: Substituição e inativação de evidência preservam 100% do histórico e dos vínculos,
  mantêm a versão corrente identificável e nunca apagam fisicamente registros.
- **SC-005**: 100% das ações sensíveis sobre evidências e auditorias geram audit log sem expor
  conteúdo de arquivo, caminhos internos ou dados sensíveis; a listagem de metadados não gera audit.
- **SC-006**: Usuários conseguem planejar uma auditoria (escopo/critérios/auditor/período), conduzi-la
  pelos estados e registrar pelo menos uma constatação de cada tipo, com vínculo e evidência, sem
  vazar dados de outro tenant.
- **SC-007**: 100% das constatações de não conformidade (maior/menor) ficam marcadas como promovíveis
  e expõem o ponto de vínculo (vazio) para a NC formal da Feature 5b; nenhuma constatação de outro
  tipo é marcada como promovível.
- **SC-008**: O relatório de auditoria só pode ser aprovado/congelado quando o gate de completude é
  satisfeito; uma vez aprovado, a versão é imutável e exportável em PDF com escopo, critérios, itens
  e constatações.
- **SC-009**: A timeline de um controle/risco/ativo exibe os eventos/artefatos associados em ordem
  cronológica, somente leitura, sem expor conteúdo sensível.
- **SC-010**: O dashboard do módulo apresenta contagens corretas de evidências por status/
  classificação, auditorias por status e constatações por tipo, e o Dashboard de Conformidade reflete
  o readiness desta etapa.
- **SC-011**: A generalização não quebra a Feature 008: a experiência de evidências na Matriz do Gap
  continua funcionando após a unificação no repositório transversal.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar, baixar, vincular, alterar ou inativar
  evidência, auditoria, constatação ou relatório de uma organização à qual não pertence — verificado
  por teste automatizado de isolamento de tenant.

## Dependencies

- **Feature 008 — Evidências do Gap**: padrão a generalizar (upload, hash, classificação, trilha
  append-only, auditoria). Esta feature unifica a base de evidências sem quebrar a experiência do Gap.
- **Feature 005 — SoA** e sua evolução (013): alvo de vínculo de evidência (controle da SoA) e fonte
  de controles do Anexo A para o checklist/constatações.
- **Feature 004 — Gap Analysis**: alvo de vínculo (item do Gap) e fonte de cláusulas (4–10) e
  controles do Anexo A.
- **Feature 011 — Ativos/Processos/Escopo**: alvo de vínculo de evidência (ativo/processo).
- **Feature 012 — Riscos**: alvo de vínculo de evidência e de constatação (risco).
- **Documento Controlado + versões imutáveis**: reuso para o relatório de auditoria (novo tipo de
  documento) com aprovação e PDF.
- **Feature 003 — Motor de Workflow / Assinatura avançada**: assinatura opcional na aprovação do
  relatório.
- **Exportação PDF (Feature 005)**: reuso para o relatório de auditoria.
- **Política de classificação/acesso (Módulo 1)**: governa o acesso ao conteúdo das evidências.
- **Fundação Multi-Tenant (001)**: auth, RBAC, `tenant_scope`/RLS, audit logs.
- **Feature 006 — Dashboard de Conformidade**: recebe o card de readiness desta etapa.

## Preparação para a Feature 5b (não implementar aqui)

- O **vínculo polimórfico de evidência** já contempla, por design, alvos de não conformidade e ação
  corretiva — basta a 5b registrar novos tipos de alvo, sem redesenho.
- A **constatação** carrega flag de **promovível** e um ponto de vínculo reservado (vazio) para a não
  conformidade formal; a 5b lê constatações de NC e cria a NC formal vinculada, fechando o ciclo
  PDCA, sem alterar a estrutura definida aqui.
- A **timeline** e os **dashboards** são extensíveis para incluir NCs/ações corretivas/análise crítica
  quando a 5b existir.

## Assumptions

- A feature reutiliza a fundação multi-tenant, autenticação, RBAC, `tenant_scope`/RLS e audit logs já
  existentes.
- **Modelo de evidência** (resolvido — ver Clarifications): a evidência é um objeto central do tenant,
  vinculável a **1..N** artefatos (vínculo polimórfico reutilizável), em vez de pertencer a um único
  artefato como na Feature 008. O store é **unificado** e as evidências do Gap (008) são **migradas**
  para ele; a Matriz do Gap passa a consumir o repositório transversal mantendo a experiência atual.
  Os detalhes operacionais da migração (preservando histórico, hash e autoria, sem perda de dados) são
  definidos no planejamento (`/speckit.plan`).
- **Permissões novas**: `view_evidence`/`manage_evidence` (repositório transversal) e
  `view_internal_audit`/`manage_internal_audit`/`approve_audit_report` (auditoria interna). O nome da
  permissão de auditoria interna é deliberadamente distinto de uma futura permissão de leitura de
  audit logs (`view_audit`) para evitar colisão.
- A política de tipos de arquivo, tamanho máximo e classificação é configurável no planejamento sem
  mudar a experiência descrita aqui (herda os parâmetros já usados pela Feature 008/storage de
  evidências).
- O **gate de completude** do relatório de auditoria é: auditoria no estado `completed` **e** nenhum
  item de checklist com resultado `pendente` (ver FR-029). Usa o enum `AuditChecklistResult`
  existente — sem campo `mandatory` na checklist.
- A **assinatura avançada** do relatório é opcional, reusando o motor existente; sua ausência não
  bloqueia a aprovação.
- "Visualizar conteúdo" significa abrir/baixar o arquivo, respeitando permissão, classificação e
  auditoria; "listar metadados" não baixa conteúdo e não gera audit.
- Indicadores do dashboard são contagens/agrupamentos simples — não há motor de KPIs/medição (9.1)
  nesta feature.
