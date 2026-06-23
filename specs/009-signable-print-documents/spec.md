# Feature Specification: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

**Feature Branch**: `009-signable-print-documents`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "Implementar a feature Documentos Imprimiveis, Pre-visualizaveis e Assinaveis para permitir que os principais artefatos do SGSI sejam gerados como documentos controlados em PDF, revisados em preview e assinados eletronicamente pela plataforma."

## Clarifications

### Session 2026-06-23

- Q: Como tratar preview desatualizado antes da assinatura? -> A: Preview gera snapshot temporario; assinatura so e permitida se artefato e template nao mudaram desde o preview. Se mudaram, exigir novo preview.
- Q: Qual deve ser o escopo da criacao de templates no MVP? -> A: Admins da organizacao podem criar e versionar templates proprios com variaveis e secoes controladas, sem editor visual avancado.
- Q: Quem pode assinar documentos no MVP? -> A: A assinatura segue a permissao de aprovacao do modulo de origem; Contexto, Gap Analysis e SoA usam seus aprovadores atuais.
- Q: Para Contexto, qual documento deve existir no MVP? -> A: Um unico relatorio consolidado de Contexto reunindo diagnostico, analise de contexto, partes interessadas e escopo.
- Q: O PDF preliminar de preview deve poder ser baixado no MVP? -> A: Sim, permitir baixar PDF preliminar com marca clara de "Nao assinado / Preview".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pre-visualizar Documento Controlado (Priority: P1)

Como usuario autorizado de uma organizacao, quero gerar uma pre-visualizacao de documento para o relatorio consolidado de Contexto, Gap Analysis ou SoA antes de assinar, para revisar o conteudo que sera formalizado como registro do SGSI.

**Why this priority**: A pre-visualizacao e o ponto minimo de valor. Sem ela, o usuario nao consegue revisar o documento final antes de assinar, criando risco de formalizar informacoes incorretas.

**Independent Test**: Selecionar um artefato existente de Contexto consolidado, Gap Analysis ou SoA, gerar preview, verificar que o documento apresenta os dados do artefato, template aplicado, identificacao de tenant, classificacao e status de pre-visualizacao, sem criar documento assinado.

**Acceptance Scenarios**:

1. **Given** um usuario com permissao de visualizar Contexto, **When** ele solicita o preview do relatorio consolidado de Contexto, **Then** o sistema apresenta documento preliminar reunindo diagnostico, analise de contexto, partes interessadas e escopo, com identificacao da organizacao, classificacao e marca clara de "preview".
2. **Given** um usuario visualizando o preview de Gap Analysis, **When** o artefato original ou o template e alterado antes da assinatura, **Then** o sistema bloqueia a assinatura daquele preview e exige nova geracao de preview antes de assinar.
3. **Given** um usuario com permissao apenas de leitura, **When** ele gera preview de SoA, **Then** ele consegue revisar e baixar o PDF preliminar marcado como "Nao assinado / Preview", mas nao consegue assinar o documento.

---

### User Story 2 - Assinar e Congelar Documento (Priority: P1)

Como usuario com permissao de aprovacao do modulo de origem, quero assinar eletronicamente um documento revisado, para gerar uma versao imutavel em PDF com integridade verificavel e cadeia de custodia.

**Why this priority**: A assinatura e o fechamento do ciclo de compliance. O valor central da feature e transformar artefatos vivos em documentos controlados, assinados, rastreaveis e auditaveis.

**Independent Test**: Gerar preview de um artefato, assinar o documento, baixar o PDF final e verificar que alteracoes posteriores no artefato ou no template nao alteram o documento assinado.

**Acceptance Scenarios**:

1. **Given** um preview valido de Gap Analysis, **When** um usuario com permissao de aprovacao do Gap Analysis confirma a assinatura, **Then** o sistema gera um documento assinado, imutavel, com PDF final, hash de integridade, template versionado, metadados do assinante e trilha de auditoria.
2. **Given** um relatorio consolidado de Contexto ja assinado, **When** diagnostico, analise de contexto, partes interessadas ou escopo sao editados posteriormente, **Then** o documento assinado permanece inalterado e a proxima assinatura gera uma nova versao.
3. **Given** uma SoA assinada, **When** o usuario baixa o PDF assinado, **Then** o documento contem identificador verificavel, status assinado, data/hora, responsavel pela assinatura, classificacao e hash de integridade.

