# Feature Specification: Gap Analysis ISO/IEC 27001:2022

**Feature Branch**: `004-gap-analysis`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Módulo de Gap Analysis ISO/IEC 27001:2022 — avalia a aderência da
organização à norma em duas dimensões (Cláusulas 4–10 e os 93 controles do Anexo A), gera lacunas,
indicadores e insumo para o Plano de Ação e o SoA. Roda sobre a fundação multi-tenant, o Módulo 1
(Diagnóstico/Contexto) e o Motor de Workflow (003)."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Isolamento de tenant,
  auditoria e tratamento de dados sensíveis são obrigatórios. Stack/tecnologia é decidida no /plan.
-->

## Clarifications

### Session 2026-06-20

- Q: Fórmula do percentual de aderência (peso dos status)? → A: Atende totalmente=100%, Atende
  parcialmente=50%, Não atende=0%; "Não aplicável" e "Não preenchido" ficam **fora** do denominador
  (recorte sem itens aplicáveis ⇒ aderência indefinida "—").
- Q: Granularidade da atribuição da condução (Motor 003)? → A: **Avaliação inteira por padrão**, com
  **opção de atribuir por tema do Anexo A** (A.5/A.6/A.7/A.8). Recorte por cláusula fica para evolução.
- Q: Propagação de nova versão do catálogo-seed para a organização? → A: **Opt-in versionado** — a
  org adota a nova versão; adoção **aditiva** (itens novos = "Não preenchido"), preserva
  personalizações/avaliações, marca itens removidos da norma como **descontinuados**; rastreável.
- Q: O que é exigido para congelar uma baseline? → A: **Aprovação do Admin** da organização congela a
  baseline (padrão Documento Controlado); a **assinatura** eletrônica avançada (Motor 003) é reforço
  **opcional**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Avaliar a aderência à norma (matriz de gap) (Priority: P1)

Como Consultor (ou Admin da organização), quero avaliar item a item a aderência da organização às
**Cláusulas 4–10** e aos **93 controles do Anexo A**, registrando para cada item o status de
conformidade e as informações de adequação, para enxergar onde a organização está em relação à
ISO/IEC 27001:2022 e gerar insumo para o Plano de Ação e o SoA.

**Why this priority**: É o núcleo do módulo — sem a matriz avaliável não há gap analysis. Entrega
valor sozinha (um retrato da conformidade) mesmo sem dashboard ou baseline.

**Independent Test**: Com o catálogo-seed disponível, abrir a matriz, registrar status + constatações
+ ações + prioridade em itens das duas dimensões, salvar e reabrir sem perda; um item de outra
organização nunca aparece.

**Acceptance Scenarios**:

1. **Given** o catálogo-seed carregado para a organização, **When** o Consultor define o status de um
   controle (ex.: A.5.1 = "Atende parcialmente") e preenche constatações/ações/prioridade,
   **Then** o item é salvo e o estado persiste ao reabrir.
2. **Given** um controle do Anexo A, **When** o Consultor o marca como "Não aplicável" **sem**
   justificativa, **Then** o sistema recusa e exige a justificativa de exclusão.
3. **Given** uma avaliação em andamento, **When** o Consultor altera o status de um item,
   **Then** a alteração fica registrada no histórico (autor + data) e gera audit log.

---

### User Story 2 - Indicadores de aderência e lista de lacunas (Priority: P2)

Como Consultor/Gestor, quero ver o percentual de aderência (geral e por recorte) e a lista priorizada
de lacunas, para comunicar a situação à direção e alimentar o Plano de Ação.

**Why this priority**: Transforma a matriz em informação acionável e executiva; depende da US1.

**Independent Test**: Com itens avaliados, conferir que o % de aderência geral, por dimensão, por
cláusula e por tema batem com os status registrados (considerando só aplicáveis), e que a lista de
lacunas traz apenas itens aplicáveis com status "Não atende"/"Atende parcialmente", ordenável por
prioridade.

**Acceptance Scenarios**:

1. **Given** itens avaliados com mistura de status, **When** abro o painel, **Then** o % de aderência
   considera **apenas itens aplicáveis** e é consistente entre geral, por dimensão, por cláusula e
   por tema.
