# Feature Specification: Diagnóstico e Contexto da Organização (ISO/IEC 27001 — Cláusula 4)

**Feature Branch**: `002-diagnostico-contexto`

**Created**: 2026-06-19

**Status**: Draft

**Input**: User description: "Módulo de Diagnóstico e Contexto da Organização (Cláusula 4 da ISO/IEC 27001:2022): análise de contexto (4.1), mapa de partes interessadas (4.2) e declaração de escopo do SGSI (4.3), produzidos como documentos controlados versionados, sobre a fundação multi-tenant existente."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Esta feature toca dados
  de domínio: DEVE especificar isolamento de tenant, auditoria, versionamento (Princípio IV) e
  tratamento de dados sensíveis. NÃO especificar stack aqui.
-->

## Clarifications

### Session 2026-06-19

- Q: Ao revisar um artefato já "em vigor", o que acontece com a versão vigente? → A: Revisar cria uma **nova versão em rascunho/revisão**; a versão aprovada anterior **permanece "em vigor"** até a nova ser aprovada — sempre **exatamente uma** versão vigente por artefato.
- Q: Quem aprova/emite os artefatos controlados da Cláusula 4? → A: **Apenas o Admin da organização** (permissão `approve_context_document`); Consultor/Dono de processo/Gestor elaboram/revisam (`manage_context`).
- Q: Como a classificação da informação controla o acesso? → A: **Configurável por organização** (mapeamento classificação→papéis) **com RBAC-apenas como default** — sem política configurada, o acesso é só por RBAC e a classificação é rótulo de governança; com política, ela restringe a visibilidade por nível além do papel.
- Q: Quantos conjuntos dos três artefatos uma organização mantém? → A: **Um conjunto vigente por organização** (1 diagnóstico + 1 Análise de Contexto + 1 Mapa + 1 Declaração de Escopo), versionados ao longo do tempo. Múltiplos escopos = evolução futura.

## User Scenarios & Testing *(mandatory)*

<!--
  Histórias priorizadas como jornadas, cada uma independentemente testável sobre a fundação
  multi-tenant já existente (organizações, auth, RBAC, isolamento, auditoria). Para teste isolado,
  cada história assume uma organização ativa e usuários seedados com os papéis necessários.
-->

### User Story 1 - Análise de Contexto da Organização (4.1) (Priority: P1)

Um membro autorizado de uma organização preenche o diagnóstico de contexto de forma incremental
(salvando rascunho e retomando) e registra as questões internas e externas que afetam o SGSI,
classificando cada uma por framework (PESTEL para externo, SWOT para interno) e por impacto
potencial (Alto/Médio/Baixo) sobre os resultados pretendidos do SGSI. O resultado é a Análise de
Contexto — um documento controlado e versionado.

**Why this priority**: É a primeira das três entradas obrigatórias da Cláusula 4 e a base de Gap
Analysis, Riscos e Escopo. Entrega valor sozinha: a organização passa a ter o contexto formalmente
registrado e versionado, exigência direta de auditoria (4.1).

**Independent Test**: Com uma organização ativa e um usuário com permissão, preencher o diagnóstico
parcialmente, salvar e retomar sem perda; registrar questões internas/externas classificadas por
PESTEL/SWOT e impacto; ver a Análise de Contexto consolidada e sua versão.

**Acceptance Scenarios**:

1. **Given** um usuário autorizado de uma organização, **When** ele preenche parte do diagnóstico e
   salva como rascunho, **Then** ao retomar os dados estão preservados e a ação é auditada.
2. **Given** o diagnóstico em edição, **When** o usuário registra uma questão interna e uma externa
   com framework (SWOT/PESTEL) e impacto (Alto/Médio/Baixo), **Then** ambas aparecem classificadas
   na Análise de Contexto.
3. **Given** uma Análise de Contexto, **When** o usuário a emite/aprova, **Then** ela vira uma
   versão imutável no histórico (autor, data, natureza da alteração, aprovador) e a emissão é
   auditada.

