# Feature Specification: SoA Normativa — Declaração de Aplicabilidade dirigida pelo Tratamento de Riscos

**Feature Branch**: `013-soa-normativa-risco`

**Created**: 2026-06-29

**Status**: Draft

**Input**: User description: "Promover o Pré-SoA à Declaração de Aplicabilidade (SoA) NORMATIVA da ISO 27001 (cláusula 6.1.3 d): consolidar primariamente o PLANO DE TRATAMENTO DE RISCOS (Feature 012), com razão de inclusão tipada apontando os riscos tratados, mantendo razões manuais (legal/contratual/melhor prática), justificativa de exclusão, status de implementação (Gap), divergência/reconciliação contra o insumo de risco vivo, gate duro de aprovação (exige Plano de Tratamento aprovado) e o estado Pré-SoA vs. SoA definitiva. Evolução do módulo de SoA existente (Feature 005), não um módulo novo."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Toda feature que toca
  dados de domínio DEVE especificar isolamento de tenant, auditoria e tratamento de dados sensíveis.
  Esta feature EVOLUI o módulo de SoA (Feature 005). NÃO reimplementa Risco (012) nem Gap (004).
-->

## Contexto e Posição na Esteira

A esteira guiada do SGSI segue a ordem ISO: **Contexto (4) → Gap (4–10 + Anexo A) → Ativos →
Gestão de Riscos (6.1.2 / 6.1.3) → [ESTA FEATURE: SoA 6.1.3 d] → Evidências/Auditoria/PDCA**.

Hoje o módulo de SoA (Feature 005) consolida a **avaliação corrente do Gap Analysis** e funciona,
na prática, como um **Catálogo de Controles / Pré-SoA**. Ele já nasceu preparado para esta evolução:
o enum `SoaInclusionReason` já prevê `risk_treatment`, e o item de SoA já carrega o campo
`risks_treated`. O módulo de Risco (012) **já expõe o insumo necessário, read-only**, via
`GET /risk/soa-feed` — o vínculo controle ← risco com razão "tratamento de risco" — e o módulo de
Risco **não escreve na SoA**.

Esta feature **promove o Pré-SoA à SoA normativa** da cláusula 6.1.3 d): a aplicabilidade e a
justificativa de inclusão passam a ser dirigidas **primariamente pelo Plano de Tratamento de Riscos**,
preservando tudo o que a Feature 005 já entrega (matriz dos 93 controles, Documento Controlado,
versões/baseline/aprovação, assinatura avançada opcional, exportação PDF, classificação/acesso,
divergência/reconciliação contra o Gap).

## Clarifications

### Session 2026-06-29

- Q: A consolidação dirigida por risco deve ler o **insumo vivo** do `soa-feed` (estado atual dos
  vínculos controle←risco) ou o **snapshot do Plano de Tratamento aprovado**? → A: **Insumo vivo**
  (`soa-feed`) para a consolidação e a detecção de divergência, espelhando o padrão "valor vivo" que
  a SoA já usa contra o Gap. O **snapshot do Plano aprovado** é usado apenas para o **gate duro** de
  aprovação (existe um Plano aprovado?) e como fonte de auditoria/rastreabilidade.
- Q: Quando um controle é incluído por risco e o usuário também marcou razões manuais, a
  reconciliação por risco pode **remover** a razão `risk_treatment`? → A: A razão `risk_treatment` e
  os `risks_treated` são **derivados do insumo vivo** e geridos pela consolidação/reconciliação; as
  razões **manuais** (legal/contratual/melhor prática) e seus textos são **sempre preservados** e
  nunca removidos por consolidação. Remover `risk_treatment` é uma reconciliação explícita quando o
  insumo de risco deixa de apontar o controle.
- Q: O gate duro bloqueia toda aprovação, ou só a "SoA definitiva"? → A: A aprovação é **sempre
  permitida** como **Pré-SoA** (baseline de consolidação do Gap) **quando não há Plano de Tratamento
  aprovado**, mas a versão emitida é **rotulada "Pré-SoA"**. A **SoA definitiva** (rótulo
  "SoA normativa / 6.1.3 d") só é emitida quando existe um **Plano de Tratamento aprovado** no momento
  da aprovação. O usuário é avisado claramente do estado e do que falta.
- Q: Riscos tratados na SoA passam a ser referência **estruturada** (IDs de risco) ou continuam
  **texto livre**? → A: Referência **estruturada e rastreável** aos riscos vindos do `soa-feed`
  (IDs + códigos `RSK-####`), exibida como tal; o campo de texto livre legado é preservado e
  migrado/coexiste como observação, sem perda de dados (transição do Pré-SoA).