2. **Given** itens "Não aplicável", **When** o % é calculado, **Then** eles são excluídos do
   denominador (não contam como atende nem como não atende).
3. **Given** a lista de lacunas, **When** ordeno por prioridade, **Then** vejo primeiro as Críticas,
   depois Altas/Médias/Baixas, contendo só itens aplicáveis não conformes.

---

### User Story 3 - Catálogo editável por organização (Priority: P3)

Como Consultor/Admin, quero personalizar o catálogo da minha organização (renomear, agrupar,
adicionar requisitos/controles próprios) sem afetar outras organizações nem o catálogo-base da
plataforma, para refletir o contexto real da organização.

**Why this priority**: Aumenta a fidelidade da avaliação, mas a US1 já entrega valor com o seed puro.

**Independent Test**: Personalizar/adicionar um item no catálogo da Org A e confirmar que o catálogo
da Org B e o seed-base permanecem intactos.

**Acceptance Scenarios**:

1. **Given** o catálogo da Org A, **When** adiciono um controle próprio, **Then** ele aparece só na
   Org A; Org B e seed-base não mudam.
2. **Given** uma atualização do seed-base da plataforma (nova versão da norma/catálogo), **When** ela
   é aplicada, **Then** nenhuma avaliação já feita é apagada ou sobrescrita silenciosamente — a
   migração é versionada e rastreável.

---

### User Story 4 - Baseline versionada e rastreabilidade (Priority: P4)

Como Consultor/Admin, quero "congelar" o gap analysis como uma linha de base versionada (baseline) e
rastrear cada item até o SoA e o Plano de Ação, para comparar a evolução da aderência ao longo do
tempo e manter cadeia de evidência.

**Why this priority**: Essencial para auditoria/evolução, mas vem depois de existir o que congelar.

**Independent Test**: Congelar uma baseline, alterar a matriz, congelar outra e comparar as duas
aderências; confirmar que a baseline antiga é imutável.

**Acceptance Scenarios**:

1. **Given** uma avaliação preenchida, **When** congelo uma baseline, **Then** é criada uma versão
   imutável (data, autor/aprovador, status) que não pode ser editada/apagada.
2. **Given** duas baselines, **When** comparo, **Then** vejo a variação de aderência entre elas.
3. **Given** um controle do Anexo A avaliado, **When** consulto sua rastreabilidade, **Then** ele é
   referenciável pelo item correspondente do SoA (Módulo 3) e cada lacuna pela ação do Plano de
   Ação (Módulo 4).

---

### User Story 5 - Condução atribuível e assinável (reusa o Motor 003) (Priority: P5)

Como Consultor/Admin, quero atribuir a condução do gap analysis (ou um recorte) a um preenchedor —
membro ou externo via link tokenizado — que é notificado, preenche e envia; e ao final assinar
eletronicamente a avaliação para congelar a baseline, reaproveitando o Motor de Workflow (003).

**Why this priority**: Agrega delegação e formalização (assinatura) ao fluxo já valioso das US1–US4.

**Independent Test**: Atribuir a avaliação a um membro (e a um e-mail externo), o preenchedor assume,
preenche e envia; assinar congela uma baseline com selo de integridade verificável; cross-tenant
negado.

**Acceptance Scenarios**:

1. **Given** uma avaliação, **When** o Consultor a atribui a um preenchedor, **Then** este é
   notificado, assume, preenche e envia — com trilha imutável dos eventos (sem expor o conteúdo).
2. **Given** uma avaliação enviada, **When** é assinada (nível avançada), **Then** congela uma
   baseline imutável com selo de integridade que detecta qualquer alteração posterior.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar a matriz de gap,
   um item de avaliação, o catálogo, uma baseline ou a trilha de atribuição que pertencem à
   Organização B, **Then** o sistema nega (404/403 sem revelar existência) e registra a tentativa em
   audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas dados da Organização A são visíveis/alteráveis; personalizar o
   catálogo de A nunca altera o de B nem o seed-base.

### Edge Cases

- O que acontece quando o seed-base é atualizado para uma nova versão **enquanto** a organização tem
  avaliações em andamento? (Migração versionada; avaliações existentes preservadas; itens novos
  entram como "Não preenchido"; itens removidos da norma são marcados como descontinuados, não
  apagados.)