---

### User Story 3 - Gerenciar Templates de Impressao (Priority: P2)

Como administrador da organizacao ou responsavel autorizado, quero consultar e preparar templates de impressao por tipo de documento usando variaveis e secoes controladas, para garantir que Contexto, Gap Analysis e SoA tenham formatos consistentes, profissionais e versionados.

**Why this priority**: Templates padronizados reduzem retrabalho e garantem consistencia documental. A customizacao visual avancada pode evoluir depois, mas a existencia de templates versionados e necessaria para rastreabilidade.

**Independent Test**: Listar templates disponiveis para Contexto, Gap Analysis e SoA, selecionar a versao vigente, gerar preview com essa versao e verificar que documentos assinados preservam a versao do template usado.

**Acceptance Scenarios**:

1. **Given** templates padrao do sistema para Contexto consolidado, Gap Analysis e SoA, **When** um usuario gera preview, **Then** o sistema aplica o template vigente correspondente ao tipo de documento.
2. **Given** um documento assinado com uma versao de template, **When** o template vigente e atualizado posteriormente, **Then** o documento assinado continua vinculado a versao original do template.
3. **Given** uma organizacao com permissao de preparar templates, **When** um Admin da organizacao cria ou ativa um template proprio com variaveis e secoes controladas, **Then** novos previews podem usar esse template sem alterar documentos ja assinados.

---

### User Story 4 - Consultar Historico e Verificar Integridade (Priority: P2)

Como auditor, gestor ou usuario autorizado, quero consultar o historico de documentos assinados e verificar sua integridade, para demonstrar cadeia de custodia durante auditorias internas ou externas.

**Why this priority**: Documentos assinados precisam ser localizaveis e verificaveis. Sem historico e verificacao, o PDF assinado perde valor probatorio.

**Independent Test**: Assinar mais de uma versao de um mesmo tipo de documento, listar historico, baixar uma versao anterior e verificar seu hash/identificador sem depender do artefato atual.

**Acceptance Scenarios**:

1. **Given** multiplos documentos assinados de Gap Analysis, **When** o usuario abre o historico, **Then** o sistema lista versoes com tipo, status, assinante, data/hora, classificacao e identificador verificavel.
2. **Given** um documento assinado, **When** o usuario solicita verificacao de integridade, **Then** o sistema informa se o conteudo preservado corresponde ao hash registrado.
3. **Given** um documento assinado tornado obsoleto por versao mais recente, **When** ele e listado ou baixado, **Then** o status de obsolescencia fica claro sem alterar o documento original.

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuario da Organizacao A autenticado, **When** ele tenta visualizar, assinar, listar, baixar ou verificar um documento, preview, template ou historico pertencente a Organizacao B, **Then** o sistema nega (404/403 sem revelar existencia) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado as Organizacoes A e B, **When** ele opera no contexto da Organizacao A, **Then** apenas previews, documentos assinados, historicos e templates permitidos para a Organizacao A sao visiveis/alteraveis.
3. **Given** um Super Admin da plataforma, **When** ele acessa documentos de uma organizacao, **Then** o acesso ocorre somente em contexto explicito e auditado da organizacao selecionada.

### Edge Cases

- O preview fica desatualizado porque o artefato original ou template foi alterado antes da assinatura; a assinatura deve ser bloqueada ate que novo preview seja gerado.
- O template vigente foi desativado ou substituido entre preview e assinatura.
- O artefato ainda nao possui dados suficientes para gerar documento profissional; o sistema deve
  retornar erro claro com `missing_fields`/`missing_sections`, sem gerar PDF parcial. Dados minimos:
  Contexto consolidado exige registros fonte de diagnostico, analise de contexto, partes interessadas
  e escopo; Gap Analysis exige avaliacao adotada com ao menos um item; SoA exige SoA consolidada com
  ao menos um item.
