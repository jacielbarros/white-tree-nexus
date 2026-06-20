# Feature Specification: Motor de Workflow de Preenchimento (atribuível e assinável)

**Feature Branch**: `003-workflow-preenchimento`

**Created**: 2026-06-20

**Status**: Draft

**Input**: User description: "Motor de Workflow de Preenchimento (atribuível e assinável) — capacidade
transversal e reutilizável que envolve qualquer formulário de fase do SGSI: o consultor monta um
template parametrizável, atribui a um preenchedor (membro ou externo via link tokenizado), que é
notificado por e-mail, assume, preenche (com salvamento parcial), envia, e o formulário é assinado
eletronicamente (Lei 14.063/2020, nível avançada) gerando uma versão imutável; todo o fluxo tem
trilha append-only apresentada como wizard. O Diagnóstico (Cláusula 4) é o 1º consumidor."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): plataforma SaaS MULTI-TENANT. Toda feature de domínio
  especifica isolamento de tenant, auditoria e tratamento de dados sensíveis. Stack fica no /plan.
-->

## Clarifications

### Session 2026-06-20

- Q: Editar um template depois de atribuí-lo afeta as atribuições já criadas? → A: **Não** — a
  atribuição congela um **snapshot** dos campos do template no momento da atribuição; edições
  posteriores do template não afetam atribuições existentes.
- Q: Quem precisa assinar para selar o formulário? → A: **Configurável por organização** — padrão é
  **assinatura única do preenchedor** (sela e torna imutável); a organização pode **exigir
  contra-assinatura do atribuidor** para concluir.
- Q: Como o respondente **externo** comprova identidade ao assinar (nível avançada)? → A: Vínculo
  e-mail + token + nome informado + carimbo de tempo + IP/origem **mais um código OTP enviado ao
  e-mail no ato da assinatura** (comprova controle do e-mail).
- Q: Há campos obrigatórios e completude exigida no envio/assinatura? → A: **Sim** — campos podem ser
  marcados como obrigatórios no template; **enviar** exige todos os obrigatórios preenchidos e
  **assinar** exige um envio válido.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Atribuir e preencher (membro) (Priority: P1) 🎯 MVP

Um Consultor (ou Admin da organização) monta um template de formulário e o **atribui** a um membro
da organização (um Cliente, outro Consultor, ou a si mesmo), opcionalmente com prazo e instruções.
O preenchedor é notificado por e-mail, **assume** o preenchimento, preenche os campos (podendo salvar
parcialmente e retomar depois sem perder nada) e **envia**.

**Why this priority**: É o laço central do produto — sem atribuir + preencher + enviar não há
workflow. Entrega valor sozinho (delegar o preenchimento a quem tem o conhecimento).

**Independent Test**: criar um template, atribuir a um membro, ver o status `pendente` e o e-mail
disparado; como o membro, assumir (`em preenchimento`), salvar parcial, sair, retomar sem perda,
enviar (`preenchido`); um usuário de outra organização não enxerga nada disso.

**Acceptance Scenarios**:

1. **Given** um Consultor com um template, **When** ele atribui a um membro com prazo, **Then** a
   atribuição fica `pendente`, o preenchedor é registrado e uma notificação por e-mail é disparada.
2. **Given** uma atribuição `pendente`, **When** o preenchedor a assume, **Then** o status vira
   `em preenchimento` e fica registrado quem assumiu e quando.
3. **Given** um preenchimento em andamento, **When** o preenchedor salva parcialmente e retorna mais
   tarde, **Then** os dados anteriores são recuperados sem perda.
4. **Given** um preenchimento completo, **When** o preenchedor envia, **Then** o status vira
   `preenchido` e o atribuidor é notificado.

---

### User Story 2 - Preenchedor externo via link (Priority: P2)

O preenchedor pode ser alguém **sem conta** na plataforma. O Consultor atribui informando um e-mail;
o sistema gera um **link com token** (apenas o hash do token é guardado; o link expira). O respondente
externo acessa pelo link, preenche e envia — sem se cadastrar — e enxerga **apenas** a atribuição
dele.

**Why this priority**: muitos clientes preenchem sem virar usuários plenos; reduz atrito de adoção.