- Como o percentual de aderência se comporta quando **todos** os itens de um recorte são "Não
  aplicável" ou "Não preenchido"? (Denominador zero ⇒ aderência indefinida/"—", não 0% nem 100%.)
- O que acontece ao tentar congelar uma baseline com itens ainda "Não preenchido"? (Permitido, mas
  sinalizado; a baseline registra a completude no momento do congelamento.)
- O que acontece com um item de avaliação quando o controle correspondente é marcado como "Não
  aplicável" depois de já ter status/constatações? (Mantém o histórico; passa a exigir justificativa
  de exclusão; sai do cálculo de aderência.)
- O que acontece com este recurso quando a organização (tenant) é suspensa? (Somente leitura / sem
  novas alterações, conforme o comportamento padrão da plataforma para tenant suspenso.)

## Requirements *(mandatory)*

### Functional Requirements

**Catálogo-base (seed) e cópia por organização**

- **FR-001**: O sistema MUST fornecer um catálogo-base (seed) mantido pela plataforma cobrindo
  integralmente os requisitos das **Cláusulas 4–10** (com cláusula, subcláusula e resumo) e os **93
  controles do Anexo A** (identificador ex.: A.5.1, nome, tema e texto/objetivo).
- **FR-002**: O catálogo-base MUST ser **versionável**: uma nova versão do seed não pode apagar nem
  sobrescrever silenciosamente avaliações existentes. A adoção de uma nova versão é **opt-in por
  organização** e **aditiva**: itens novos entram como "Não preenchido", personalizações e avaliações
  são preservadas, e itens removidos da norma são marcados como **descontinuados** (não apagados) —
  migração versionada e rastreável.
- **FR-003**: Cada organização MUST receber sua própria **cópia editável** do catálogo, independente
  do seed-base e das demais organizações.
- **FR-004**: Usuários autorizados MUST poder personalizar o catálogo da própria organização:
  renomear itens, agrupar e adicionar requisitos/controles próprios — sem afetar outras organizações
  nem o seed-base.

**Avaliação (matriz)**

- **FR-005**: Para cada item das duas dimensões, o sistema MUST permitir registrar o **status de
  conformidade**: Atende totalmente | Atende parcialmente | Não atende | Não aplicável | (Não
  preenchido, default).
- **FR-006**: Para cada item, o sistema MUST permitir registrar: constatações (situação observada),
  ações de adequação, prioridade (Crítica | Alta | Média | Baixa), responsável, prazo, evidência
  existente (referência textual nesta fase) e observações.
- **FR-007**: Marcar um controle do Anexo A como **"Não aplicável"** MUST exigir uma **justificativa
  de exclusão**, que fica disponível para consumo pelo SoA (Módulo 3).
- **FR-008**: O sistema MUST permitir salvar a avaliação parcialmente e retomá-la sem perda de dados.
- **FR-009**: O sistema MAY permitir registrar, por item, **nível de maturidade** e **estimativa de
  esforço** como insumo de priorização (opcional).
- **FR-010**: Toda alteração de um item da matriz MUST gerar histórico (autor + data) preservado de
  forma append-only.

**Indicadores e visões**

- **FR-011**: O sistema MUST calcular o **percentual de aderência** considerando **apenas itens
  aplicáveis** — geral e por dimensão (Cláusulas 4–10 vs Anexo A), por cláusula (4 a 10) e por tema
  do Anexo A (Organizacional/Pessoas/Físico/Tecnológico). **Peso por status**: Atende totalmente=100%,
  Atende parcialmente=50%, Não atende=0%; "Não aplicável" e "Não preenchido" são **excluídos do
  denominador**. Recorte sem itens aplicáveis ⇒ aderência **indefinida ("—")**, nunca 0% nem 100%.
- **FR-012**: O sistema MUST exibir a **distribuição por status** (contagem de cada status) por
  dimensão.
- **FR-013**: O sistema MUST produzir a **lista de lacunas**: itens aplicáveis com status "Não
  atende" ou "Atende parcialmente", ordenável por prioridade — insumo direto do Plano de Ação.
- **FR-014**: O sistema MAY consolidar a **estimativa de esforço** das ações de adequação (opcional).

**Baseline e rastreabilidade**