- Q: Na consolidação, item **já existente** na SoA tem os campos de risco auto-aplicados ou
  preservados-e-sinalizados? → A: **Aditivo + sinaliza divergência** (espelha o padrão do Gap):
  a consolidação aplica Aplicável/`risk_treatment`/riscos **só na primeira criação do item ou
  quando ele nunca carregou vínculo de risco**; mudanças posteriores no insumo vivo aparecem como
  **divergência** e só são aplicadas por **reconciliação explícita** (nunca sobrescrita silenciosa).
- Q: O que conta como "Plano de Tratamento de Riscos aprovado" no gate duro? → A: Existe uma
  **versão aprovada vigente (in-force)** do Plano de Tratamento (ponteiro de versão vigente
  definido / não revogada) **no momento da aprovação da SoA**. Se o Plano voltou a rascunho e não
  tem versão vigente, o gate **não** é satisfeito (a SoA é emitida como Pré-SoA).
- Q: Insumo de risco aponta controle **fora** do conjunto Anexo A da SoA (custom/descontinuado)? →
  A: A consolidação **não cria** item de SoA nem **descarta** o sinal — **reporta como aviso/
  divergência** ("risco trata controle fora do Anexo A da SoA") para o usuário decidir; os 93
  controles do Anexo A consolidam normalmente. O universo de controles da SoA permanece estável.
- Q: Reconciliar removendo a **única** razão (`risk_treatment`) de um item aplicável sem razão
  manual? → A: O item **permanece aplicável**, a razão de risco é removida e ele fica **sinalizado
  como "sem razão de inclusão"** (estado incompleto que **bloqueia a aprovação final** até o usuário
  adicionar uma razão manual ou marcar "Não aplicável" com justificativa de exclusão). Sem
  auto-flip nem bloqueio da reconciliação.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consolidar a SoA a partir do Tratamento de Riscos (Priority: P1)

Como Consultor ou Admin da organização, quero **consolidar a SoA dirigida pelo Plano de Tratamento de
Riscos**, de modo que todo controle selecionado no tratamento de um risco apareça automaticamente como
**Aplicável**, com razão de inclusão **"tratamento de risco"** e os **riscos tratados vinculados**
(consumindo o insumo read-only do módulo de Risco), sem redigitar nada.

**Why this priority**: É a mudança central que promove o Pré-SoA à SoA normativa (6.1.3 d). Sem isso a
SoA continua sendo um catálogo de controles derivado só do Gap, e não a declaração que a norma exige
(que liga aplicabilidade ⇄ tratamento de risco). Sozinha já entrega o valor: uma SoA cuja
aplicabilidade é justificada pelos riscos.

**Independent Test**: Numa organização com riscos avaliados e controles selecionados no tratamento,
acionar "Consolidar SoA" produz/atualiza itens da SoA em que os controles do `soa-feed` ficam
**Aplicável = Sim**, com razão `risk_treatment` e a lista de riscos tratados (códigos `RSK-####`)
vinculada; controles fora de qualquer tratamento e sem outra razão permanecem como vinham do Gap.

**Acceptance Scenarios**:

1. **Given** uma organização com riscos cujo tratamento seleciona os controles A.8.7 e A.5.15,
   **When** o usuário aciona a consolidação da SoA, **Then** os itens A.8.7 e A.5.15 ficam
   **Aplicável = Sim**, ganham a razão de inclusão `risk_treatment` e listam os riscos tratados
   (ex.: `RSK-0003, RSK-0007`) vindos do insumo de risco.
2. **Given** um controle já incluído por risco, **When** o tratamento de um risco adicional passa a
   selecionar o mesmo controle, **Then** após nova consolidação a lista de riscos tratados do item é
   **atualizada aditivamente** (sem duplicar), preservando a razão `risk_treatment`.
3. **Given** um controle que **nenhum** risco trata e que não tem razão manual, **When** a SoA é
   consolidada, **Then** sua aplicabilidade/status continuam derivando do Gap (comportamento da
   Feature 005), sem ganhar a razão `risk_treatment`.

---

### User Story 2 - Razões de inclusão manuais e justificativa de exclusão (Priority: P2)

Como Consultor/Admin, quero **adicionar razões de inclusão manuais** (requisito legal, contratual,
melhor prática/negócio) a qualquer controle e **justificar exclusões** dos controles não aplicáveis,
de forma independente do insumo de risco, para completar a SoA normativa.