- O usuario tem permissao de visualizar o modulo, mas nao tem permissao de assinar documentos.
- O documento possui classificacao ou sensibilidade que restringe download para alguns papeis.
- Um PDF preliminar e baixado antes da assinatura; o arquivo deve conter marca clara de "Nao assinado / Preview" em todas as paginas ou em local inequivoco.
- A geracao do PDF falha ou fica indisponivel no momento da assinatura.
- Uma organizacao suspensa tenta gerar preview, assinar, listar, verificar ou baixar documento; a
  operacao deve ser bloqueada com mensagem clara e audit log, sem expor dados do documento.
- Um documento assinado precisa ser substituido por nova versao sem apagar a versao anterior.
- Um template contem variavel sem valor no artefato de origem; variaveis obrigatorias bloqueiam a
  geracao com lista de variaveis ausentes, enquanto variaveis opcionais aparecem como "Nao informado"
  e geram aviso visivel no preview.
- Um auditor precisa verificar documento antigo apos alteracao do template e do artefato original.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir gerar preview de documento para Contexto consolidado, Gap Analysis e SoA.
- **FR-002**: O sistema MUST identificar visualmente previews como documentos preliminares nao assinados.
- **FR-003**: O sistema MUST permitir baixar PDF preliminar de preview, sempre com marca clara de "Nao assinado / Preview" para evitar confusao com documento final assinado.
- **FR-004**: O sistema MUST permitir que usuarios com permissao de aprovacao do modulo de origem assinem eletronicamente documentos gerados a partir de preview confirmado.
- **FR-005**: O sistema MUST congelar, no momento da assinatura, os dados do artefato, a versao do template, o documento final, o hash de integridade, o assinante, data/hora, tenant, tipo documental e identificador verificavel.
- **FR-006**: O sistema MUST gerar PDF final assinado para download apos assinatura bem-sucedida.
- **FR-007**: O sistema MUST manter documentos assinados imutaveis, mesmo quando o artefato original ou o template forem alterados posteriormente.
- **FR-008**: O sistema MUST gerar nova versao quando um artefato ja assinado for assinado novamente apos alteracoes.
- **FR-009**: O sistema MUST listar historico de documentos assinados por tipo documental e artefato de origem.
- **FR-010**: O sistema MUST permitir verificar integridade de documento assinado por meio de hash e identificador verificavel.
- **FR-011**: O sistema MUST prover templates padrao para Contexto consolidado, Gap Analysis e SoA.
- **FR-012**: O sistema MUST versionar templates de impressao e preservar a versao usada em cada documento assinado.
- **FR-013**: O sistema MUST permitir que Admins da organizacao criem, versionem e ativem templates proprios por tipo de documento usando apenas variaveis e secoes controladas; editor visual avancado permanece fora do MVP.
- **FR-014**: O sistema MUST exibir no PDF final informacoes minimas de controle documental: organizacao, tipo documental, classificacao, status, versao, data/hora, assinante, identificador e hash de integridade.
- **FR-015**: O sistema MUST impedir assinatura quando o usuario nao possuir permissao adequada.
- **FR-021**: O sistema MUST mapear a permissao de assinatura por tipo documental para a permissao de aprovacao do modulo de origem: Contexto usa aprovadores de documentos de contexto, Gap Analysis usa aprovadores de baseline/Gap, e SoA usa aprovadores de SoA.
- **FR-016**: O sistema MUST impedir assinatura se o artefato ou o template mudaram desde a geracao do preview; nesse caso, o usuario deve gerar novo preview antes de assinar.
- **FR-017**: O sistema MUST registrar auditoria para preview, download preliminar, assinatura, download final, verificacao de integridade, criacao/ativacao de template e tentativas negadas.
- **FR-023**: O sistema MUST impedir que PDFs preliminares exibam status, selo, identificador ou pagina de assinatura que possam ser confundidos com documento assinado.
- **FR-018**: O sistema MUST preparar os tipos documentais para Contexto consolidado, Gap Analysis, SoA, Gap Baseline e respostas de formulario, permitindo extensao futura para documentos separados de Contexto, Plano de Acao, Riscos, Auditoria Interna, Revisao pela Direcao e pacotes de auditoria.
- **FR-022**: O sistema MUST tratar o documento de Contexto do MVP como relatorio consolidado da Clausula 4, reunindo diagnostico, analise de contexto, partes interessadas e escopo.
- **FR-019**: O sistema MUST apresentar mensagens claras quando um documento nao puder ser gerado por dados insuficientes, permissao insuficiente, template indisponivel ou falha temporaria.
- **FR-020**: O sistema MUST permitir que documentos assinados sejam marcados como obsoletos por versoes posteriores sem apagar ou alterar o documento original.
- **FR-024**: O sistema MUST validar dados minimos por tipo documental antes de gerar preview ou assinar; falhas retornam mensagem clara com campos/secoes ausentes e nao criam PDF parcial.
- **FR-025**: O sistema MUST tratar variaveis obrigatorias de template sem valor como erro bloqueante com lista de variaveis ausentes; variaveis opcionais sem valor devem renderizar "Nao informado" e aviso no preview.
- **FR-026**: O sistema MUST bloquear preview, assinatura, listagem sensivel, verificacao e download quando a organizacao estiver suspensa, registrando auditoria sem expor conteudo.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado manipulado por esta feature e escopado pela organizacao do usuario. Recursos afetados: templates por organizacao, versoes de template, previews, snapshots, documentos assinados, PDFs gerados, assinaturas, historico e verificacoes de integridade. Acesso cross-tenant => 404/403 + audit log.
- **SEC-002 (Papeis e permissoes)**: Usuarios com permissao de visualizar o modulo de origem podem gerar preview e consultar documentos permitidos; usuarios com permissao de aprovacao do modulo de origem podem assinar o respectivo documento; Admins da organizacao podem criar, versionar e ativar templates proprios; Super Admin so acessa documentos em contexto explicito e auditado. Permissoes concretas reutilizam a governanca de aprovacao existente para Contexto, Gap Analysis e SoA.
- **SEC-003 (Auditoria)**: Operacoes que geram audit log: preview, download preliminar, assinatura, download final, verificacao de integridade, criacao/ativacao/desativacao de template, listagem historica sensivel e tentativas negadas. Cada registro grava operation, entity_type, entity_id, user_id, tenant_id, outcome e metadados nao sensiveis.
- **SEC-004 (Dados sensiveis)**: Esta feature trata dados confidenciais, PII e possiveis evidencias refletidas nos documentos. Conteudo do documento, PDF, tokens, OTPs, caminhos internos e dados sensiveis nao podem aparecer em logs, mensagens de erro ou audit details. O acesso deve respeitar classificacao/sensibilidade quando aplicavel.
- **SEC-005 (Evidencias/versionamento)**: A feature cria artefatos versionaveis: templates, documentos assinados, snapshots e assinaturas. Documentos assinados e registros de assinatura sao append-only; substituicoes geram nova versao e preservam autor/data/acao.
- **SEC-006 (Degradacao)**: Falha na geracao, armazenamento ou assinatura de documento e fail-closed para assinatura e download final, preservando isolamento de tenant. Preview pode falhar graciosamente com mensagem clara, sem degradar seguranca ou assinar conteudo incompleto.