- **FR-015**: O sistema MUST permitir **congelar** o gap analysis como uma **baseline versionada**
  (snapshot imutável com data, autor/aprovador, status) mediante **aprovação do Admin da
  organização**, reaproveitando o padrão de Documento Controlado SGSI. A assinatura eletrônica
  avançada (FR-019) é um reforço **opcional** da baseline, não condição para congelá-la.
- **FR-016**: O sistema MUST permitir **comparar** a aderência entre baselines ao longo do tempo.
- **FR-017**: Cada avaliação de controle do Anexo A MUST ser rastreável até o item correspondente do
  SoA (Módulo 3); cada lacuna MUST ser rastreável até a ação do Plano de Ação (Módulo 4). *(Nesta
  feature: expor a chave de rastreabilidade; o consumo é dos módulos 3 e 4.)*

**Condução atribuível e assinável (reusa o Motor 003)**

- **FR-018**: O sistema MUST permitir **atribuir** a condução do gap analysis a um preenchedor —
  membro da organização ou respondente externo via link tokenizado — reaproveitando o ciclo de vida,
  notificação e trilha imutável do Motor de Workflow (003). O escopo da atribuição é a **avaliação
  inteira por padrão**, com **opção de recorte por tema do Anexo A** (A.5/A.6/A.7/A.8). Recorte por
  cláusula fica para evolução.
- **FR-019**: O sistema MUST permitir **assinar eletronicamente** (nível avançada, Lei 14.063/2020) a
  avaliação concluída, congelando a baseline com **selo de integridade** que detecta alteração
  posterior.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado é escopado pela organização do usuário. Recursos
  afetados: catálogo (cópia por org), itens de avaliação (matriz), baselines/versões, trilha e
  assinaturas da condução. Acesso cross-tenant ⇒ **404/403** (sem revelar existência) + audit log.
  O seed-base da plataforma é compartilhado **somente leitura** pelas organizações.
- **SEC-002 (Papéis e permissões)**: **Consultor** e **Admin da organização** avaliam/personalizam/
  atribuem. **Aprovar/congelar a baseline** é do **Admin da organização** (alinhado a
  `approve_context_document` do Módulo 1). **Gestor/Auditor interno** visualizam (incl. dashboard).
  **Cliente** e demais papéis visualizam conforme permissão de contexto. Preencher quando atribuído:
  o preenchedor designado (membro) ou o portador do link. Permissões previstas:
  `view_gap`, `manage_gap`, `assign_gap` (ou reuso de `assign_form`), `approve_gap_baseline`.
- **SEC-003 (Auditoria)**: Geram audit log: criar/editar item de avaliação, marcar N/A, personalizar
  catálogo, atribuir/assumir/enviar/devolver/assinar a condução, congelar/aprovar baseline. Cada
  registro grava [operation, entity_type, entity_id, user_id] e **nunca** PII/conteúdo sensível.
- **SEC-004 (Dados sensíveis)**: Constatações e ações podem conter informação de segurança sensível
  da organização (não necessariamente PII). Tratamento (default, consistente com o Módulo 1):
  protegidas por **isolamento de tenant + RBAC + classificação de acesso** (reusa a política do
  Módulo 1); **nunca** logadas em audit/erros. Cifragem em repouso (`FIELD_ENCRYPTION_KEY`) fica
  reservada a risco/PII/evidência (Módulos de Riscos/Evidências), não a este módulo (default aceito
  nesta feature).
- **SEC-005 (Evidências/versionamento)**: A feature cria/altera artefato versionável (matriz com
  histórico; baseline como Documento Controlado). Sim — alterações são **append-only** e preservam
  autor/data/ação; baselines são imutáveis.
- **SEC-006 (Degradação)**: Falha de e-mail (atribuição/lembrete) é **fail-open** best-effort (não
  bloqueia a avaliação); OTP de assinatura do externo é **fail-closed** (reuso do 003); isolamento
  de tenant é **sempre fail-closed**.

### Key Entities *(include if feature involves data)*

- **CatalogItem (seed-base, plataforma)**: item do catálogo da norma — dimensão (cláusula | controle),
  identificador (ex.: "6.1.2" ou "A.5.1"), nome, tema (para Anexo A), texto/objetivo, versão do seed.
  Compartilhado (não pertence a tenant); somente leitura para as organizações.
