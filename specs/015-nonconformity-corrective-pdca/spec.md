# Feature Specification: Não Conformidades & Ações Corretivas (10.2) + Análise Crítica (9.3) + Melhoria Contínua/PDCA (10.1)

**Feature Branch**: `015-nonconformity-corrective-pdca`

**Created**: 2026-06-30

**Status**: Draft

**Input**: User description: "Feature 5b — etapa final da esteira, segunda parte. Fecha o ciclo PDCA.
Cobre não conformidades e ações corretivas (10.2), análise crítica pela direção (9.3) e melhoria
contínua (10.1). CONSOME a Feature 5a: anexa evidências às NCs/ações pelo repositório existente e
PROMOVE constatações de auditoria do tipo 'não conformidade' a NCs formais. Não reimplementa
evidências nem auditoria interna."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Isolamento de tenant,
  auditoria, integridade/cadeia de custódia, append-only e proteção de dados sensíveis são
  inegociáveis. Esta spec descreve O QUÊ; stack/tecnologia ficam no /speckit.plan.
-->

## Visão Geral

Esta feature **fecha o ciclo PDCA** do SGSI e realimenta a esteira. Tem três fases:

- **Fase 1 — Não Conformidades & Ações Corretivas (10.2)** — o "Plano de Ação" da ISO. Registrar não
  conformidades (NC) com origem, severidade, vínculo a artefato (controle da SoA / risco / ativo),
  **análise de causa raiz**, **plano de ação corretiva** (ação + responsável + prazo) e **verificação
  de eficácia**, acompanhando o status até o encerramento. Uma **constatação de auditoria do tipo "não
  conformidade"** (Feature 5a) pode ser **promovida** a NC formal. Evidências anexadas via o
  repositório transversal da 5a.
- **Fase 2 — Análise Crítica pela Direção (9.3)** — registrar a reunião de análise crítica como
  **Documento Controlado** (entradas + saídas/decisões), versionável, aprovável, exportável em PDF,
  com assinatura avançada opcional.
- **Fase 3 — Melhoria Contínua / PDCA (10.1)** — registrar **melhorias/oportunidades** (origem:
  auditoria, NC, análise crítica, sugestão) com status, e uma **visão do ciclo PDCA** que **fecha o
  loop**: auditorias/NCs/análise crítica geram melhorias que realimentam contexto/risco/controles.

Transversal: dashboard do módulo, card de readiness na esteira e reuso da **rastreabilidade/timeline**
introduzida na 5a. **Consome** SoA (005), Riscos (012), Ativos (011), Evidências + Auditoria Interna
(5a/014), Documento Controlado, assinatura avançada (003) e exportação PDF (005) — **sem alterá-los**.

## Clarifications

### Session 2026-06-30

- Q: Como a promoção de constatação → NC se comporta em relação à constatação de origem? → A:
  **1:1 idempotente** — copia tipo/descrição/vínculo como semente, preenche o `nonconformity_ref`
  reservado na constatação (5a) e **mantém a constatação ativa** (referência bidirecional
  auditoria↔NC; a constatação não é encerrada/arquivada pela promoção).
- Q: Como a Análise Crítica pela Direção (9.3) é modelada — singleton por org (como a SoA) ou várias?
  → A: **Coleção** — **uma análise crítica por reunião**, cada uma um Documento Controlado independente
  (data própria, entradas/saídas, versionável/aprovável/PDF/assinatura). A org acumula um histórico de
  atas ao longo do tempo.
- Q: Qual a escala de severidade da NC? → A: **Maior / Menor / Observação** (terminologia ISO de não
  conformidade, alinhada aos tipos de constatação da auditoria 5a — `nc_maior`/`nc_menor` mapeiam
  diretamente na promoção; "Observação" disponível para NCs registradas manualmente).