---

### User Story 2 - Mapa de Partes Interessadas (4.2) (Priority: P2)

Um membro autorizado cadastra as partes interessadas relevantes (internas e externas), seus
requisitos e expectativas (tipados: legal/regulatório/contratual/expectativa) e como o SGSI
endereça cada um. Ao informar Poder e Interesse de cada parte, o sistema deriva automaticamente a
estratégia de relacionamento (matriz de Mendelow). O resultado é o Mapa de Partes Interessadas —
documento controlado e versionado.

**Why this priority**: Segunda entrada obrigatória da Cláusula 4 e insumo do escopo e dos riscos.
Independentemente testável e entrega valor: visão priorizada das partes interessadas e seus
requisitos.

**Independent Test**: Com uma organização ativa, cadastrar partes interessadas com requisitos
tipados; definir Poder/Interesse e verificar que a estratégia (Gerenciar de perto / Manter
satisfeito / Manter informado / Monitorar) é derivada corretamente; versionar o mapa.

**Acceptance Scenarios**:

1. **Given** um usuário autorizado, **When** ele cadastra uma parte interessada com um requisito
   contratual e descreve como o SGSI o endereça, **Then** a parte e o requisito tipado aparecem no
   Mapa.
2. **Given** uma parte interessada, **When** o usuário define Poder = Alto e Interesse = Alto,
   **Then** a estratégia derivada é "Gerenciar de perto"; **When** Poder = Alto e Interesse =
   Baixo, **Then** "Manter satisfeito"; (e assim para "Manter informado"/"Monitorar").
3. **Given** o Mapa de Partes Interessadas, **When** o usuário o emite, **Then** gera versão
   imutável e auditada.

---

### User Story 3 - Declaração de Escopo do SGSI (4.3) (Priority: P3)

Um membro autorizado elabora a Declaração de Escopo do SGSI a partir das três entradas obrigatórias
da cláusula 4.3 — (a) as questões da Análise de Contexto, (b) os requisitos do Mapa de Partes
Interessadas e (c) as interfaces e dependências com terceiros — registrando inclusões e exclusões
justificadas. A Declaração referencia as versões da Análise de Contexto e do Mapa que a
fundamentaram (rastreabilidade). É um documento controlado e versionado.

**Why this priority**: Terceira entrada da Cláusula 4 e o primeiro documento que um auditor
solicita. Depende conceitualmente de US1/US2, mas é testável de forma independente com contexto e
partes interessadas seedados.

**Independent Test**: Com Análise de Contexto e Mapa de Partes Interessadas existentes, elaborar a
Declaração de Escopo com inclusões/exclusões justificadas e interfaces/dependências; verificar que
ela referencia as versões de origem e que a remoção/obsolescência de um artefato referenciado é
sinalizada.

**Acceptance Scenarios**:

1. **Given** Análise de Contexto e Mapa vigentes, **When** o usuário elabora a Declaração de Escopo
   com inclusões/exclusões justificadas, **Then** a Declaração lista as três entradas (4.3 a/b/c) e
   referencia as versões de Contexto e Partes Interessadas.
2. **Given** uma Declaração de Escopo que referencia uma versão da Análise de Contexto, **When**
   essa Análise é revisada/obsoletada, **Then** o sistema sinaliza a referência potencialmente
   desatualizada (sem quebra silenciosa).
3. **Given** uma Declaração de Escopo, **When** ela é emitida/aprovada, **Then** gera versão
   imutável e auditada.

---

### User Story 4 - Controle documental e versionamento dos artefatos (7.5) (Priority: P4)

Os três artefatos da Cláusula 4 são documentos controlados conforme a cláusula 7.5: cada um possui
identificador estável, classificação da informação, datas de emissão e próxima análise crítica, um
ciclo de vida de status (rascunho → em revisão → aprovado/em vigor → obsoleto/substituído) com
cadeia de aprovação (elaborado/revisado/aprovado por) e histórico de versões imutável.