- **OrgCatalogItem**: cópia editável do CatalogItem por organização (carrega `tenant_id`); referencia
  o item-seed de origem; marca itens próprios/personalizados e aplicabilidade.
- **GapAssessment**: o gap analysis "de trabalho" da organização (carrega `tenant_id`); um conjunto
  por organização (1 vigente + baselines). Container dos itens de avaliação.
- **GapAssessmentItem**: avaliação de um OrgCatalogItem (carrega `tenant_id`): status, constatações,
  ações, prioridade, responsável, prazo, evidência (ref textual), observações, justificativa de
  exclusão (quando N/A), maturidade/esforço (opcional). Histórico append-only.
- **GapBaseline**: snapshot imutável versionado do GapAssessment (reusa Documento Controlado/versões):
  data, autor/aprovador, status, completude, aderência consolidada — para comparação temporal.
- **SeedVersion**: versão do catálogo-base da plataforma, para migração rastreável.

*(Reuso do Motor 003 para a condução: a atribuição/assinatura da avaliação reaproveita
FormAssignment/FormSignature e a trilha append-only, em vez de novas entidades de workflow.)*

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O seed cobre **100%** das Cláusulas 4–10 e os **93** controles do Anexo A 2022; uma
  atualização do seed não apaga nem sobrescreve nenhuma avaliação existente (0 perdas).
- **SC-002**: O percentual de aderência é **consistente** entre as visões (geral, por dimensão, por
  cláusula, por tema) e considera **apenas itens aplicáveis** — verificável recomputando a partir dos
  status registrados.
- **SC-003**: 100% das tentativas de marcar um controle como "Não aplicável" sem justificativa são
  recusadas.
- **SC-004**: A lista de lacunas retorna exatamente os itens aplicáveis com status "Não atende"/
  "Atende parcialmente", ordenável por prioridade.
- **SC-005**: Uma baseline congelada é imutável (qualquer tentativa de editar/apagar é bloqueada) e
  duas baselines podem ser comparadas mostrando a variação de aderência.
- **SC-006**: Uma avaliação atribuída e assinada gera selo de integridade que, recomputado sobre o
  conteúdo assinado, confere; qualquer alteração posterior é detectável.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar catálogo, matriz, itens,
  baselines ou trilha de uma organização à qual não pertence — verificado por teste automatizado de
  isolamento de tenant.

## Assumptions

- **Reuso da fundação e módulos existentes**: aproveita a fundação multi-tenant (auth + RBAC +
  `tenant_scope` + RLS), o padrão de Documento Controlado/versões do Módulo 1 e o Motor de Workflow
  (003) para atribuição/assinatura — nada disso é reimplementado.
- **Gap Analysis é módulo próprio**, não um formulário genérico do Motor 003: a matriz/dashboards têm
  modelo de dados próprio; o Motor 003 é reusado apenas para o ciclo *atribuir → preencher → assinar*
  e o congelamento de baseline.
- **Fórmula de aderência (confirmado — ver Clarifications)**: itens aplicáveis pesam Atende=100%,
  Atende parcialmente=50%, Não atende=0%; "Não aplicável" e "Não preenchido" ficam fora do
  denominador. Denominador zero ⇒ aderência "—" (indefinida).
- **Um GapAssessment vigente por organização**, com baselines como snapshots (análogo a "1 em vigor +
  histórico" do Módulo 1).
- **Granularidade de atribuição (confirmado — ver Clarifications)**: avaliação inteira por padrão,
  com opção de recorte por tema do Anexo A (A.5/A.6/A.7/A.8); recorte por cláusula fica para evolução.
- **Seed da norma**: o conteúdo textual dos requisitos/controles segue a ISO/IEC 27001:2022 e
  27002:2022; o seed inicial é derivado do estudo de caso real (Nexim Tech) já no repositório.
- **Itens "Não preenchido"** não bloqueiam o congelamento de baseline, mas a completude é registrada.

## Dependencies

- Feature 001 (Fundação multi-tenant), Feature 002 (Diagnóstico/Contexto — padrão Documento
  Controlado) e Feature 003 (Motor de Workflow) implementadas.
- Consumidores a jusante: Módulo 3 (SoA) e Módulo 4 (Plano de Ação) — fora do escopo desta feature.