### Key Entities *(include if feature involves data)*

- **PrintTemplate**: Representa um template de impressao por tipo documental, com nome, escopo, status, classificacao padrao, versao vigente e pertencimento a Organization quando customizado por tenant.
- **PrintTemplateVersion**: Representa uma versao imutavel do template, com conteudo do modelo, variaveis permitidas, secoes controladas, autor, numero da versao e hash; a versao vigente e derivada de `PrintTemplate.current_version_id`, sem mutar a versao.
- **DocumentPreview**: Representa uma pre-visualizacao gerada a partir de um artefato e template especificos, com status preliminar, validade curta, hash do conteudo visualizado, referencias de versao/fingerprint do artefato e template, e tenant.
- **SignedDocument**: Representa documento controlado assinado, com tenant, tipo documental, artefato de origem, versao, status, classificacao, identificador verificavel, hash de integridade e referencia ao arquivo final.
- **SignedDocumentSnapshot**: Representa o conteudo congelado usado para gerar e assinar o documento, preservando dados do artefato, template usado, variaveis resolvidas e metadados de geracao.
- **DocumentSignature**: Representa assinatura eletronica interna da plataforma, com assinante, papel, data/hora, nivel, hash assinado, evidencia de autenticacao e cadeia de custodia.
- **DocumentAccessEvent**: Representa eventos auditaveis relacionados a preview, download, assinatura, verificacao e tentativas negadas, sem armazenar conteudo sensivel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuarios autorizados conseguem gerar preview para Contexto consolidado, Gap Analysis e SoA em ate 30 segundos por documento em condicoes normais.
- **SC-002**: 100% dos previews exibem status preliminar e nao podem ser confundidos visualmente com documentos assinados.
- **SC-010**: 100% dos PDFs preliminares baixados exibem marca clara de "Nao assinado / Preview" e nao incluem selo de assinatura.
- **SC-003**: Usuarios autorizados conseguem assinar um documento revisado e baixar o PDF final em menos de 2 minutos a partir do preview.
- **SC-004**: 100% dos documentos assinados preservam a versao do template e permanecem inalterados apos mudancas no artefato original ou no template vigente.
- **SC-005**: 100% dos documentos assinados possuem identificador verificavel, hash de integridade, assinante, data/hora, tenant, tipo documental e classificacao.
- **SC-006**: Usuarios conseguem consultar historico de documentos assinados de um artefato e baixar uma versao anterior sem depender do estado atual do artefato.
- **SC-007**: Tentativas de assinar sem permissao adequada sao bloqueadas e auditadas em 100% dos casos testados.
- **SC-008**: Falhas de geracao ou armazenamento nao produzem documentos assinados parciais.
- **SC-009**: Templates padrao geram documentos profissionais e consistentes para Contexto consolidado, Gap Analysis e SoA sem configuracao inicial da organizacao.
- **SC-ISO (mandatory)**: Nenhum usuario consegue ler, listar, baixar, assinar, verificar ou alterar documento/template de uma organizacao a qual nao pertence - verificado por teste automatizado de isolamento de tenant.
- **SC-011**: 100% das falhas por dados minimos ausentes ou variaveis obrigatorias sem valor retornam mensagem acionavel com lista do que precisa ser corrigido.
- **SC-012**: Teste automatizado ou quickstart mede que preview e assinatura respeitam metas de 30 segundos e 2 minutos ou retornam timeout claro sem documento parcial.