- Q: Quantos vínculos a artefato (SoA/risco/ativo) uma NC pode ter? → A: **Um vínculo primário
  opcional** por NC (tipo+id de controle SoA *ou* risco *ou* ativo), além da referência à constatação
  de origem. Múltiplos vínculos por NC ficam para evolução.
- Q: O fechamento do PDCA realimenta os módulos consumidos de forma ativa ou apenas por referência? →
  A: **Referência read-only + visualização** (vínculo da melhoria ao artefato + visão de ciclo PDCA/
  timeline). **Sem write-back automático** nos módulos consumidos; revisar um risco/controle continua
  sendo ação humana no módulo de origem.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar e Tratar uma Não Conformidade (Priority: P1)

Um responsável por compliance registra uma não conformidade: informa origem (constatação de auditoria
interna, auditoria externa, incidente, análise crítica, outros), descrição, severidade e (opcional)
vínculo a um controle da SoA / risco / ativo. Registra a **análise de causa raiz** e acompanha o
**status** (aberta → em andamento → em verificação → encerrada). Quando a origem é uma constatação de
auditoria interna do tipo "não conformidade" (5a), ele a **promove** a NC formal, reaproveitando os
dados da constatação.

**Why this priority**: É o núcleo da cláusula 10.2 e o gancho que a 5a deixou pronto (constatação
promovível). Sem ele, as NCs não têm registro formal nem rastreabilidade de tratamento.

**Independent Test**: Registrar uma NC manual e promover uma constatação de NC da 5a; verificar que
ambas existem com origem/severidade/causa raiz/status, escopadas ao tenant, e que a constatação
promovida fica vinculada à NC criada (e não pode ser promovida duas vezes).

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de gerenciar NCs, **When** registra uma NC com origem,
   descrição, severidade e (opcional) vínculo a controle/risco/ativo, **Then** a NC é criada no estado
   "aberta", com código identificável e escopada ao tenant.
2. **Given** uma constatação de auditoria interna do tipo "não conformidade" (maior/menor) marcada como
   promovível (5a), **When** o usuário a promove, **Then** uma NC formal é criada vinculada à
   constatação, reaproveitando tipo/descrição/vínculo, e a constatação passa a referenciar a NC.
3. **Given** uma constatação já promovida, **When** o usuário tenta promovê-la de novo, **Then** o
   sistema não cria NC duplicada (retorna/abre a NC existente).
4. **Given** uma NC aberta, **When** o usuário registra a análise de causa raiz e altera o status,
   **Then** as mudanças ficam registradas com autor/data em trilha append-only.

---

### User Story 2 - Plano de Ação Corretiva e Verificação de Eficácia (Priority: P1)

Para uma NC, o usuário cria uma ou mais **ações corretivas** (descrição, responsável = membro da
organização, prazo) e acompanha o andamento. Ao concluir as ações, registra a **verificação de
eficácia** (quem verificou, quando, resultado eficaz/ineficaz, observações). O encerramento da NC
depende de uma verificação eficaz.

**Why this priority**: A ação corretiva verificável é o que diferencia o "Plano de Ação" de uma mera
lista de tarefas — é exigência central da 10.2.

**Independent Test**: Criar ações corretivas com responsável e prazo, concluí-las, registrar
verificação de eficácia e encerrar a NC; verificar que o encerramento é bloqueado sem verificação
eficaz e que prazos vencidos são sinalizados.

**Acceptance Scenarios**:

1. **Given** uma NC, **When** o usuário adiciona uma ação corretiva (descrição, responsável, prazo),
   **Then** a ação fica vinculada à NC com status inicial e responsável atribuído.
2. **Given** ações corretivas concluídas, **When** o usuário registra a verificação de eficácia com
   resultado "eficaz", **Then** a NC pode ser encerrada.
3. **Given** uma NC sem verificação de eficácia (ou com verificação "ineficaz"), **When** o usuário
   tenta encerrá-la, **Then** o sistema bloqueia com mensagem clara (gate de encerramento).