**Why this priority**: A SoA real combina inclusões dirigidas por risco com inclusões por
requisito legal/contratual/negócio; controles não aplicáveis exigem justificativa de exclusão pela
norma. Depende da SoA existir (US1 ou consolidação do Gap).

**Independent Test**: Adicionar uma razão manual `legal` a um controle persiste a razão junto de
(ou na ausência de) `risk_treatment`; marcar um controle como "Não aplicável" sem justificativa de
exclusão é rejeitado; um controle aplicável sem **nenhuma** razão tipada é rejeitado.

**Acceptance Scenarios**:

1. **Given** um controle aplicável incluído por risco, **When** o usuário adiciona a razão manual
   `contractual` com texto complementar, **Then** o item passa a ter **ambas** as razões
   (`risk_treatment` + `contractual`) e o texto é persistido.
2. **Given** um controle marcado "Não aplicável", **When** o usuário salva sem justificativa de
   exclusão, **Then** o sistema rejeita com mensagem de validação.
3. **Given** um controle marcado "Aplicável" **When** o usuário salva sem nenhuma razão tipada
   (nem risco, nem manual), **Then** o sistema rejeita com mensagem de validação.

---

### User Story 3 - Consolidação aditiva/idempotente e transição do Pré-SoA (Priority: P1)

Como organização que **já montou um Pré-SoA** a partir do Gap (Feature 005), quero que a evolução
**não quebre meu estado existente**: a nova consolidação dirigida por risco deve ser **aditiva e
idempotente**, reconciliando o estado atual com o insumo de risco **sem apagar edições manuais nem
justificativas já escritas**.

**Why this priority**: Há organizações com SoA/Pré-SoA já preenchida em produção. A promoção não pode
causar perda de dados — é um requisito de segurança de dados tão crítico quanto a própria mudança.
Empatado em P1 com a US1 porque a US1 sem esta garantia é destrutiva.

**Independent Test**: Numa SoA pré-existente com itens editados manualmente (razões manuais,
justificativas, observações), rodar a consolidação dirigida por risco **duas vezes seguidas** não
duplica itens, não apaga razões manuais nem textos, e converge para o mesmo resultado (idempotência);
apenas as razões/riscos derivados do insumo de risco são (des)marcados conforme o insumo vivo.

**Acceptance Scenarios**:

1. **Given** uma SoA pré-existente onde A.5.1 tem razão manual `legal` e uma justificativa escrita,
   **When** a consolidação dirigida por risco roda, **Then** a razão `legal` e a justificativa são
   **preservadas**; se A.5.1 também é tratado por um risco, ganha **adicionalmente** `risk_treatment`.
2. **Given** uma SoA consolidada, **When** o usuário aciona a consolidação **novamente** sem mudanças
   no insumo, **Then** nenhum item é duplicado e nenhum campo manual muda (idempotência).
3. **Given** uma SoA com itens criados pela Feature 005 (sem vínculo de risco), **When** a evolução é
   implantada e a consolidação roda, **Then** os itens existentes continuam válidos e consultáveis,
   sem migração destrutiva.

---

### User Story 4 - Divergência e reconciliação contra o insumo de risco (Priority: P2)

Como Consultor/Admin, quero **ver onde a SoA diverge do insumo de risco vivo** (além do Gap, que a
Feature 005 já cobre) e **reconciliar item a item explicitamente**, para manter a SoA coerente com o
tratamento de risco corrente sem sobrescrita silenciosa.

**Why this priority**: Garante coerência rastreável entre a SoA e o tratamento de risco vivo, que muda
ao longo do tempo. Depende de US1 (origem por risco). Mesmo padrão de divergência/reconciliação que a
SoA já tem contra o Gap.

**Independent Test**: Quando um risco passa a selecionar um controle ainda não aplicável na SoA, o item
fica **divergente** ("risco trata mas SoA não inclui"); quando um item está marcado aplicável por risco
mas o insumo de risco não aponta mais aquele controle, fica **divergente** ("incluído por risco órfão");
reconciliar aplica o valor vivo apenas por ação explícita.

**Acceptance Scenarios**:

1. **Given** um controle selecionado no tratamento de um risco mas **não** marcado aplicável na SoA,
   **When** o usuário abre a SoA, **Then** o controle é sinalizado como **divergente** mostrando o
   valor vivo do insumo de risco (riscos que o tratam) vs. o valor atual da SoA.