**Why this priority**: É o controle que torna os artefatos auditáveis e confiáveis (Princípio IV da
constitution). Atravessa US1–US3; isolada como história para tornar o ciclo de vida e a
imutabilidade explicitamente verificáveis.

**Independent Test**: Sobre qualquer artefato, transicionar o status pelo ciclo de vida exigindo o
papel autorizado para aprovar; confirmar que cada versão preserva autor/data/ação, que o histórico
é append-only e que a próxima análise crítica vencida é destacada.

**Acceptance Scenarios**:

1. **Given** um artefato em "rascunho", **When** um usuário sem o papel de aprovação tenta
   aprová-lo, **Then** a ação é negada (403) e auditada.
2. **Given** um artefato "aprovado/em vigor", **When** ele é alterado, **Then** uma nova versão é
   criada preservando a anterior; nenhuma versão é editada ou apagada.
3. **Given** um artefato com data de próxima análise crítica vencida, **When** o usuário consulta os
   artefatos, **Then** ele é destacado como pendente de revisão.

---

### User Story 5 - Visão consolidada e sugestões heurísticas (Priority: P5)

O usuário vê uma visão consolidada e legível do contexto (Cláusula 4) a partir dos três artefatos,
e recebe sugestões (por heurística/regras, não IA) de questões, partes interessadas e requisitos
potencialmente relevantes a partir do diagnóstico — sempre indicativas, nunca aplicadas sem ação
explícita.

**Why this priority**: Melhora a experiência e a completude, mas não é pré-requisito dos artefatos.

**Independent Test**: Preencher o diagnóstico indicando tratamento de dados pessoais e verificar que
o sistema sugere ANPD/titulares como partes interessadas e requisitos LGPD; confirmar que nenhuma
sugestão é persistida sem o usuário aceitá-la explicitamente.

**Acceptance Scenarios**:

1. **Given** um diagnóstico que indica tratamento de dados pessoais, **When** o usuário abre as
   sugestões, **Then** vê sugestões de partes interessadas (ANPD/titulares) e requisitos (LGPD)
   marcadas como indicativas.
2. **Given** uma sugestão, **When** o usuário não a aceita, **Then** ela não é persistida em nenhum
   artefato.
3. **Given** os três artefatos atualizados, **When** o usuário abre a visão consolidada, **Then**
   ela reflete a versão mais recente (aprovada, ou rascunho corrente claramente marcado).

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar um diagnóstico,
   análise de contexto, mapa de partes interessadas ou declaração de escopo (ou versão) da
   Organização B, **Then** o sistema nega (404/403 sem revelar existência) e registra a tentativa em
   audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas os artefatos da Organização A são visíveis/alteráveis.
3. **Given** o Super Admin da plataforma, **When** ele acessa artefatos no contexto de uma
   organização, **Then** o acesso é permitido (único papel cross-tenant), porém toda ação é
   auditada.

### Edge Cases

- Diagnóstico parcialmente preenchido e abandonado: permanece como rascunho recuperável; não entra
  em artefatos aprovados.
- Declaração de Escopo que referencia uma versão de Contexto/Partes que foi obsoletada: referência
  sinalizada como potencialmente desatualizada (não quebra silenciosa).
- Tentativa de aprovar o próprio artefato sem o papel de aprovação: negada e auditada.
- Tentativa de editar/apagar uma versão histórica: não suportada (append-only).
- Próxima análise crítica vencida: artefato destacado como pendente de revisão.
- Organização suspensa (fundação): usuários não operam o módulo até reativação (fail-closed).
- Conteúdo classificado como Confidencial/Restrito: se a organização configurou a política
  classificação→papéis, o acesso respeita o nível além do papel; por padrão (sem política), o acesso
  é apenas por RBAC.

## Requirements *(mandatory)*

### Functional Requirements

**Diagnóstico-questionário**

- **FR-001**: O sistema MUST permitir preencher o diagnóstico de contexto de forma incremental,
  salvando rascunho e retomando sem perda de dados.