4. **Given** uma ação corretiva com prazo no passado e ainda não concluída, **When** a lista é
   exibida, **Then** a ação é sinalizada como **prazo vencido**.

---

### User Story 3 - Lista, Filtros e Indicadores de NCs/Ações (Priority: P2)

Um gestor abre a lista de NCs e filtra por status, severidade, responsável e prazo vencido, com
indicadores de quantidades. A partir da lista, abre uma NC para ver causa raiz, ações, verificação,
evidências e histórico.

**Why this priority**: Operacionaliza o tratamento — sem busca/filtros, o acompanhamento de muitas NCs
fica inviável.

**Independent Test**: Com NCs em estados/severidades distintos, aplicar filtros e confirmar que o
resultado reflete os filtros, escopado ao tenant.

**Acceptance Scenarios**:

1. **Given** NCs com status/severidade/responsável variados, **When** o usuário filtra, **Then** o
   resultado reflete os filtros aplicados.
2. **Given** ações corretivas com prazos diversos, **When** o filtro "prazo vencido" é aplicado,
   **Then** apenas itens vencidos e não concluídos aparecem.
3. **Given** a lista, **When** exibida, **Then** mostra indicadores simples (ex.: NCs por status e por
   severidade).

---

### User Story 4 - Anexar Evidências a NCs e Ações Corretivas (Priority: P2)

O usuário anexa evidências reais (documentos/registros) a uma NC e às suas ações corretivas, usando o
**repositório transversal de evidências da 5a** — com integridade, classificação e custódia
append-only herdadas.

**Why this priority**: A comprovação documental sustenta a eficácia da ação corretiva em auditoria/
certificação. Reusa a 5a sem reimplementar evidências.

**Independent Test**: Anexar uma evidência a uma NC e a uma ação corretiva e verificar que aparecem
vinculadas ao item correto, escopadas ao tenant, com os mesmos metadados/integridade da 5a.

**Acceptance Scenarios**:

1. **Given** uma NC, **When** o usuário anexa uma evidência pelo repositório da 5a, **Then** a
   evidência fica vinculada à NC (vínculo polimórfico para o novo tipo de alvo "não conformidade").
2. **Given** uma ação corretiva, **When** o usuário anexa uma evidência, **Then** ela fica vinculada à
   ação (novo tipo de alvo "ação corretiva").
3. **Given** evidências confidenciais/restritas, **When** acessadas, **Then** valem as mesmas regras de
   classificação/acesso da 5a.

---

### User Story 5 - Análise Crítica pela Direção como Documento Controlado (Priority: P3)

Um Admin/Direção registra uma reunião de análise crítica do SGSI: preenche as **entradas** (status das
ações de análises anteriores, mudanças internas/externas, desempenho do SGSI, resultados de auditoria,
situação dos riscos, NCs e ações corretivas) e as **saídas/decisões** (oportunidades de melhoria,
mudanças no SGSI, necessidade de recursos). Submete, aprova e congela a **Ata** como Documento
Controlado versionado, exportável em PDF, com assinatura avançada opcional.

**Why this priority**: É a cláusula 9.3 e o entregável formal da direção; reusa o ciclo de Documento
Controlado já existente. Depende dos dados das fases anteriores para preencher as entradas.

**Independent Test**: Criar uma análise crítica com entradas/saídas, submeter a revisão, aprovar (com e
sem assinatura) e exportar PDF; verificar que a versão fica imutável e que a aprovação é bloqueada
enquanto incompleta.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de gerenciar análise crítica, **When** cria uma análise crítica
   com entradas e saídas/decisões, **Then** ela é registrada como rascunho escopado ao tenant.
2. **Given** uma análise crítica em rascunho, **When** submetida e aprovada por usuário com permissão
   de aprovar, **Then** uma versão imutável é congelada (autor/data) e exportável em PDF.