2. **Given** um item marcado aplicável com razão `risk_treatment` mas cujo insumo de risco **não**
   aponta mais aquele controle, **When** o usuário abre a SoA, **Then** o item é sinalizado como
   divergente ("inclusão por risco sem risco correspondente").
3. **Given** um item divergente vs. risco, **When** o usuário opta por reconciliar, **Then** o valor
   vivo do insumo de risco é aplicado **explicitamente** (incluir + razão `risk_treatment` + riscos, ou
   remover `risk_treatment`/riscos), **nunca** de forma automática/silenciosa, e as razões manuais
   permanecem intactas.

---

### User Story 5 - Gate da esteira: Pré-SoA vs. SoA definitiva na aprovação (Priority: P1)

Como Admin da organização, quero que **rascunhar/editar a SoA seja livre (gate suave)** mas que a
**emissão da SoA definitiva (normativa) exija um Plano de Tratamento de Riscos aprovado (gate duro)**;
enquanto não houver, a tela deixa claro que estou em **modo Pré-SoA** e avisa o que falta.

**Why this priority**: É a regra de negócio que diferencia a SoA normativa de um mero catálogo, e o
ponto de gate da esteira. A norma deriva a aplicabilidade do tratamento de risco; aprovar uma SoA
"definitiva" sem tratamento aprovado seria não-conforme. P1 porque define o significado da aprovação.

**Independent Test**: Sem Plano de Tratamento aprovado, a aprovação é permitida mas a versão emitida é
rotulada **"Pré-SoA"** (consolidação do Gap) com aviso; com Plano aprovado, a versão emitida é rotulada
**"SoA normativa (6.1.3 d)"**. O rótulo da versão reflete o estado no momento da aprovação e é imutável.

**Acceptance Scenarios**:

1. **Given** uma organização **sem** Plano de Tratamento de Riscos aprovado, **When** o Admin envia
   para revisão e aprova a SoA, **Then** o sistema emite a versão, mas **rotulada "Pré-SoA"**, e a UI
   informa que a SoA definitiva exige um Plano de Tratamento aprovado.
2. **Given** uma organização **com** Plano de Tratamento de Riscos aprovado, **When** o Admin aprova a
   SoA, **Then** a versão imutável emitida é rotulada **"SoA normativa (6.1.3 d)"**, com assinatura
   avançada opcional.
3. **Given** a tela da SoA em qualquer estado de rascunho, **When** o usuário a abre, **Then** um
   indicador mostra se está em modo **Pré-SoA** ou **pronta para SoA definitiva**, listando os
   pré-requisitos pendentes (ex.: "Plano de Tratamento de Riscos ainda não aprovado").

---

### User Story 6 - Documento Controlado, versões e exportação PDF enriquecida (Priority: P3)

Como Auditor interno, Consultor ou Admin, quero **emitir versões imutáveis** e **exportar a SoA em PDF**
a partir do snapshot da versão, **agora incluindo a razão de inclusão tipada, os riscos tratados e a
origem** (tratamento de risco vs. inclusão manual), além do rótulo Pré-SoA / SoA normativa.

**Why this priority**: O PDF é o entregável de certificação. Reusa o versionamento/exportação da
Feature 005; o incremento é o conteúdo enriquecido. Depende de US1/US2 (conteúdo) e US5 (rótulo).

**Independent Test**: Exportar uma versão aprovada gera um PDF cujo conteúdo bate com o snapshot,
exibindo por controle a razão de inclusão tipada, os riscos tratados e a origem, e no cabeçalho o
rótulo (Pré-SoA / SoA normativa) daquela versão.

**Acceptance Scenarios**:

1. **Given** uma versão "SoA normativa" aprovada, **When** o usuário a exporta em PDF, **Then** cada
   controle aplicável mostra a(s) razão(ões) de inclusão tipada(s), os riscos tratados (códigos) e a
   origem; controles não aplicáveis mostram a justificativa de exclusão.
2. **Given** múltiplas versões (uma "Pré-SoA" antiga e uma "SoA normativa" recente), **When** o usuário
   exporta a versão antiga, **Then** o PDF reflete exatamente aquele snapshot, com o rótulo "Pré-SoA".