## Assumptions

- O MVP oferece templates padrao do sistema para Contexto consolidado, Gap Analysis e SoA; customizacao visual avancada fica fora de escopo.
- O documento de Contexto no MVP consolida Diagnostico, Analise de Contexto, Partes Interessadas e Escopo em um unico relatorio da Clausula 4.
- Criacao/ativacao de templates por organizacao deve existir em nivel controlado e versionado para Admins da organizacao, com variaveis e secoes permitidas; editor visual avancado nao faz parte desta feature.
- A assinatura inicial e uma assinatura eletronica interna da plataforma com hash, trilha de auditoria e cadeia de custodia; assinatura digital embutida no PDF, PAdES ou ICP-Brasil fica fora do MVP.
- O fluxo de multiplos assinantes e aprovacao sequencial complexa fica fora do MVP.
- A feature reutiliza a fundacao multi-tenant, RBAC, auditoria, documentos controlados, classificacao e o motor inicial de assinatura existentes.
- A assinatura de documentos no MVP reutiliza os aprovadores ja definidos em cada modulo de origem, em vez de criar uma matriz paralela de assinantes.
- Documentos podem conter informacoes confidenciais, PII e evidencias referenciadas; portanto acesso e logs seguem as regras mais restritivas aplicaveis.
- O identificador verificavel sera suficiente para verificacao interna no MVP, preparando evolucao futura para verificacao publica ou pacote de auditoria.