3. **Given** a aprovação, **When** o aprovador opta por assinar, **Then** a assinatura avançada opcional
   é aplicada à versão (selo de integridade), reusando o motor existente.
4. **Given** uma análise crítica incompleta (entradas/saídas obrigatórias ausentes), **When** o usuário
   tenta aprovar, **Then** a aprovação é bloqueada com mensagem clara (gate duro).

---

### User Story 6 - Melhorias e Fechamento do Ciclo PDCA (Priority: P4)

O usuário registra **melhorias/oportunidades** (origem: auditoria, NC, análise crítica, sugestão) com
status e (opcional) referência ao artefato que elas realimentam (contexto/risco/controle). Uma visão
de **ciclo PDCA** mostra o loop fechado: auditorias e NCs e análise crítica geram melhorias que
realimentam os módulos a montante — reusando a rastreabilidade/timeline da 5a.

**Why this priority**: É a cláusula 10.1 e o fechamento do PDCA — o diferencial "esteira guiada". Valor
incremental sobre as fases anteriores.

**Independent Test**: Registrar melhorias de origens distintas e abrir a visão de PDCA; verificar que o
loop é exibido (origem → melhoria → artefato realimentado), somente leitura, escopado ao tenant.

**Acceptance Scenarios**:

1. **Given** uma auditoria/NC/análise crítica/sugestão, **When** o usuário registra uma melhoria com
   essa origem, **Then** a melhoria é criada com status e referência de origem.
2. **Given** uma melhoria, **When** o usuário a referencia a um controle/risco/contexto, **Then** o
   vínculo de realimentação fica registrado (referência read-only, sem alterar o artefato).
3. **Given** dados das fases anteriores, **When** a visão de ciclo PDCA é aberta, **Then** ela exibe o
   loop fechado (somente leitura), sem expor conteúdo sensível.

---

### User Story 7 - Dashboard do Módulo + Readiness na Esteira (Priority: P5)

Um gestor abre o dashboard do módulo e vê: NCs por status/severidade, ações corretivas com prazo
vencido, melhorias por status e o estado do ciclo PDCA. O Dashboard de Conformidade reflete o
fechamento do PDCA desta etapa final.

**Why this priority**: Visão executiva e fechamento da esteira; depende das demais fases para ter dados.

**Independent Test**: Com NCs/ações/melhorias criadas, abrir o dashboard e verificar as contagens,
escopadas ao tenant; verificar o card de readiness/PDCA no Dashboard de Conformidade.

**Acceptance Scenarios**:

1. **Given** dados do módulo no tenant, **When** o usuário abre o dashboard, **Then** vê NCs por
   status/severidade, ações com prazo vencido e melhorias por status.
2. **Given** o ciclo PDCA com análise crítica aprovada e NCs encerradas, **When** o Dashboard de
   Conformidade é carregado, **Then** o card desta etapa reflete o fechamento do PDCA.