3. **Given** uma exportação concluída, **When** ela termina, **Then** a ação é registrada em audit log.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/consolidar/editar/aprovar/
   exportar a SoA, um item de SoA ou uma versão de SoA que pertence à Organização B, **Then** o sistema
   nega (404/403 sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A e aciona a consolidação dirigida por risco, **Then** apenas o `soa-feed` e os riscos
   da Organização A alimentam a SoA da Organização A; nenhum dado da Organização B é lido ou vinculado.
3. **Given** o insumo de risco (`soa-feed`) é tenant-scoped, **When** a consolidação roda, **Then** ela
   só agrega vínculos controle←risco da própria organização (isolamento fail-closed mesmo na agregação).

### Edge Cases

- Um controle é tratado por um risco **arquivado** — o insumo de risco já exclui riscos arquivados;
  a SoA não deve manter o vínculo a risco arquivado (vira divergência "risco órfão").
- Um risco que selecionava um controle **muda de opção de tratamento** (ex.: passa a "aceitar" sem
  controles) — o controle pode ficar "incluído por risco sem risco correspondente" (divergência).
- O controle do `soa-feed` referencia um **item de catálogo de Gap** que não existe na SoA (catálogo
  personalizado/descontinuado, fora do conjunto Anexo A) — a consolidação **não cria** item de SoA e
  **não descarta** o sinal: reporta como **aviso/divergência** ("risco trata um controle fora do
  conjunto Anexo A da SoA") para o usuário decidir. Os 93 controles do Anexo A consolidam normalmente.
- Consolidar quando **não há nenhum** controle tratado por risco (esteira ainda no Gap) — a SoA
  permanece em modo Pré-SoA, sem itens com razão `risk_treatment`.
- Aprovar a SoA, depois o Plano de Tratamento é **revogado/superado** — versões já emitidas permanecem
  imutáveis com o rótulo que tinham; só novas aprovações reavaliam o gate.
- O campo legado `risks_treated` (texto livre da Feature 005) coexiste com os riscos estruturados —
  não pode ser apagado na transição.
- O que acontece com a SoA quando a organização (tenant) é suspensa?
- Reconciliar um item cuja divergência é simultânea contra **Gap e risco** — as duas fontes de
  divergência são apresentadas e reconciliáveis de forma independente, sem conflito de sobrescrita.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST evoluir a SoA existente (Feature 005) — **sem criar um módulo novo** —
  mantendo a SoA **única por organização**, a matriz dos 93 controles do Anexo A, o Documento
  Controlado/versões/baseline/aprovação, a assinatura avançada opcional, a exportação PDF e a política
  de acesso por classificação.
- **FR-002**: A consolidação da SoA MUST ser dirigida **primariamente pelo Plano de Tratamento de
  Riscos**: para cada controle apontado pelo insumo read-only do módulo de Risco (`soa-feed` —
  vínculo controle←risco), o item de SoA correspondente MUST ficar **Aplicável = Sim**, ganhar a razão
  de inclusão tipada **`risk_treatment`** e vincular os **riscos tratados** (IDs + códigos `RSK-####`).
- **FR-002a**: A consolidação dirigida por risco MUST ler o **valor vivo** do insumo de risco (estado
  atual dos vínculos controle←risco), **não** um snapshot. O snapshot do Plano de Tratamento aprovado
  é usado apenas no gate de aprovação (FR-010) e na rastreabilidade/auditoria.
- **FR-003**: O sistema MUST permitir **razões de inclusão manuais e complementares** por controle,
  dentre: **requisito legal/regulatório**, **requisito contratual**, **melhor prática/requisito de
  negócio** (enum já existente `SoaInclusionReason`), com texto livre complementar; um controle pode ter
  `risk_treatment` **e** razões manuais simultaneamente.
- **FR-004**: Para controles aplicáveis o sistema MUST exigir **ao menos uma razão de inclusão tipada**
  (risco ou manual); para controles **não aplicáveis** MUST exigir **justificativa de exclusão**.
- **FR-005**: O **status de implementação** de cada controle MAY continuar refletindo a **avaliação
  corrente do Gap Analysis** (Implementado/Em andamento/Não iniciado/Não aplicável), como na Feature
  005, independentemente da fonte de aplicabilidade.
- **FR-006**: A consolidação MUST ser **aditiva e idempotente**: rodá-la novamente **não duplica**
  itens nem riscos vinculados, **não apaga** razões manuais nem justificativas/observações já escritas.
  A razão `risk_treatment` e os riscos tratados MUST ser aplicados **apenas na primeira criação do
  item** (ou quando o item nunca carregou vínculo de risco); para itens já existentes que já
  carregaram vínculo de risco, mudanças no insumo vivo MUST aparecer como **divergência** (FR-008) e
  só ser aplicadas por **reconciliação explícita** (FR-009), **nunca** por sobrescrita silenciosa na
  consolidação.
- **FR-007**: A evolução MUST **reconciliar o estado existente** de organizações que já montaram um
  Pré-SoA a partir do Gap **sem perda de dados**: itens, razões manuais, justificativas, status,
  responsáveis, prazos e o campo legado de riscos-texto MUST ser preservados.
- **FR-008**: O sistema MUST **detectar divergências contra o insumo de risco vivo**, no mínimo:
  (a) controle selecionado no tratamento de um risco mas **não** marcado aplicável na SoA;
  (b) item marcado aplicável por razão `risk_treatment` mas **sem** risco correspondente no insumo
  vivo. As divergências contra o **Gap** (Feature 005) MUST permanecer funcionando em paralelo.
- **FR-009**: A **reconciliação** de uma divergência (aplicar o valor vivo do insumo de risco ao item:
  incluir + razão `risk_treatment` + riscos, ou remover `risk_treatment`/riscos órfãos) MUST ocorrer
  apenas por **ação explícita** do usuário, **preservando** as razões manuais e seus textos. Quando a
  reconciliação remove a **única** razão (`risk_treatment`) de um item aplicável sem razão manual, o
  item MUST **permanecer aplicável** e ficar **sinalizado como "sem razão de inclusão"** (estado
  incompleto), sem auto-converter para "Não aplicável" e sem bloquear a reconciliação.
- **FR-009a (completude para aprovação)**: A aprovação/emissão de versão MUST ser **bloqueada**
  enquanto houver controle **aplicável sem razão de inclusão** (incl. o estado da FR-009) ou controle
  **não aplicável sem justificativa de exclusão**. O gate suave (rascunho/edição) permanece livre.
- **FR-010 (gate duro)**: Rascunhar/editar a SoA MUST ser livre (gate suave). A **emissão de versão**
  MUST ser sempre possível, porém a versão MUST ser **rotulada conforme o estado no momento da
  aprovação**: **"SoA normativa (6.1.3 d)"** somente quando, no instante da aprovação, existir uma
  **versão aprovada vigente (in-force)** do Plano de Tratamento de Riscos; caso contrário
  **"Pré-SoA (consolidação do Gap)"**. O rótulo MUST ser registrado de forma imutável na versão.
  *Nota:* o gate de risco **não bloqueia** a aprovação — apenas decide o rótulo. O **único** bloqueio
  de aprovação é a **completude** (FR-009a).
- **FR-011**: A UI MUST indicar continuamente o estado da SoA (**Pré-SoA** vs. **pronta para SoA
  definitiva**) e **listar os pré-requisitos pendentes** para a versão definitiva (ex.: "Plano de
  Tratamento de Riscos ainda não aprovado").
- **FR-012**: A aprovação MUST registrar uma **versão imutável** (Documento Controlado, append-only),
  com **assinatura avançada opcional** (reusa o Motor 003), espelhando a baseline da Feature 005.
- **FR-013**: A **exportação em PDF** MUST refletir exatamente o snapshot da versão e MUST incluir, por
  controle: a(s) **razão(ões) de inclusão tipada(s)**, os **riscos tratados** (códigos), a **origem**
  (tratamento de risco vs. inclusão manual) e, no cabeçalho, o **rótulo** (Pré-SoA / SoA normativa)
  daquela versão; controles não aplicáveis exibem a **justificativa de exclusão**.
- **FR-014**: Os **riscos tratados** por controle MUST ser referência **estruturada e rastreável** aos
  riscos do insumo de risco (IDs + códigos `RSK-####`); o campo legado de riscos-texto (Feature 005)
  MUST ser preservado e coexistir (ex.: como observação) sem perda de dados.
- **FR-015**: Toda **consolidação**, **edição de aplicabilidade/justificativa/razões**, **reconciliação
  de divergência** (Gap e risco) e **aprovação/assinatura/exportação** MUST gerar **audit log** e
  **trilha append-only** preservando autor/data/ação, **sem PII nem conteúdo confidencial**.
- **FR-016**: A feature MUST **consumir o módulo de Risco read-only** (não escreve em risco) e a
  **avaliação corrente do Gap** (status de implementação); MUST **não alterar** o módulo de Risco (012)
  nem o de Gap (004); e MUST **não introduzir cálculo de risco** (o insumo já vem pronto).
- **FR-017**: A feature MUST **preparar o terreno** para a etapa seguinte (Evidências/Auditoria/PDCA),
  mantendo cada controle da SoA rastreável (catálogo de Gap, riscos tratados) para futura anexação de
  evidências, **sem** implementar upload/anexo de evidência nesta feature.
- **FR-018**: O sistema MUST **não implementar Plano de Ação como módulo separado** e MUST reusar as
  permissões de SoA existentes (`view_soa`/`manage_soa`/`approve_soa`) sem criar novas.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado é escopado pela organização do usuário. Recursos
  afetados: **SoA**, **item de SoA (por controle)**, **versão de SoA**, e o **vínculo estruturado item
  de SoA ↔ riscos tratados**. O insumo de risco (`soa-feed`) lido na consolidação é, ele próprio,
  tenant-scoped. Acesso/agregação cross-tenant ⇒ **404/403 sem revelar existência** + audit log.
  Isolamento é sempre **fail-closed**, inclusive na agregação do insumo de risco.
- **SEC-002 (Papéis e permissões)**: Reusa o RBAC da Feature 005, **sem novas permissões**.
  Visualizar/exportar: Admin da organização, Consultor, Gestor, Auditor interno, Cliente (com
  permissão) — `view_soa`. Editar/consolidar/reconciliar: Admin da organização e Consultor —
  `manage_soa`. Aprovar/emitir versão: **Admin da organização** — `approve_soa`.
- **SEC-003 (Auditoria)**: Geram audit log: consolidar (Gap e risco), criar/editar item, mudar
  aplicabilidade/razões/status, reconciliar divergência (Gap e risco), enviar para revisão, aprovar
  (com o rótulo Pré-SoA/normativa), emitir versão, assinar, exportar. Cada registro grava operation,
  entity_type, entity_id, user_id e **nunca** PII/conteúdo confidencial da SoA.
- **SEC-004 (Dados sensíveis)**: A SoA **não** trata PII diretamente, mas seu conteúdo (justificativas,
  riscos tratados, referências) é **confidencial de negócio**. Proteção: rótulo de classificação +
  política de acesso por classificação (reusa Módulo 1); conteúdo nunca em logs/erros. Os vínculos de
  risco guardam **referências** (IDs/códigos), não detalhe sensível do risco.
- **SEC-005 (Evidências/versionamento)**: Sim — a SoA é artefato versionável. Versões são
  **append-only** e preservam autor/data/natureza/aprovador/rótulo (reusa `document_versions`). A
  trilha de item da SoA (`soa_item_event`) permanece append-only e cobre as novas mudanças
  (razões/riscos/origem).
- **SEC-006 (Degradação)**: Falha ao ler o insumo de risco ou ao gerar/exportar o PDF ⇒ a operação
  falha de forma **limpa e auditável**, sem corromper a SoA nem suas versões (fail-closed na exportação
  e na consolidação). Indisponibilidade do insumo de risco **não** silenciosamente apaga vínculos já
  consolidados — apenas adia a consolidação. Isolamento de tenant permanece fail-closed.

### Key Entities *(include if feature involves data)*

- **SoA (Declaração de Aplicabilidade)**: artefato **único por organização** (tenant_id → Organization),
  já existente (Feature 005). Liga-se ao Gap de origem e, agora, **logicamente** ao insumo de risco vivo.
  Atributos: identificador do documento controlado, status de rascunho, ponteiro para versão em vigor,
  classificação, datas de emissão e próxima análise crítica.
- **SoAItem (controle da SoA)**: um por controle do Anexo A (tenant_id), já existente. **Evolui** para
  carregar razões de inclusão tipadas incluindo `risk_treatment`, **riscos tratados estruturados**
  (referência aos riscos do insumo) e indicadores de **origem** (tratamento de risco vs. manual) e de
  **divergência vs. risco** (além da divergência vs. Gap já existente). Preserva o campo legado de
  riscos-texto.
- **Vínculo SoAItem ↔ Risco tratado**: relação **rastreável** (item de SoA → IDs/códigos de risco)
  derivada do insumo read-only do módulo de Risco. Tenant-scoped. **Não** escreve no módulo de Risco.
- **SoAVersion**: snapshot **imutável** de uma emissão (reusa `document_versions`, append-only),
  agora carregando, no conteúdo congelado de cada controle, a razão de inclusão tipada, os riscos
  tratados e a origem, mais o **rótulo da versão** (Pré-SoA / SoA normativa).
- **Razão de inclusão (tipo)**: enumeração já existente — `risk_treatment` (tratamento de riscos) |
  `legal` | `contractual` | `best_practice`.
- **Insumo de risco (`soa-feed`)** *(read-only, externo a esta feature)*: vínculo controle←risco com
  razão "tratamento de risco", exposto pelo módulo de Risco (012); tenant-scoped; consumido, nunca
  escrito.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir de um tratamento de risco com controles selecionados, o usuário **consolida a
  SoA numa única ação** e 100% dos controles do insumo de risco ficam **Aplicável = Sim** com razão
  `risk_treatment` e os riscos tratados vinculados — sem redigitação.
- **SC-002**: A consolidação é **idempotente**: executá-la duas vezes seguidas produz **zero**
  duplicações e **zero** alterações em campos manuais — verificável por teste automatizado.
- **SC-003**: Numa SoA/Pré-SoA pré-existente, a evolução **não causa perda de dados**: 100% das razões
  manuais, justificativas e observações são preservadas após a primeira consolidação dirigida por risco
  — verificável por teste automatizado.
- **SC-004**: 100% dos controles aplicáveis têm ≥1 razão de inclusão tipada e 100% dos não aplicáveis
  têm justificativa de exclusão antes de a versão poder ser aprovada.
- **SC-005**: Toda divergência entre a SoA e o insumo de risco vivo é **visível** ao usuário e nenhuma
  reconciliação ocorre sem ação explícita — verificável por teste automatizado.
- **SC-006**: A SoA só é emitida como **"SoA normativa (6.1.3 d)"** quando existe um Plano de Tratamento
  de Riscos aprovado; sem ele, a versão emitida é rotulada **"Pré-SoA"** e o usuário é avisado do que
  falta — verificável por teste automatizado.
- **SC-007**: O PDF de uma versão aprovada corresponde **exatamente** ao snapshot e exibe, por controle,
  razão de inclusão tipada, riscos tratados e origem, mais o rótulo da versão.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar, exportar, consolidar ou alterar a SoA
  (ou seus itens/versões/vínculos de risco) de uma organização à qual não pertence, e a consolidação
  nunca agrega insumo de risco de outra organização — verificado por teste automatizado de isolamento
  de tenant.

## Assumptions

- **Evolução, não reescrita**: reutiliza integralmente a Feature 005 (matriz dos 93 controles,
  Documento Controlado/versões/baseline/aprovação, assinatura avançada opcional, exportação PDF,
  classificação/acesso, divergência/reconciliação vs. Gap) e a fundação multi-tenant (auth + RBAC +
  `tenant_scope` + RLS + auditoria).
- **Insumo de risco já pronto**: o módulo de Risco (012) já expõe `GET /risk/soa-feed` (read-only,
  tenant-scoped) com o vínculo controle←risco e razão `risk_treatment`; o enum `SoaInclusionReason`
  já inclui `risk_treatment`. Esta feature **consome**, não reimplementa.
- **Insumo vivo para consolidação/divergência; snapshot só para o gate**: a consolidação e a detecção
  de divergência leem o estado vivo do `soa-feed` (espelhando o padrão "valor vivo" vs. o Gap); a
  existência de um **Plano de Tratamento aprovado** é o que decide o rótulo da versão na aprovação.
- **Razões manuais nunca removidas por consolidação**: apenas a razão `risk_treatment` e os riscos
  estruturados são geridos pela consolidação/reconciliação; legal/contratual/melhor prática e seus
  textos são sempre preservados.
- **Uma SoA por organização** (índice único por tenant), coerente com a Feature 005.
- **Aprovação só pelo Admin da organização** (`approve_soa`); **assinatura avançada opcional** na
  emissão; **sem novas permissões**.
- **Status de implementação** continua derivando da avaliação corrente do Gap, como na Feature 005.
- **Transição não destrutiva** do campo legado de riscos-texto: coexiste com os riscos estruturados.

### Dependencies / Out of Scope

- **Depende de**: Módulo de Risco (012, insumo `soa-feed` + Plano de Tratamento aprovado para o gate),
  Gap Analysis (004, status de implementação corrente), Documento Controlado/versões (`document_versions`),
  assinatura avançada (Motor 003), exportação PDF (reportlab, Feature 005), classificação/acesso
  (Módulo 1).
- **Fora de escopo**: reimplementar/alterar o módulo de Risco (012) ou o de Gap (004); escrever na SoA
  a partir do módulo de Risco (o Risco permanece read-only para a SoA); cálculo de risco; Plano de Ação
  como módulo separado; **upload/anexo de arquivos de evidência** por controle (Módulo 5 —
  Evidências/Auditoria/PDCA), que esta feature apenas **prepara**; geração de SoA por IA.
