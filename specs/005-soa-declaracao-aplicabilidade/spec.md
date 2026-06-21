# Feature Specification: Statement of Applicability (SoA) — Declaração de Aplicabilidade

**Feature Branch**: `005-soa-declaracao-aplicabilidade`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "Módulo de Statement of Applicability (Declaração de Aplicabilidade — SoA) da plataforma SaaS multi-tenant de Gestão de SGSI ISO/IEC 27001:2022. Produz o documento de SoA exigido pela cláusula 6.1.3 d) da norma: para cada um dos 93 controles do Anexo A, a decisão de aplicabilidade, a justificativa de inclusão/exclusão, os riscos tratados e o status de implementação — consolidando os dados do Gap Analysis num documento controlado e exportável."

## Clarifications

### Session 2026-06-21

- Q: Insumo da consolidação — avaliação corrente do Gap Analysis vs. baseline aprovada? → A: Avaliação **corrente** do Gap Analysis (estado vivo dos itens). A SoA congela via seu próprio versionamento de Documento Controlado.
- Q: Mapeamento de status Gap Analysis → status de implementação da SoA na consolidação? → A: Atende→Implementado · Parcial→Em andamento · Não atende→Não iniciado · N/A→Não aplicável · Não avaliado→sem status (vazio, usuário define).
- Q: Detecção de divergência — escopo de campos e base de comparação? → A: Campos consolidados (aplicabilidade, justificativa de exclusão, status, responsável, prazo) comparados contra o **valor vivo atual** do item de Gap (via mapeamento); campos exclusivos da SoA ficam fora; sem snapshot por campo.
- Q: Aprovação da SoA exige assinatura eletrônica? → A: Aprovação simples do Admin + **assinatura eletrônica avançada opcional** (reusa o Motor 003, Lei 14.063/2020), espelhando a baseline do Gap (Módulo 2).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consolidar a SoA a partir do Gap Analysis (Priority: P1)

Como Consultor ou Admin da organização, quero **gerar a Declaração de Aplicabilidade** consolidando
automaticamente os dados do Gap Analysis (Módulo 2), de modo que os 93 controles do Anexo A já
apareçam pré-preenchidos (aplicabilidade, justificativa de exclusão, status, responsável e prazo)
sem redigitação.

**Why this priority**: É o coração da feature e o ganho central — transformar o resultado do Gap
Analysis no documento que a cláusula 6.1.3 d) exige. Sem isso, não há SoA. Sozinha, já entrega uma
SoA completa e consultável.

**Independent Test**: Numa organização com Gap Analysis avaliado, acionar "Gerar/atualizar SoA"
produz uma SoA com **93 itens** (um por controle do Anexo A), cada um com os campos herdados do Gap
Analysis correspondente; controles marcados "Não atende"/"Parcial"/"Atende" mapeiam para status de
implementação coerente, e os marcados "N/A" no Gap chegam como "Não aplicável" com a justificativa
de exclusão pré-carregada.

**Acceptance Scenarios**:

1. **Given** uma organização com avaliação de Gap Analysis preenchida, **When** o usuário aciona a
   geração/atualização da SoA, **Then** a SoA passa a conter os 93 controles do Anexo A, com
   aplicabilidade, justificativa de exclusão, status de implementação, responsável e prazo
   herdados do item de Gap Analysis correspondente.
2. **Given** uma SoA já consolidada e edições manuais feitas nela, **When** o usuário aciona uma
   nova consolidação a partir do Gap Analysis, **Then** o sistema **não sobrescreve silenciosamente**
   os campos editados manualmente — em vez disso sinaliza divergência (ver US5).
3. **Given** uma organização sem Gap Analysis avaliado, **When** o usuário tenta gerar a SoA,
   **Then** o sistema informa que é preciso ter a avaliação de Gap Analysis como insumo (ou gera a
   SoA com os 93 controles em estado "não preenchido", conforme decidido no plano).

---

### User Story 2 - Editar a SoA controle a controle (Priority: P2)

Como Consultor/Admin, quero **editar cada controle da SoA** — decisão de aplicabilidade,
justificativa de inclusão (tipada), justificativa de exclusão, riscos tratados, status de
implementação, responsável, prazo, evidências esperadas/referências e observações — de forma
independente do Gap Analysis, para refinar a declaração até ficar pronta para aprovação.