**Independent Test**: atribuir a um e-mail externo; receber/registrar o link tokenizado; acessar pelo
token, preencher e enviar; token expirado ou inválido é recusado; o link não dá acesso a nenhum outro
dado da organização.

**Acceptance Scenarios**:

1. **Given** uma atribuição a um e-mail externo, **When** criada, **Then** um link com token é gerado
   (só o hash é persistido) e enviado por e-mail, com expiração.
2. **Given** um link válido e não expirado, **When** o respondente externo o acessa, **Then** ele vê
   somente a sua atribuição e pode preencher/enviar.
3. **Given** um link expirado/revogado/inválido, **When** acessado, **Then** o acesso é negado sem
   revelar a existência de outros dados.

---

### User Story 3 - Assinatura eletrônica avançada (Priority: P3)

Após o preenchimento, o formulário pode ser **assinado eletronicamente** (nível *avançada*, Lei
14.063/2020): vincula a identidade do signatário, registra carimbo de tempo e gera um **selo de
integridade** do conteúdo. A assinatura **congela uma versão imutável** do preenchimento. Qualquer
alteração posterior do conteúdo torna-se detectável ao recomputar o selo.

**Why this priority**: dá valor jurídico/probatório e fecha o ciclo do documento controlado.

**Independent Test**: assinar um formulário `preenchido`; verificar que o status vira `assinado`, que
uma versão imutável foi criada com selo de integridade, e que recomputar o selo sobre o conteúdo
assinado confere; uma adulteração do conteúdo é detectada.

**Acceptance Scenarios**:

1. **Given** uma atribuição `preenchido`, **When** o signatário autorizado assina, **Then** registra-se
   a identidade do signatário, o carimbo de tempo e o selo de integridade, e gera-se uma versão imutável.
2. **Given** uma versão assinada, **When** se recomputa o selo sobre o conteúdo assinado, **Then** ele
   confere; **When** o conteúdo é alterado, **Then** a verificação acusa divergência.
3. **Given** uma versão `assinado`, **When** alguém tenta editá-la/excluí-la, **Then** a operação é
   recusada (histórico append-only).

---

### User Story 4 - Trilha, wizard, devolução e cancelamento (Priority: P4)

Todo o histórico do fluxo (atribuição, notificações, assunção, salvamentos, envio, devolução,
assinatura, conclusão) é preservado de forma **imutável** e apresentado como **linha do tempo /
wizard** dos passos. O atribuidor pode **devolver** um formulário enviado para ajustes (volta a
`em preenchimento`) ou **cancelar** a atribuição.

**Why this priority**: rastreabilidade e correção de rota são exigências de auditoria do SGSI.

**Independent Test**: percorrer o fluxo e ver a linha do tempo completa e ordenada; devolver um
`preenchido` (volta a `em preenchimento` com registro do motivo) e reenviar; cancelar uma atribuição.

**Acceptance Scenarios**:

1. **Given** uma atribuição em qualquer estado, **When** se consulta sua trilha, **Then** todos os
   eventos aparecem em ordem cronológica, com quem e quando, sem expor o conteúdo das respostas.
2. **Given** uma atribuição `preenchido`, **When** o atribuidor a devolve, **Then** volta a
   `em preenchimento`, registra-se o evento (e motivo) e o preenchedor é notificado.
3. **Given** uma atribuição não concluída, **When** o atribuidor a cancela, **Then** o status vira
   `cancelado` e fica registrado.

---

### User Story 5 - Diagnóstico como primeiro consumidor (Priority: P5)

O **Diagnóstico de Contexto (Cláusula 4)** passa a ser preenchido por este fluxo: o preenchimento
**assinado** torna-se a fonte do diagnóstico vigente da organização e continua alimentando as
**sugestões heurísticas** da visão consolidada (sem aplicação automática — só via aceite).

**Why this priority**: conecta o motor genérico ao módulo existente, validando o reuso end-to-end.

**Independent Test**: atribuir/preencher/assinar um template do tipo *diagnóstico*; verificar que o
diagnóstico vigente da organização reflete as respostas assinadas e que as sugestões continuam
disponíveis sob aceite.

**Acceptance Scenarios**:

1. **Given** um template do tipo *diagnóstico* preenchido e assinado, **When** concluído, **Then** o
   diagnóstico vigente da organização passa a refletir essas respostas.
2. **Given** um diagnóstico assinado que indica tratamento de dados pessoais, **When** se abre a visão
   consolidada, **Then** as sugestões correspondentes aparecem e só persistem após aceite.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar um template,
   atribuição, trilha ou versão assinada que pertence à Organização B, **Then** o sistema nega
   (404/403 sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas templates/atribuições da Organização A são visíveis/alteráveis.
3. **Given** um link tokenizado de uma atribuição da Organização A, **When** usado, **Then** dá acesso
   **somente** àquela atribuição — nunca a outros dados da Organização A ou de qualquer outra.

### Edge Cases

- **Token expirado/revogado**: acesso externo negado sem revelar existência; pode ser reemitido pelo atribuidor.
- **Edição após assinatura**: bloqueada — a versão assinada é imutável; mudanças exigem nova atribuição/versão.
- **Preenchedor sem direito**: usuário que não é o designado (nem porta o token) não acessa o preenchimento.
- **Falha de SMTP**: notificação é best-effort (fail-soft) — não bloqueia a atribuição; o evento de "notificação tentada" fica na trilha.
- **Prazo vencido**: a atribuição é **sinalizada** como atrasada (não é bloqueada automaticamente).
- **Organização suspensa**: operações de domínio da organização ficam indisponíveis (fail-closed), inclusive o link externo.
- **Reatribuição/transferência**: o atribuidor pode cancelar e recriar; o histórico de ambas permanece.

## Requirements *(mandatory)*

### Functional Requirements

**Template**
- **FR-001**: O sistema MUST permitir a um Consultor/Admin criar e editar um **template** de formulário
  como conjunto de campos por seção, cada campo com rótulo, tipo (texto, sim/não, número, seleção) e
  indicador de **obrigatoriedade**, e um **tipo de template** (diagnóstico, gap analysis, genérico).
- **FR-002**: Personalizar o template de uma organização MUST NOT afetar o de qualquer outra.

**Atribuição e notificação**
- **FR-003**: O sistema MUST permitir criar uma **atribuição** de um template a um preenchedor, com
  prazo opcional e instruções.
- **FR-004**: O preenchedor MUST poder ser (a) um membro da organização (Cliente/Consultor, inclusive
  o próprio atribuidor) ou (b) um respondente **externo** identificado por e-mail e acessível por
  **link com token** — sem exigir conta; apenas o **hash** do token é persistido e o link **expira**.
- **FR-005**: Ao atribuir (e em lembretes), o sistema MUST notificar o preenchedor por **e-mail**,
  com entrega **best-effort** (a falha de envio não derruba a operação).

**Ciclo de vida**
- **FR-006**: O sistema MUST gerir a máquina de estados: `rascunho → pendente → em_preenchimento →
  preenchido → assinado → concluído`, além de `devolvido` (volta a `em_preenchimento`) e `cancelado`,
  permitindo apenas as transições válidas.
- **FR-007**: Ao **assumir**, o sistema MUST mudar o status para `em_preenchimento` e registrar quem
  assumiu e quando.
- **FR-008**: O preenchedor MUST poder salvar parcialmente e retomar sem perda de dados.
- **FR-009**: O preenchedor MUST poder **enviar** (→ `preenchido`); o atribuidor MUST poder
  **devolver** (→ `em_preenchimento`, com motivo) e **cancelar** (→ `cancelado`).
- **FR-009a**: O **envio** MUST exigir que todos os campos **obrigatórios** do snapshot estejam
  preenchidos; a **assinatura** MUST exigir um envio válido (formulário em `preenchido`).
- **FR-010**: Cada transição MUST registrar autor e carimbo de tempo (UTC).
- **FR-019**: Uma atribuição com prazo vencido MUST ser sinalizada como atrasada (sem bloqueio automático).

**Assinatura**
- **FR-011**: O sistema MUST permitir assinar eletronicamente (nível **avançada**, Lei 14.063/2020),
  vinculando a identidade do signatário, carimbo de tempo e um **selo de integridade** do conteúdo.
- **FR-011a**: A **política de assinatura** MUST ser configurável por organização: o padrão é
  **assinatura única do preenchedor** (que sela e torna imutável); a organização MAY exigir
  **contra-assinatura do atribuidor** — neste caso, a conclusão só ocorre após ambas as assinaturas.
- **FR-011b**: Para um **membro**, a identidade do signatário MUST vir da sessão autenticada. Para um
  **respondente externo**, a assinatura avançada MUST vincular e-mail + posse do token + nome
  informado + carimbo de tempo + IP/origem **e** exigir a confirmação de um **código OTP enviado ao
  e-mail** no ato da assinatura (comprova controle do e-mail). A entrega desse OTP é um **gate de
  segurança** (fail-closed: sem OTP confirmado, não há assinatura), distinta das notificações
  best-effort.
- **FR-012**: A assinatura MUST congelar uma **versão imutável** do preenchimento (histórico
  append-only; não pode ser editada/excluída).
- **FR-013**: O sistema MUST permitir **verificar** a integridade: recomputar o selo sobre o conteúdo
  assinado confere; qualquer alteração posterior é detectável.
- **FR-014**: Esta feature MUST NOT exigir certificado digital ICP-Brasil (nível *qualificada* fora de escopo).

**Trilha e visão**
- **FR-015**: O sistema MUST manter, por atribuição, uma **trilha append-only** de todos os eventos do
  fluxo, apresentável como **linha do tempo / wizard**.
- **FR-016**: A trilha MUST registrar os **eventos** (quem/quando/tipo), nunca o conteúdo sensível das respostas.

**Permissões e visibilidade**
- **FR-017**: O sistema MUST restringir: atribuir/gerir/devolver/cancelar a **Consultor/Admin**;
  preencher/enviar ao **preenchedor designado** (membro) ou ao **portador do token**; assinar ao
  preenchedor e/ou atribuidor; visualizar a usuários da organização com permissão; o respondente
  externo vê **apenas** a sua atribuição.

**Consumo pelo Diagnóstico**
- **FR-018**: O Diagnóstico de Contexto (Cláusula 4) MUST passar a ser preenchido por este fluxo: o
  preenchimento **assinado** torna-se a fonte do diagnóstico vigente da organização e continua
  alimentando as sugestões heurísticas (sem aplicação automática — apenas via aceite).

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado é escopado pela organização. Recursos afetados:
  **template de formulário, atribuição, respostas, trilha de eventos, assinatura, versão assinada**.
  Acesso cross-tenant ⇒ **404/403** (sem revelar existência) + audit log. O link tokenizado dá acesso
  **somente** à atribuição correspondente.
- **SEC-002 (Papéis e permissões)**: Atribuir/gerir/devolver/cancelar: **Admin da organização,
  Consultor**. Preencher/enviar: o **preenchedor designado** (ex.: Cliente, Consultor) ou portador do
  token externo. Assinar: preenchedor e/ou atribuidor. Visualizar: papéis com permissão. Permissões
  necessárias: `assign_form`, `fill_form`, `sign_form`, `view_form`. (Super Admin: bypass de permissão,
  nunca de auditoria.)
- **SEC-003 (Auditoria)**: Geram audit log: criar/editar template, atribuir, notificar, assumir,
  salvar, enviar, devolver, cancelar, assinar, concluir, e tentativa cross-tenant. Cada registro grava
  operation/entity_type/entity_id/user_id e **nunca** PII/segredos (token, conteúdo das respostas).
- **SEC-004 (Dados sensíveis)**: **Sim** — as **respostas** podem conter PII/dado confidencial. Ficam
  na entidade de preenchimento (e no snapshot imutável), **nunca** na trilha de auditoria nem em
  logs/erros. O **token** do link nunca é persistido em claro (apenas o hash).
- **SEC-005 (Evidências/versionamento)**: **Sim** — a assinatura cria uma **versão imutável**
  (append-only) que preserva autor/data/ação e o selo de integridade; reusa o padrão de Documento
  Controlado SGSI.
- **SEC-006 (Degradação)**: E-mail/SMTP em falha ⇒ **fail-soft** (best-effort; a operação não cai e o
  evento de tentativa fica na trilha). Validação de token e isolamento de tenant ⇒ **fail-closed**.

### Key Entities *(include if feature involves data)*

- **FormTemplate**: definição parametrizável (campos por seção: rótulo + tipo + obrigatoriedade) e o
  **tipo** do template (diagnóstico/gap analysis/genérico). Pertence a Organization via `tenant_id`.
- **FormAssignment**: instância do workflow — **snapshot dos campos do template** (congelado no
  momento da atribuição; editar o template depois não altera atribuições existentes) + referência ao
  template de origem, **preenchedor** (membro **ou** e-mail externo + hash de token + expiração),
  status (máquina de estados), prazo, instruções,
  **respostas** (conteúdo preenchido), marcas de tempo (atribuição/assunção/envio/assinatura) e
  ponteiro para a versão assinada. Pertence a Organization via `tenant_id`.
- **FormAssignmentEvent**: registro **append-only** de cada evento do fluxo (tipo, autor, data/hora,
  nota), por atribuição — alimenta a trilha/wizard. Pertence a Organization via `tenant_id`.
- **FormSignature**: assinatura **avançada** (identidade do signatário, **papel do signatário**
  — preenchedor ou atribuidor contra-assinante —, carimbo de tempo, **selo de integridade/hash** do
  conteúdo, metadados de origem), append-only; suporta 1 ou 2 assinaturas conforme a política da
  organização (FR-011a). Pertence a Organization via `tenant_id`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das atribuições percorrem `pendente → em_preenchimento → preenchido` sem perda de
  dados entre salvamentos parciais.
- **SC-002**: Um respondente **sem conta** consegue preencher e enviar uma atribuição apenas pelo link
  tokenizado, e nunca acessa qualquer outro dado da organização.
- **SC-003**: Para todo formulário assinado, a verificação de integridade **confere** sobre o conteúdo
  assinado e **acusa** qualquer alteração posterior em 100% dos casos.
- **SC-004**: A trilha de qualquer atribuição reconstrói o fluxo completo (quem/quando de cada passo)
  e é exibível como linha do tempo, sem expor o conteúdo das respostas.
- **SC-005**: O preenchedor é notificado por e-mail ao ser atribuído; quando o e-mail falha, a
  atribuição continua válida e o fato fica registrado.
- **SC-006**: Um diagnóstico preenchido e assinado por este fluxo torna-se a fonte do diagnóstico
  vigente da organização e mantém as sugestões disponíveis sob aceite.
- **SC-ISO (mandatory)**: Nenhum usuário (nem portador de token) consegue ler, listar ou alterar dado
  de uma organização/atribuição à qual não tem direito — verificado por teste automatizado de
  isolamento de tenant.

## Assumptions

- Reutiliza a **fundação multi-tenant** (auth + RBAC + `tenant_scope` + auditoria + RLS) e o padrão
  **Documento Controlado SGSI** (versões imutáveis), a **mecânica de convite por token** (apenas hash,
  expiração) e o **serviço de e-mail** best-effort — todos já implementados (Features 001/002).
- **Assinatura "avançada"**: a identidade do signatário membro vem da sessão autenticada; para o
  respondente externo, a identidade é o vínculo e-mail + token + nome informado no ato + carimbo de
  tempo + origem **+ confirmação por código OTP enviado ao e-mail no ato da assinatura** (FR-011b).
  **Nível qualificada (ICP-Brasil) está fora de escopo.**
- **Quem assina**: por padrão, a assinatura do preenchedor sela o formulário; a exigência de
  contra-assinatura pelo atribuidor é opcional/configurável pela organização (regra simples no v1).
- **Imutabilidade**: uma atribuição `assinado/concluído` não é editada; correções geram nova atribuição
  (nova versão). Versões anteriores permanecem no histórico.
- **Template parametrizável** reutiliza o *form-builder* já existente como ferramenta de autoria; o
  preenchedor vê o mesmo formulário em modo resposta (somente valores).
- O **Diagnóstico** (Cláusula 4) é o **primeiro consumidor**; o conteúdo específico do **Gap Analysis**
  virá na feature seguinte (004), consumindo este motor.
- Prazo é **sinalizador** (atrasado), não bloqueio automático.