- **FR-002**: O diagnóstico MUST cobrir as seções: Identificação, Estrutura, Negócio, Tecnologia,
  Dados tratados (incl. papel controlador/operador LGPD), Cadeia de suprimento e Requisitos
  (legais/regulatórios/contratuais).
- **FR-003**: Os dados do diagnóstico MUST ser reutilizáveis como entradas das análises **por meio
  das sugestões heurísticas** (FR-016 / US5): o usuário aceita as sugestões derivadas do diagnóstico
  para popular questões/partes/requisitos — sem redigitação manual e **sem aplicação automática**
  (não há pré-preenchimento silencioso).

**Análise de Contexto (4.1)**

- **FR-004**: O sistema MUST permitir registrar questões com: descrição, origem (interna/externa),
  classificação por framework (PESTEL para externas; SWOT para internas) e impacto (Alto/Médio/Baixo)
  sobre os resultados pretendidos do SGSI.
- **FR-005**: O sistema MUST permitir registrar/editar a síntese dos resultados pretendidos do SGSI
  e a metodologia/fontes utilizadas.

**Mapa de Partes Interessadas (4.2)**

- **FR-006**: O sistema MUST permitir cadastrar partes interessadas (internas/externas) com seus
  requisitos/expectativas tipados (legal/regulatório/contratual/expectativa) e a descrição de como
  o SGSI endereça cada requisito.
- **FR-007**: Ao informar Poder (Alto/Médio/Baixo) e Interesse (Alto/Médio/Baixo) de uma parte, o
  sistema MUST derivar a estratégia de relacionamento (Mendelow): Gerenciar de perto, Manter
  satisfeito, Manter informado ou Monitorar.

**Declaração de Escopo (4.3)**

- **FR-008**: O sistema MUST permitir elaborar a Declaração de Escopo registrando as três entradas
  da cláusula 4.3: questões (4.1), requisitos das partes (4.2) e interfaces/dependências com
  terceiros.
- **FR-009**: A Declaração MUST registrar inclusões e exclusões com justificativa, e referenciar as
  versões da Análise de Contexto e do Mapa de Partes Interessadas que a fundamentaram.
- **FR-010**: O sistema MUST sinalizar quando a Declaração referencia uma versão de artefato que
  passou a ser obsoleta/revisada (rastreabilidade não silenciosa).

**Documento controlado e versionamento (7.5)**

- **FR-011**: Cada artefato MUST ser um documento controlado com: identificador estável,
  classificação da informação (Público/Uso Interno/Confidencial/Restrito), data de emissão e data
  de próxima análise crítica.
- **FR-011a**: Cada organização MAY configurar uma política de acesso por classificação (mapeamento
  nível → papéis) que restringe a visibilidade dos artefatos **além** do RBAC. **Por padrão** (sem
  política configurada), o acesso é controlado **apenas pelo RBAC** e a classificação é rótulo de
  governança (sem restrição adicional).
- **FR-012**: Cada artefato MUST ter um ciclo de vida de status (rascunho → em revisão →
  aprovado/em vigor → obsoleto/substituído); cada transição é auditada e a aprovação exige o papel
  autorizado.
- **FR-012a**: Revisar um artefato já "em vigor" MUST criar uma **nova versão** em rascunho/revisão,
  mantendo a versão aprovada anterior **"em vigor"** até a nova ser aprovada. O sistema MUST garantir
  **exatamente uma** versão "em vigor" por artefato a qualquer momento; ao aprovar a nova versão, a
  anterior passa a "obsoleta/substituída".
- **FR-013**: Toda alteração relevante MUST gerar nova versão e uma entrada imutável (append-only)
  no histórico (data, autor, natureza da alteração, aprovador). Nenhuma versão é editada ou apagada.
- **FR-014**: O sistema MUST destacar artefatos com a próxima análise crítica vencida.

**Visão consolidada e sugestões**