**Why this priority**: Uma SoA real precisa ser ajustada manualmente (justificativas tipadas,
referências de risco e evidência) além do que o Gap Analysis fornece. Depende de existir a SoA (US1).

**Independent Test**: Editar um controle aplicável exige ao menos **uma razão tipada** de inclusão;
marcar um controle como "Não aplicável" exige **justificativa de exclusão**; salvar persiste os
campos e a edição fica registrada.

**Acceptance Scenarios**:

1. **Given** um controle da SoA, **When** o usuário o marca como "Aplicável" e salva sem nenhuma
   razão de inclusão tipada (risco/legal/contratual/melhor prática), **Then** o sistema rejeita com
   mensagem de validação.
2. **Given** um controle da SoA, **When** o usuário o marca como "Não aplicável" sem justificativa
   de exclusão, **Then** o sistema rejeita com mensagem de validação.
3. **Given** um controle aplicável, **When** o usuário registra razões de inclusão tipadas, riscos
   tratados (ex.: "R01, R02"), status de implementação, responsável, prazo, evidências esperadas e
   referências (ex.: "POL-SI-001"), **Then** os dados são persistidos e exibidos na SoA.

---

### User Story 3 - SoA como Documento Controlado versionado (Priority: P3)

Como Admin da organização, quero **emitir versões imutáveis da SoA** seguindo o ciclo de vida de
documento controlado (rascunho → em revisão → aprovado/em vigor → obsoleto), com identificador,
versão, classificação, datas (emissão e próxima análise crítica) e cadeia elaborado/revisado/
aprovado, para ter rastreabilidade e atender o requisito documental da norma.

**Why this priority**: A SoA é um documento controlado obrigatório; sem versionamento imutável e
aprovação não serve para auditoria de certificação. Reusa o padrão "Documento Controlado SGSI 7.5".

**Independent Test**: Enviar para revisão → aprovar cria uma **versão imutável**; tentar editar/
apagar uma versão anterior é bloqueado (append-only); aprovar sem revisão é negado; aprovação só
pelo papel autorizado.

**Acceptance Scenarios**:

1. **Given** uma SoA em rascunho, **When** o Admin a envia para revisão e depois aprova, **Then** é
   criada uma versão imutável registrando autor, data, natureza da alteração e aprovador, e a SoA
   passa a ter uma versão "em vigor".
2. **Given** uma versão de SoA já emitida, **When** qualquer ator tenta alterá-la ou apagá-la,
   **Then** a operação é bloqueada (append-only) e as versões anteriores permanecem consultáveis.
3. **Given** uma SoA em rascunho (sem revisão), **When** um usuário tenta aprovar diretamente,
   **Then** o sistema nega (conflito de estado); **And** um usuário sem o papel de aprovação que
   tenta aprovar recebe 403.

---

### User Story 4 - Exportar a SoA de uma versão específica (Priority: P4)

Como Auditor interno, Consultor ou Admin, quero **exportar a SoA em formato de documento (PDF)**
correspondendo exatamente a uma versão selecionada, para entregar ao auditor de certificação o
artefato que ele solicita.

**Why this priority**: O documento exportado é o entregável final consumido fora da plataforma.
Depende de existir conteúdo (US1/US2) e versões (US3).

**Independent Test**: Exportar a versão aprovada gera um documento cujo conteúdo bate exatamente com
o snapshot daquela versão (não com o rascunho atual); exportar uma versão antiga reflete o conteúdo
daquela época.

**Acceptance Scenarios**:

1. **Given** uma SoA com uma versão aprovada e um rascunho com edições posteriores, **When** o
   usuário exporta a versão aprovada, **Then** o documento reflete o conteúdo da versão aprovada, não
   o do rascunho atual.
2. **Given** múltiplas versões emitidas, **When** o usuário seleciona uma versão anterior e exporta,
   **Then** o documento corresponde exatamente àquela versão.
3. **Given** uma exportação, **When** ela é concluída, **Then** a ação é registrada em audit log.

---

### User Story 5 - Sinalização de divergência SoA × Gap Analysis (Priority: P5)

Como Consultor/Admin, quero **ver onde a SoA diverge do Gap Analysis de origem**, para decidir
conscientemente quando reconciliar — sem que nenhum dos dois seja sobrescrito silenciosamente.

**Why this priority**: Garante coerência e rastreabilidade entre os dois artefatos sem acoplá-los
rigidamente. Depende de US1 (origem) e US2 (edição independente).