3. **Given** nenhum dado, **When** os dashboards são abertos, **Then** mostram estado vazio claro sem
   erro.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar uma NC, ação
   corretiva, verificação, análise crítica ou melhoria da Organização B, **Then** o sistema nega com
   resposta genérica (404/403 sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** opera no contexto da Organização A,
   **Then** apenas dados da Organização A são visíveis/manipuláveis.
3. **Given** a promoção de uma constatação a NC, **When** executada, **Then** só promove constatações da
   própria organização; nunca referencia constatação/artefato de outro tenant.
4. **Given** a visão de PDCA/dashboard, **When** montada, **Then** nunca agrega NCs/melhorias/eventos de
   outro tenant (fail-closed).

### Edge Cases

- Promover uma constatação que **não** é do tipo "não conformidade" (conforme/observação/oportunidade):
  bloqueado — apenas constatações promovíveis viram NC.
- Promover uma constatação já promovida: não duplica; resolve a NC existente.
- Encerrar NC sem ação corretiva concluída ou sem verificação eficaz: bloqueado pelo gate de
  encerramento.
- Ação corretiva com responsável que deixou de ser membro ativo: a ação permanece rastreável; o sistema
  trata graciosamente (sem quebrar listagem).
- Organização suspensa: leitura/escrita de NCs/análise crítica/melhorias bloqueadas; registros
  preservados.
- NC vinculada a um controle/risco/ativo que foi arquivado/excluído logicamente: o vínculo é preservado
  e exibido no estado atual sem quebrar.
- Tentar aprovar/congelar uma Ata de análise crítica incompleta: bloqueado pelo gate duro.
- Melhoria que referencia artefato de outro módulo: é **referência read-only** — nunca altera o módulo
  consumido.
- Constatação de NC inativada na 5a depois de promovida: a NC permanece; a referência indica o estado.

## Requirements *(mandatory)*

### Functional Requirements

#### Fase 1 — Não Conformidades & Ações Corretivas (10.2)

- **FR-001**: O sistema MUST permitir registrar uma **não conformidade** com origem (constatação de
  auditoria interna, auditoria externa, incidente, análise crítica, outros), descrição, **severidade
  (Maior / Menor / Observação)** e (opcional) vínculo a um artefato tenant-scoped (controle da SoA,
  risco ou ativo). Na promoção (FR-002), `nc_maior`/`nc_menor` da constatação mapeiam para Maior/Menor.
  O vínculo a artefato é **um primário opcional** por NC (tipo+id); múltiplos vínculos ficam para
  evolução.
- **FR-002**: O sistema MUST permitir **promover** uma **constatação de auditoria interna do tipo "não
  conformidade"** (5a, marcada como promovível) a uma NC formal, reaproveitando dados da constatação e
  registrando o vínculo **bidirecional** (a constatação passa a referenciar a NC via `nonconformity_ref`
  e **permanece ativa** — a promoção não a encerra/arquiva).
- **FR-003**: A promoção MUST ser idempotente: promover a mesma constatação duas vezes NÃO cria NC
  duplicada (resolve a NC existente). Constatações que NÃO são promovíveis (conforme/observação/
  oportunidade) MUST NOT poder ser promovidas.
- **FR-004**: Cada NC MUST registrar **análise de causa raiz** e um **status** entre **aberta**, **em
  andamento**, **em verificação** e **encerrada**, com transições controladas.
- **FR-005**: O sistema MUST permitir criar **ações corretivas** vinculadas a uma NC, cada uma com
  descrição, **responsável** (referência a membro da organização), **prazo** e status próprio.
- **FR-006**: O sistema MUST permitir registrar **verificação de eficácia** da NC (quem verificou,
  quando, resultado eficaz/ineficaz, observações).
- **FR-007**: O encerramento da NC MUST ser bloqueado por um **gate** enquanto não houver verificação de
  eficácia com resultado **eficaz** (e ações obrigatórias concluídas), com mensagem clara.
- **FR-008**: O sistema MUST sinalizar **ações corretivas com prazo vencido** (prazo no passado e não
  concluídas).
- **FR-009**: O sistema MUST oferecer **lista de NCs** filtrável por status, severidade, responsável e
  prazo vencido, com indicadores simples de quantidades.
- **FR-010**: Toda mudança relevante (status, causa raiz, ação, verificação, promoção) MUST preservar
  **trilha append-only** (autor/data/ação); remoção é **lógica**, nunca física.

#### Fase 2 — Análise Crítica pela Direção (9.3)

- **FR-019**: O sistema MUST modelar a análise crítica como **coleção** — **uma por reunião** (cada
  uma com data própria), e MUST permitir manter um histórico de análises críticas por organização ao
  longo do tempo (não há singleton por org).
- **FR-020**: O sistema MUST permitir registrar uma **análise crítica pela direção** com **entradas**
  (status de ações de análises anteriores, mudanças internas/externas, desempenho do SGSI, resultados
  de auditoria, situação dos riscos, NCs e ações corretivas) e **saídas/decisões** (oportunidades de
  melhoria, mudanças no SGSI, necessidade de recursos).
- **FR-021**: A análise crítica MUST ser tratada como **Documento Controlado**: submissão a revisão,
  aprovação por usuário com permissão, **versão imutável** com autor/data, **exportação em PDF** e
  **assinatura avançada opcional** — reusando o ciclo de Documento Controlado existente.
- **FR-022**: A aprovação/congelamento da Ata MUST ser bloqueada por um **gate duro** quando entradas/
  saídas obrigatórias estiverem ausentes; navegar/editar/rascunhar permanece sob **gates suaves**.

#### Fase 3 — Melhoria Contínua / PDCA (10.1)

- **FR-030**: O sistema MUST permitir registrar **melhorias/oportunidades** com origem (auditoria, NC,
  análise crítica, sugestão), descrição, status e (opcional) referência a um artefato que a melhoria
  realimenta (contexto/risco/controle).
- **FR-031**: A referência de realimentação MUST ser **somente leitura** — não cria nem altera o
  artefato/módulo consumido.
- **FR-032**: O sistema MUST oferecer uma **visão de ciclo PDCA** (somente leitura) que exibe o loop
  fechado — auditorias/NCs/análise crítica → melhorias → artefatos realimentados — reusando a
  rastreabilidade/timeline da 5a, sem expor conteúdo sensível.

#### Transversal — Evidências, dashboard, readiness

- **FR-040**: O sistema MUST permitir anexar evidências a **NCs** e **ações corretivas** usando o
  **repositório transversal da 5a**, estendendo o vínculo polimórfico de evidência para os novos tipos
  de alvo ("não conformidade", "ação corretiva") — **sem reimplementar** evidências.
- **FR-041**: O sistema MUST oferecer um **dashboard do módulo** com cards simples: NCs por status/
  severidade, ações corretivas com prazo vencido, melhorias por status e estado do ciclo PDCA.
- **FR-042**: O sistema MUST refletir o **fechamento do PDCA** desta etapa no Dashboard de Conformidade
  (esteira), reusando a camada de agregação existente.

#### Restrições de escopo

- **FR-050**: A feature MUST NOT reimplementar o repositório de evidências nem a auditoria interna
  (vêm da 5a) — apenas consome/estende os pontos previstos (vínculo de evidência extensível e
  constatação promovível).
- **FR-051**: A feature MUST NOT implementar auditoria externa/certificação, nem motor de KPIs/medição
  (9.1, no máximo indicadores simples), nem exclusão física de registros. MUST NOT alterar os módulos
  consumidos (SoA/Risco/Ativo/Contexto/Auditoria) — vínculos são read-only.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado desta feature é escopado à organização. Recursos
  afetados: não conformidade, ação corretiva, verificação de eficácia, trilha de NC, análise crítica
  (e suas versões), melhoria. Acesso cross-tenant ⇒ 404/403 (sem revelar existência) + audit log.
  Promoção, PDCA e dashboards nunca agregam dados de outro tenant (fail-closed).
- **SEC-002 (Papéis e permissões)**: NC/ações/melhorias/PDCA — visualizar exige **view_nonconformity**;
  registrar/tratar (NC, ação, verificação, promoção, melhoria) exige **manage_nonconformity**. Análise
  crítica — visualizar exige **view_management_review**; criar/editar exige **manage_management_review**;
  aprovar/congelar a Ata exige **approve_management_review**. Papéis típicos: Admin da organização,
  Consultor, Gestor, Dono de controle, Auditor interno (visualização). Super Admin só com contexto
  explícito de organização e auditoria.
- **SEC-003 (Auditoria)**: Geram audit log: criação/edição/transição de NC, promoção de constatação,
  criação/conclusão de ação corretiva, verificação de eficácia, encerramento de NC, criação/submissão/
  aprovação/assinatura/exportação da análise crítica, criação/transição de melhoria, e tentativas não
  autorizadas/cross-tenant. Cada registro grava operação, entidade, identificador, usuário, organização
  e resultado — **nunca** PII bruta, conteúdo sensível, tokens ou caminhos internos.
- **SEC-004 (Dados sensíveis)**: NCs e análises críticas podem conter conteúdo sensível do SGSI; o
  sistema **não** grava PII bruta nesses campos e nunca expõe conteúdo sensível em logs, erros ou
  telemetria. Evidências anexadas seguem a proteção da 5a (storage + classificação).
- **SEC-005 (Evidências/versionamento)**: A feature cria/altera artefatos versionáveis: NC + trilha
  append-only, análise crítica como Documento Controlado (versões imutáveis), melhoria com trilha.
  Alterações preservam autor/data/ação; registros anteriores não são apagados; assinatura avançada da
  Ata reusa o motor existente.
- **SEC-006 (Degradação)**: Falha de e-mail/assinatura na aprovação da Ata segue o comportamento já
  definido no Documento Controlado/assinatura (OTP fail-closed). Falha no storage de evidências segue a
  5a (fail-closed por arquivo). Isolamento de tenant é **sempre fail-closed**.

### Key Entities *(include if feature involves data)*

- **Não Conformidade (NC)**: registro central de uma não conformidade da organização (tenant). Atributos
  -chave: código, origem, descrição, severidade, vínculo opcional a artefato (controle SoA/risco/ativo),
  referência opcional à constatação de origem (5a), análise de causa raiz, status, autor/datas.
- **Ação Corretiva**: ação vinculada a uma NC, com descrição, responsável (membro), prazo e status;
  pode ter evidências anexadas.
- **Verificação de Eficácia**: registro da verificação de uma NC (verificador, data, resultado eficaz/
  ineficaz, observações) que governa o gate de encerramento.
- **Evento de NC**: trilha append-only das ações relevantes sobre NC/ação/verificação/promoção.
- **Análise Crítica pela Direção**: **uma por reunião** (coleção; data própria) com entradas e saídas/
  decisões, tratada como Documento Controlado (versões imutáveis, aprovação, PDF, assinatura opcional).
  A organização acumula um histórico de atas ao longo do tempo.
- **Melhoria/Oportunidade**: registro 10.1 com origem, descrição, status e referência opcional de
  realimentação a um artefato (read-only), fechando o PDCA.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários autorizados conseguem registrar uma NC (manual ou **promovida** de uma
  constatação da 5a) com causa raiz, ação corretiva (responsável + prazo) e verificação de eficácia,
  acompanhando o status até o encerramento.
- **SC-002**: 100% das promoções de constatação são idempotentes (sem NC duplicada) e só ocorrem para
  constatações promovíveis (NC maior/menor); a constatação promovida passa a referenciar a NC.
- **SC-003**: O encerramento de uma NC é bloqueado quando não há verificação de eficácia "eficaz" — em
  100% dos casos — com mensagem clara.
- **SC-004**: Ações corretivas com prazo vencido são sinalizadas corretamente na lista/filtros.
- **SC-005**: Usuários conseguem anexar evidências a NCs e ações corretivas pelo repositório da 5a, com
  integridade/classificação/custódia herdadas, sem reimplementar evidências.
- **SC-006**: Uma análise crítica pela direção pode ser registrada, aprovada (com e sem assinatura) e
  exportada em PDF; a aprovação é bloqueada quando incompleta e a versão aprovada é imutável.
- **SC-007**: Melhorias podem ser registradas por origem e a visão de ciclo PDCA exibe o loop fechado
  (somente leitura), sem alterar os módulos consumidos.
- **SC-008**: O dashboard do módulo apresenta NCs por status/severidade, ações com prazo vencido e
  melhorias por status; o Dashboard de Conformidade reflete o fechamento do PDCA desta etapa.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar NC, ação corretiva, análise
  crítica ou melhoria de uma organização à qual não pertence — verificado por teste automatizado de
  isolamento de tenant.

## Dependencies

- **Feature 5a (014) — Evidências + Auditoria Interna**: dependência central. (1) Constatações de
  auditoria do tipo "não conformidade" são **promovidas** a NC (o gancho `nonconformity_ref` +
  `promotable` já foi preparado na 5a). (2) Evidências são anexadas a NCs/ações pelo **repositório
  transversal** (o vínculo polimórfico da 5a é **extensível** para os novos alvos). (3) Reuso da
  rastreabilidade/timeline da 5a para a visão de PDCA.
- **Documento Controlado + versões imutáveis**: reuso para a Ata de Análise Crítica (novo tipo de
  documento) com aprovação e PDF.
- **Feature 003 — Assinatura avançada**: assinatura opcional na aprovação da Ata.
- **Exportação PDF (Feature 005)**: reuso para a Ata.
- **SoA (005) / Riscos (012) / Ativos (011) / Contexto (002)**: alvos **read-only** de vínculo de NC e
  de realimentação de melhoria; **não** são alterados.
- **Dashboard de Conformidade (006)**: recebe o card de fechamento do PDCA.
- **Fundação Multi-Tenant (001)**: auth, RBAC, `tenant_scope`/RLS, audit logs.

## Fechamento do ciclo PDCA (realimentação da esteira)

- **Plan** (Contexto/Risco/SoA) → **Do** (controles/ativos) → **Check** (Gap/Auditoria Interna 5a +
  Análise Crítica 9.3) → **Act** (NCs/ações corretivas 10.2 + Melhorias 10.1) → **realimenta o Plan**.
- O "fechamento" é materializado por: (1) **promoção** de constatações em NCs; (2) **melhorias** com
  referência de realimentação a contexto/risco/controle; (3) a **visão de ciclo PDCA** e a
  **timeline** que tornam o loop visível e auditável. A realimentação é **referência read-only** — a
  decisão de efetivamente revisar um risco/controle continua sendo uma ação do usuário no módulo de
  origem (esta feature não faz write-back automático).

## Assumptions

- A feature reutiliza a fundação multi-tenant, autenticação, RBAC, `tenant_scope`/RLS e audit logs.
- **Promoção de constatação** (resolvido — Clarifications): **1:1 idempotente**; copia tipo/descrição/
  vínculo como semente; preenche o `nonconformity_ref` reservado na 5a; a constatação **permanece
  ativa**. Sem promoção em massa no MVP.
- **Análise crítica** (resolvido): **coleção** — uma por reunião (não singleton por org).
- **Severidade da NC** (resolvido): **Maior / Menor / Observação**.
- **Vínculo NC↔artefato** (resolvido): **um vínculo primário opcional** por NC (tipo+id de controle
  SoA/risco/ativo); múltiplos vínculos ficam para evolução.
- **Realimentação do PDCA** (resolvido): **referência read-only** + visualização (timeline/visão PDCA);
  **sem write-back automático** nos módulos consumidos.
- **Gate de encerramento da NC**: encerrar exige verificação de eficácia "eficaz" (e ações obrigatórias
  concluídas); o que conta como "obrigatória" é parametrizado no planejamento.
- **Extensão do vínculo de evidência**: os novos alvos ("não conformidade", "ação corretiva") são
  acrescentados à taxonomia polimórfica da 5a — sem novo esquema de evidência.
- **Permissões novas**: `view_nonconformity`/`manage_nonconformity` (NC+ações+melhorias+PDCA) e
  `view_management_review`/`manage_management_review`/`approve_management_review` (análise crítica).
- Indicadores do dashboard são contagens/agrupamentos simples — não há motor de KPIs/medição (9.1).
- Esta feature **encerra o MVP da esteira** (PDCA completo); não cobre auditoria externa/certificação.