- **FR-015**: O sistema MUST exibir uma visão consolidada legível do contexto (Cláusula 4) a partir
  dos três artefatos, refletindo a versão mais recente aprovada (ou rascunho corrente, marcado).
- **FR-016**: O sistema MUST gerar sugestões por heurística/regras a partir do diagnóstico
  (ex.: dados pessoais ⇒ ANPD/titulares + requisitos LGPD), sempre indicativas e nunca aplicadas
  sem ação explícita do usuário.

**Transversais**

- **FR-017**: Todo dado do módulo MUST ser escopado pela organização do usuário (ponto único de
  escopo de tenant); acesso cross-tenant ⇒ 404/403 sem revelar existência + audit log.
- **FR-018**: Toda operação sensível (criar/editar/emitir/aprovar/obsoletar artefato, salvar
  diagnóstico, tentativa cross-tenant) MUST gerar registro de auditoria.
- **FR-019**: Mensagens de erro NUNCA MUST expor detalhes internos (tabela, stack, existência de
  recurso de outro tenant).

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado é escopado pela organização. Recursos afetados:
  **Diagnóstico de Contexto**, **Análise de Contexto**, **Mapa de Partes Interessadas**,
  **Declaração de Escopo** e suas **versões**. Acesso cross-tenant ⇒ 404/403 sem revelar existência
  + audit log. Reutiliza o `tenant_scope` central da fundação.
- **SEC-002 (Papéis e permissões)**: Papéis que executam cada ação (permissões granulares):
  - *Visualizar* o contexto/artefatos: membros da organização com permissão (ex.: `view_context`),
    respeitando a classificação da informação.
  - *Editar* diagnóstico e artefatos (rascunho/revisão): Consultor, Dono de processo, Gestor, Admin
    da organização (permissão `manage_context`).
  - *Aprovar/emitir/obsoletar* artefatos: Admin da organização (e/ou papel de direção designado)
    — permissão `approve_context_document`.
  - Super Admin da plataforma: cross-tenant, auditado, sem bypass de auditoria.
- **SEC-003 (Auditoria)**: Geram audit log: salvar diagnóstico, criar/editar questão/parte/escopo,
  transição de status, emissão/aprovação/obsolescência de versão, aceitar sugestão, e tentativa de
  acesso cross-tenant. Cada registro grava `[actor, operation, entity_type, entity_id,
  tenant_context, timestamp, outcome]` e **nunca** PII de conteúdo/dados sensíveis.
- **SEC-004 (Dados sensíveis)**: **Sim** — o contexto pode conter informação de negócio sensível e
  PII (nomes de responsáveis, fornecedores, descrição de dados tratados). Proteção: classificação
  da informação por artefato; por padrão o acesso é por RBAC (classificação = rótulo de governança)
  e cada organização **pode** configurar uma política classificação→papéis que restringe a
  visibilidade por nível (ver FR-011a); conteúdo confidencial nunca em logs/erros/telemetria;
  cifragem de campos sensíveis em repouso quando aplicável conforme a política da plataforma.
- **SEC-005 (Evidências/versionamento)**: **Sim** — os três artefatos são documentos versionáveis
  (cláusula 7.5). Alterações são append-only e preservam autor/data/ação/aprovador; o ciclo de
  aprovação/obsolescência é rastreável de ponta a ponta. Esta é a primeira realização do padrão
  "Documento Controlado SGSI" (ver `docs/iso27001-documento-controlado.md`).
- **SEC-006 (Degradação)**: Isolamento de tenant e suspensão de organização são **fail-closed**. O
  módulo não depende de infraestrutura externa crítica (sugestões são heurísticas locais; sem
  e-mail/IA nesta feature). Falha de geração de sugestões degrada graciosamente (artefatos
  continuam editáveis).

### Key Entities *(include if feature involves data)*

- **Organização (Tenant)**: da fundação; referencial de `tenant_id` de todos os itens abaixo.
- **Diagnóstico de Contexto**: respostas do questionário incremental (seções), com estado
  rascunho/concluído; pertence a uma Organização. Alimenta os artefatos.