**Independent Test**: Após editar manualmente na SoA um campo que veio do Gap Analysis, o controle
correspondente fica marcado como "divergente"; reconsolidar não apaga a edição — apenas sinaliza.

**Acceptance Scenarios**:

1. **Given** um controle cujo status na SoA foi editado manualmente diferindo do Gap Analysis de
   origem, **When** o usuário visualiza a SoA, **Then** o controle é sinalizado como divergente,
   mostrando o valor da SoA e o valor de origem do Gap Analysis.
2. **Given** um controle divergente, **When** o usuário opta por reconciliar com o Gap Analysis,
   **Then** o valor de origem é aplicado **explicitamente** (ação do usuário), nunca de forma
   automática/silenciosa.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar/exportar a SoA,
   um item de SoA ou uma versão de SoA que pertence à Organização B, **Then** o sistema nega
   (404/403 sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas a SoA e os controles da Organização A são visíveis/alteráveis.

### Edge Cases

- O que acontece ao consolidar quando o Gap Analysis tem controles "não preenchidos"? (Esperado:
  o item da SoA fica em estado correspondente e não força um status de implementação inventado.)
- Como a SoA lida com controles **personalizados/descontinuados** do catálogo da organização (a
  cópia editável do Módulo 2 pode ter itens custom além dos 93 do Anexo A padrão)?
- O que acontece se o Gap Analysis for **re-adotado** (nova versão do seed) depois da SoA existir?
- O que acontece ao exportar uma SoA que ainda não tem nenhuma versão aprovada (só rascunho)?
- O que acontece com a SoA quando a organização (tenant) é suspensa?
- Marcar como "Não aplicável" um controle que no Gap Analysis estava como "Atende" (divergência
  legítima) — deve ser permitido com justificativa, e sinalizado.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST manter **uma SoA por organização**, cobrindo os controles do Anexo A
  do catálogo de Gap Analysis adotado pela organização (93 controles padrão + eventuais itens
  personalizados de Anexo A da organização).
- **FR-002**: O sistema MUST permitir **gerar/atualizar a SoA a partir da avaliação corrente do Gap
  Analysis** (estado vivo dos itens, não uma baseline congelada), pré-preenchendo por controle:
  aplicabilidade, justificativa de exclusão, status de implementação, responsável e prazo, derivados
  do item de Gap Analysis correspondente.
- **FR-002a (mapeamento de status na consolidação)**: O status do Gap Analysis MUST mapear para o
  status de implementação da SoA assim: **Atende→Implementado**, **Parcial→Em andamento**, **Não
  atende→Não iniciado**, **N/A→Não aplicável**, **Não avaliado→sem status** (deixado vazio para o
  usuário definir; nunca inventar um valor). A aplicabilidade deriva: **N/A ⇒ Não aplicável**;
  qualquer outro status ⇒ **Aplicável = Sim**.
- **FR-003**: Para cada controle, o sistema MUST registrar: ID do controle (ex.: A.5.1), tema
  (Organizacional/Pessoas/Físico/Tecnológico), nome; **Aplicável (Sim/Não)**; justificativa de
  inclusão; justificativa de exclusão; riscos tratados; status de implementação; responsável; prazo
  de conclusão; evidências objetivas esperadas + referências a documentos/evidências; observações.
- **FR-004**: A **justificativa de inclusão** MUST registrar ao menos uma **razão tipada** para
  controles aplicáveis, dentre: resultado do tratamento de riscos | requisito legal/regulatório |
  requisito contratual | melhor prática/requisito de negócio; texto livre complementar é permitido.
- **FR-005**: A **justificativa de exclusão** MUST ser obrigatória quando o controle for marcado
  "Não aplicável" (pré-carregada do Gap Analysis quando existir).
- **FR-006**: O **status de implementação** MUST ser um entre: Implementado | Em andamento |
  Planejado | Não iniciado | Não aplicável.
- **FR-007**: O campo **riscos tratados** MUST aceitar referências rastreáveis aos riscos que o
  controle mitiga (ex.: "R01, R02"), sem depender do Módulo de Riscos (ainda inexistente) — apenas
  referência textual rastreável.
- **FR-008**: O campo **evidências esperadas/referências** MUST aceitar descrição textual do que
  comprova o controle e referências a documentos/evidências (ex.: "POL-SI-001"), sem upload de
  arquivo (Módulo de Evidências) — apenas referência rastreável.
- **FR-009**: Todos os campos da SoA MUST ser **editáveis manualmente**, de forma independente do
  Gap Analysis.
- **FR-010**: O sistema MUST detectar divergência **apenas nos campos consolidados** (aplicabilidade,
  justificativa de exclusão, status de implementação, responsável, prazo), comparando o valor da SoA
  contra o **valor vivo atual** do item de Gap Analysis correspondente (aplicando o mapeamento de
  status do FR-002a); campos exclusivos da SoA (razões de inclusão, riscos tratados, evidências,
  observações) ficam fora da detecção. Não é necessário snapshot por campo. Ao divergir, o sistema
  MUST sinalizar (exibindo valor da SoA e valor vivo do Gap) **sem sobrescrever silenciosamente**
  nenhum dos dois.
- **FR-011**: A reconciliação de uma divergência (aplicar o valor vivo atual do Gap Analysis ao
  campo da SoA) MUST ocorrer apenas por **ação explícita** do usuário.
- **FR-012**: A SoA MUST seguir o padrão **Documento Controlado SGSI (7.5)**: identificador, versão,
  status (rascunho → em revisão → aprovado/em vigor → obsoleto), classificação, datas de emissão e
  próxima análise crítica, e cadeia elaborado/revisado/aprovado.
- **FR-013**: O versionamento MUST ser **append-only**: cada emissão/revisão é uma versão imutável
  (autor, data, natureza da alteração, aprovador); versões anteriores permanecem consultáveis e
  nunca são alteradas ou apagadas.
- **FR-014**: A **aprovação** da SoA MUST ser restrita ao papel autorizado (Admin da organização);
  aprovar uma SoA que não passou por revisão MUST ser negado (conflito de estado). A aprovação MAY
  ser acompanhada de **assinatura eletrônica avançada opcional** (Lei 14.063/2020), reusando o Motor
  de Workflow (Módulo 3) — espelhando a baseline do Gap Analysis; a assinatura, quando feita, vincula
  o signatário e sela a integridade da versão emitida.
- **FR-015**: O sistema MUST permitir **exportar a SoA** em formato de documento (PDF) refletindo
  **exatamente** uma versão selecionada (não o rascunho corrente, salvo se a versão escolhida for o
  rascunho).
- **FR-016**: Cada controle da SoA MUST ser **rastreável** até o item correspondente do Gap Analysis
  (Módulo 2); as referências de riscos e evidências preparam a rastreabilidade para os módulos
  futuros (Riscos, Evidências).
- **FR-017**: O sistema MUST registrar em **audit log** toda emissão, edição, mudança de status,
  consolidação a partir do Gap Analysis e exportação — sem PII/conteúdo sensível.
- **FR-018**: Acesso à SoA e a seus itens/versões MUST respeitar a **política de acesso por
  classificação** da organização (reusa o mecanismo do Módulo 1), além do RBAC.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado é escopado pela organização do usuário. Recursos
  afetados: **SoA**, **item de SoA (por controle)** e **versão de SoA**. Acesso cross-tenant ⇒
  **404/403 sem revelar existência** + audit log. Isolamento é sempre fail-closed.
- **SEC-002 (Papéis e permissões)**: Visualizar/exportar: Admin da organização, Consultor, Gestor,
  Auditor interno, Cliente (com permissão). Editar/consolidar: Admin da organização e Consultor.
  Aprovar/emitir versão em vigor: **Admin da organização**. Permissões: `view_soa`, `manage_soa`,
  `approve_soa`.
- **SEC-003 (Auditoria)**: Geram audit log: consolidar do Gap Analysis, criar/editar item, mudar
  aplicabilidade/status, enviar para revisão, aprovar, emitir versão, exportar. Cada registro grava
  operation, entity_type, entity_id, user_id e **nunca** PII/conteúdo confidencial da SoA.
- **SEC-004 (Dados sensíveis)**: A SoA **não** trata PII diretamente, mas seu conteúdo
  (justificativas, riscos, referências) é **confidencial de negócio**. Proteção: rótulo de
  classificação + política de acesso por classificação (reusa Módulo 1); conteúdo nunca em
  logs/erros.
- **SEC-005 (Evidências/versionamento)**: Sim — a SoA é artefato versionável. Versões são
  **append-only** e preservam autor/data/natureza/aprovador (reusa `document_versions`).
- **SEC-006 (Degradação)**: Falha na geração/exportação do documento (PDF) ⇒ a operação falha de
  forma limpa e auditável, sem corromper a SoA nem suas versões (fail-closed na exportação).
  Isolamento de tenant permanece fail-closed.

### Key Entities *(include if feature involves data)*

- **SoA (Declaração de Aplicabilidade)**: artefato **único por organização** (tenant_id → Organization).
  Liga-se à avaliação de Gap Analysis de origem. Atributos: identificador do documento controlado,
  status de rascunho, ponteiro para versão em vigor (`current_version_id`), classificação, datas de
  emissão e próxima análise crítica.
- **SoAItem (controle da SoA)**: um por controle do Anexo A (tenant_id). Referencia o item de Gap
  Analysis / item de catálogo de origem. Atributos: ID/tema/nome do controle; aplicável (Sim/Não);
  razões de inclusão tipadas (+ texto livre); justificativa de exclusão; status de implementação;
  responsável; prazo; riscos tratados (referências); evidências esperadas + referências;
  observações; indicadores de divergência vs. origem.
- **SoAVersion**: snapshot **imutável** de uma emissão (reusa o padrão `document_versions`,
  append-only): autor, data, natureza da alteração, aprovador, e o conteúdo congelado dos 93+
  controles daquela versão (base da exportação).
- **Razão de inclusão (tipo)**: enumeração — resultado de tratamento de riscos | legal/regulatório |
  contratual | melhor prática/negócio.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A partir de um Gap Analysis avaliado, o usuário **gera uma SoA completa dos 93
  controles** do Anexo A numa única ação, sem redigitar dados já existentes no Gap Analysis.
- **SC-002**: 100% dos controles marcados "Não aplicável" possuem justificativa de exclusão e 100%
  dos controles "Aplicável" possuem ao menos uma razão de inclusão tipada antes de a SoA poder ser
  aprovada.
- **SC-003**: Uma versão aprovada da SoA é **imutável**: nenhuma edição/exclusão posterior altera o
  conteúdo daquela versão — verificável por teste automatizado.
- **SC-004**: O documento exportado de uma versão selecionada corresponde **exatamente** ao conteúdo
  daquela versão (e não ao rascunho corrente).
- **SC-005**: Toda divergência entre SoA e Gap Analysis de origem é **visível** ao usuário e nenhuma
  reconciliação ocorre sem ação explícita.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar, exportar ou alterar a SoA (ou seus
  itens/versões) de uma organização à qual não pertence — verificado por teste automatizado de
  isolamento de tenant.

## Assumptions

- **Reutiliza a fundação multi-tenant** (auth + RBAC + `tenant_scope` + RLS + auditoria) e o padrão
  **Documento Controlado SGSI (7.5)** já implementados (Módulos 1 e 2).
- **Insumo = avaliação de Gap Analysis corrente** da organização (Módulo 2), decidido no clarify
  (não uma baseline congelada). A SoA torna-se ela própria o artefato congelável via seu
  versionamento de Documento Controlado.
- **Uma SoA por organização** (índice único por tenant), coerente com o padrão "1 conjunto por org"
  dos Módulos 1 e 2.
- **Aprovação só pelo Admin da organização** (`approve_soa`), espelhando `approve_context_document`
  e `approve_gap_baseline`; **assinatura eletrônica avançada é opcional** na emissão (reusa Motor 003).
- **Exportação primária em PDF**; outros formatos ficam fora de escopo nesta feature.
- **Riscos tratados** e **referências de evidência** são, nesta fase, **referências textuais
  rastreáveis** — o vínculo efetivo virá com o Módulo de Riscos e o Módulo de Evidências.
- O catálogo de Anexo A da organização (cópia editável do Módulo 2) é a fonte da lista de controles;
  itens personalizados de Anexo A da organização, se existirem, também entram na SoA.

### Dependencies / Out of Scope

- **Fora de escopo**: cadastro/cálculo de riscos e plano de tratamento (Módulo de Riscos) — a SoA
  apenas referencia; upload/versionamento de arquivos de evidência (Módulo de Evidências) — a SoA
  apenas referencia; geração de rascunho de SoA por IA (Módulo de IA, opt-in futuro).