- **Questão de Contexto (Issue)**: descrição, origem (interna/externa), framework (PESTEL/SWOT),
  impacto (Alto/Médio/Baixo); pertence à Análise de Contexto.
- **Análise de Contexto**: documento controlado (4.1) que agrega as questões + resultados
  pretendidos; versionado.
- **Parte Interessada**: nome/categoria, tipo (interna/externa), Poder, Interesse, estratégia
  derivada; pertence ao Mapa de Partes Interessadas.
- **Requisito de Parte Interessada**: tipo (legal/regulatório/contratual/expectativa), descrição e
  "como o SGSI endereça"; pertence a uma Parte Interessada.
- **Mapa de Partes Interessadas**: documento controlado (4.2); versionado.
- **Declaração de Escopo**: documento controlado (4.3); inclusões/exclusões, interfaces; referencia
  versões de Análise de Contexto e Mapa; versionado.
- **Versão de Documento**: registro append-only por artefato (identificador, versão, status,
  classificação, datas, elaborado/revisado/aprovado por, natureza da alteração). Materializa o
  padrão "Documento Controlado SGSI".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tentativas de acesso cross-tenant a qualquer artefato/versão são negadas sem
  revelar existência — verificado por teste automatizado de isolamento que cobre diagnóstico,
  análise de contexto, mapa de partes interessadas e declaração de escopo.
- **SC-002**: Um diagnóstico salvo como rascunho é retomado sem nenhuma perda de dados em 100% dos
  casos.
- **SC-003**: 100% das emissões/alterações de artefato geram uma nova versão imutável; 0% das
  versões/histórico podem ser editadas ou apagadas (verificado por teste automatizado).
- **SC-004**: A estratégia de relacionamento de uma parte interessada é derivada corretamente da
  combinação Poder × Interesse em 100% das combinações (Gerenciar de perto / Manter satisfeito /
  Manter informado / Monitorar).
- **SC-005**: 100% das Declarações de Escopo referenciam versões específicas da Análise de Contexto
  e do Mapa de Partes Interessadas; referências obsoletas são sinalizadas.
- **SC-006**: 100% das tentativas de aprovar um artefato sem o papel autorizado são negadas e
  auditadas.
- **SC-007**: Nenhuma sugestão heurística é persistida em um artefato sem ação explícita do usuário
  (0% de aplicação automática).
- **SC-008**: A visão consolidada reflete a versão mais recente dos artefatos em 100% das
  verificações.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar dado de contexto de uma
  organização à qual não pertence — verificado por teste automatizado dedicado de isolamento de
  tenant.

## Assumptions

- **Reutiliza a fundação multi-tenant** (auth + RBAC + `tenant_scope` + auditoria + papéis) já
  implementada; novas permissões (`view_context`, `manage_context`, `approve_context_document`) são
  adicionadas ao RBAC existente.
- **Aprovação** (decidido — ver Clarifications): **apenas** o "Admin da organização" aprova/emite/
  obsoleta os artefatos (`approve_context_document`); Consultor, Dono de processo e Gestor
  elaboram/editam (`manage_context`). Conjunto de aprovadores configurável por organização fica
  como evolução futura.
- **Um diagnóstico e um conjunto vigente dos três artefatos por organização**, cada um versionado
  ao longo do tempo (revisões geram novas versões; versões antigas permanecem consultáveis).
- **Identificador de documento**: padrão configurável por organização (ex.: `SGSI-DOC-NNN`),
  conforme o padrão "Documento Controlado SGSI".
- **Sugestões são heurísticas/regras locais** (sem IA), sempre indicativas; IA é módulo posterior e
  opt-in por organização.
- **Escopo estritamente da Cláusula 4** (+ controle documental 7.5 dos seus artefatos): Gap
  Analysis, SoA, Riscos e Evidências (arquivos) são módulos próprios que consomem este contexto.
