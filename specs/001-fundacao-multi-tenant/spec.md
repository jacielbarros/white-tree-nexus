# Feature Specification: Fundação Multi-Tenant (Organizações, Autenticação, RBAC, Isolamento e Auditoria)

**Feature Branch**: `001-fundacao-multi-tenant`

**Created**: 2026-06-18

**Status**: Draft

**Input**: User description: "Plataforma SaaS multi-tenant de Gestão de SGSI e Compliance ISO/IEC 27001:2022. Primeira feature: FUNDAÇÃO — gestão de organizações (tenants), autenticação, RBAC, isolamento de dados entre organizações e trilha de auditoria. Nenhum módulo de negócio entra aqui — só a base."

<!--
  CONSTITUTION REMINDER (White Tree Nexus): esta é uma plataforma SaaS MULTI-TENANT.
  Toda feature que toca dados de domínio DEVE especificar comportamento de isolamento de
  tenant, auditoria e tratamento de dados sensíveis. NÃO especificar stack/tecnologia aqui.
-->

## Clarifications

### Session 2026-06-18

- Q: Modelo de pertença (membership) e papel por pessoa — quantos vínculos uma pessoa pode ter? → A: Restritivo/literal — o papel vive no vínculo; **apenas o papel Consultor** permite múltiplos vínculos; qualquer pessoa com vínculo de outro papel pertence a **exatamente uma** organização.
- Q: Como o primeiro administrador de uma organização recém-criada é estabelecido? → A: O Super Admin **convida** o Admin inicial (ou um Consultor) pela organização nova usando o fluxo de convite normal (sem caminho especial de criação de conta).
- Q: Como o bloqueio de conta (após falhas de login) é removido? → A: Ambos — auto-expiração após uma janela configurável **e** desbloqueio manual por admin autorizado (Admin da organização / Super Admin); uma redefinição de senha bem-sucedida também limpa o bloqueio.
- Q: Quem pode criar/onboarding de novas organizações? → A: **Apenas o Super Admin** da plataforma; Consultores são convidados para organizações já existentes (autosserviço fica fora de escopo desta fundação).

## User Scenarios & Testing *(mandatory)*

<!--
  As histórias estão priorizadas como jornadas. Cada uma é INDEPENDENTEMENTE TESTÁVEL:
  implementar apenas uma já entrega valor verificável. Para teste isolado, cada história
  assume o baseline mínimo seedado (ex.: uma organização ativa e um usuário) descrito em
  Assumptions.
-->

### User Story 1 - Acesso seguro e isolamento de dados entre organizações (Priority: P1)

Um usuário pertencente a uma organização autentica-se com suas credenciais, obtém uma sessão
que expira automaticamente, encerra a sessão quando desejar, e durante toda a sessão só
consegue ver e operar dados da(s) organização(ões) à(s) qual(is) pertence. Qualquer tentativa
de acessar dado de outra organização é negada sem revelar que o recurso existe. Após sucessivas
tentativas malsucedidas de login, a conta é bloqueada temporariamente.

**Why this priority**: É a invariante catastrófica e o propósito central da fundação. Um
vazamento cross-tenant compromete a confiança de todos os clientes simultaneamente. Sem acesso
seguro e isolamento provado, nenhum módulo de negócio pode ser construído com segurança.

**Independent Test**: Com uma organização ativa e um usuário seedados, é possível verificar
login bem-sucedido, expiração de sessão, logout que invalida a sessão, bloqueio após N falhas,
e — com duas organizações e seus respectivos usuários — que um usuário nunca lê/lista/altera
dado da outra organização (negado com 404/403 + auditoria).

**Acceptance Scenarios**:

1. **Given** um usuário ativo de uma organização ativa, **When** ele se autentica com
   credenciais válidas, **Then** recebe uma sessão válida com expiração configurável e a ação
   de login é registrada em auditoria.
2. **Given** uma sessão autenticada válida, **When** o usuário faz logout, **Then** a sessão é
   encerrada imediatamente e qualquer reuso do mesmo token é negado, com o logout auditado.
3. **Given** uma sessão autenticada, **When** o tempo de expiração configurado é atingido,
   **Then** a sessão deixa de ser aceita e o usuário precisa autenticar novamente.
4. **Given** uma conta de usuário, **When** ocorrem N tentativas consecutivas de login com
   senha incorreta (N configurável), **Then** a conta é bloqueada temporariamente, novas
   tentativas são recusadas, e cada falha e o bloqueio são auditados.
5. **Given** credenciais inválidas (e-mail inexistente OU senha errada), **When** o usuário
   tenta autenticar, **Then** o sistema retorna o mesmo erro genérico, sem revelar se o e-mail
   existe.
6. **Given** um usuário autenticado da Organização A, **When** ele tenta ler/listar/alterar
   um recurso da Organização B, **Then** o acesso é negado (404/403 sem revelar existência) e
   a tentativa é auditada.

---

### User Story 2 - Provisionamento da plataforma e ciclo de vida de organizações (Priority: P2)

A plataforma é inicializável: o primeiro Super Admin da plataforma é criado por um mecanismo de
bootstrap único. O Super Admin então cadastra organizações (tenants) e controla seu ciclo de
vida — criar, ativar, suspender e reativar — controlando assim quando os usuários de cada
organização podem operar.

**Why this priority**: Sem o bootstrap e sem organizações provisionadas, não há tenants para
isolar nem usuários para autenticar. Habilita o onboarding de novas organizações-cliente e o
controle do seu estado de acesso (ex.: suspensão por inadimplência ou incidente).

**Independent Test**: É possível executar o bootstrap do primeiro Super Admin uma única vez,
criar uma organização, ativá-la, suspendê-la (verificando que seus usuários deixam de operar)
e reativá-la — cada transição auditada.

**Acceptance Scenarios**:

1. **Given** uma plataforma sem nenhum Super Admin, **When** o mecanismo de bootstrap é
   executado, **Then** o primeiro Super Admin da plataforma é criado e a ação é auditada.
2. **Given** uma plataforma que já possui um Super Admin, **When** o bootstrap é executado
   novamente, **Then** a operação é recusada.
3. **Given** um Super Admin autenticado, **When** ele cria uma organização com nome e
   identificador únicos, **Then** a organização é criada no estado inicial e a ação é auditada.
4. **Given** uma organização ativa, **When** o Super Admin a suspende, **Then** os usuários
   dessa organização deixam de conseguir autenticar/operar, os dados são preservados, e a
   suspensão é auditada.
5. **Given** uma organização suspensa, **When** o Super Admin a reativa, **Then** seus usuários
   voltam a poder operar e a reativação é auditada.
6. **Given** um Super Admin operando entre organizações, **When** ele realiza qualquer ação,
   **Then** a ação é auditada normalmente — não há bypass de auditoria para o Super Admin.
7. **Given** uma organização recém-criada sem usuários, **When** o Super Admin convida seu
   administrador inicial (Admin da organização ou Consultor) pelo fluxo de convite normal,
   **Then** o convite é emitido e auditado, e ao aceitar o convidado torna-se administrador apto
   a convidar os demais — sem criação direta de conta.

---

### User Story 3 - Convite de usuários e controle de acesso por papel (RBAC) (Priority: P3)

Um administrador de organização (ou o Super Admin, ou um Consultor com permissão na
organização) convida um usuário para a organização atribuindo-lhe um papel. O convidado recebe
o convite, aceita dentro do prazo, define sua senha e passa a operar conforme as permissões do
seu papel. Papéis e permissões controlam o que cada usuário pode fazer; ações não permitidas são
negadas e auditadas. Um Consultor pode pertencer a múltiplas organizações; os demais papéis
pertencem a exatamente uma.

**Why this priority**: Popula as organizações com usuários e estabelece o controle de acesso
granular sobre o qual todas as ações sensíveis dependem. Depende de organizações existirem (US2)
e de autenticação funcionar (US1).

**Independent Test**: Com uma organização ativa e um administrador, é possível convidar um
usuário com um papel, aceitar o convite, definir senha e autenticar; verificar que o convite
expira/é revogável; verificar que uma ação fora das permissões do papel é negada (403) e
auditada; e que um Consultor vinculado a duas organizações opera em ambas mas não vê dados de
uma terceira.

**Acceptance Scenarios**:

1. **Given** um Admin da organização autenticado, **When** ele convida um e-mail para sua
   organização atribuindo um papel, **Then** um convite com prazo de expiração configurável é
   criado e a ação é auditada.
2. **Given** um convite válido e não expirado, **When** o destinatário o aceita e define uma
   senha que atende à política mínima, **Then** o vínculo (membership) com o papel atribuído é
   ativado, o usuário consegue autenticar, e o aceite é auditado.
3. **Given** um convite expirado, já aceito ou revogado, **When** alguém tenta aceitá-lo,
   **Then** o aceite é recusado com mensagem genérica e a tentativa é auditada.
4. **Given** um usuário com um papel sem determinada permissão, **When** ele tenta executar uma
   ação que exige essa permissão, **Then** a ação é negada (403, sem alteração de estado) e o
   evento é auditado.
5. **Given** um Admin da organização autenticado, **When** ele altera o papel de um usuário da
   sua organização, **Then** o papel é atualizado e a mudança é auditada.
6. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas dados da Organização A são visíveis/alteráveis, e ele não
   consegue acessar a Organização C (não vinculada).

---

### User Story 4 - Definição e redefinição de senha (autoatendimento) (Priority: P4)

Um usuário que esqueceu a senha solicita a redefinição informando seu e-mail; recebe um meio de
redefinição com prazo de validade e uso único; define uma nova senha. O fluxo não revela se o
e-mail existe e invalida sessões ativas após a troca.

**Why this priority**: Recuperação de acesso de autoatendimento reduz dependência de suporte e
fecha o ciclo de gestão de credenciais. Importante, porém não bloqueia o MVP de acesso seguro.

**Independent Test**: Com um usuário existente, solicitar redefinição, usar o meio de
redefinição uma única vez dentro da validade para definir nova senha, autenticar com a nova
senha, e confirmar que o meio de redefinição não pode ser reutilizado e que e-mail inexistente
produz resposta genérica.

**Acceptance Scenarios**:

1. **Given** um e-mail qualquer, **When** o usuário solicita redefinição de senha, **Then** o
   sistema responde de forma genérica (sem revelar se o e-mail existe) e, se existir, emite um
   meio de redefinição com validade configurável e uso único; a solicitação é auditada.
2. **Given** um meio de redefinição válido e não expirado, **When** o usuário define uma nova
   senha que atende à política, **Then** a senha é atualizada, sessões ativas anteriores são
   invalidadas, o meio de redefinição é consumido, e a ação é auditada.
3. **Given** um meio de redefinição expirado ou já usado, **When** o usuário tenta usá-lo,
   **Then** a operação é recusada com mensagem genérica.

---

### User Story 5 - Trilha de auditoria imutável de ações sensíveis (Priority: P5)

Toda ação sensível na fundação (login, logout, falha de login, convite, aceite/revogação de
convite, mudança de papel, criação/alteração de organização ou usuário, mudança de estado de
organização, tentativa de acesso cross-tenant, bootstrap, redefinição de senha) gera um registro
de auditoria imutável (append-only) que não contém senhas, tokens, chaves nem PII em texto claro.

**Why this priority**: Garante rastreabilidade operacional — requisito de compliance e a base
probatória de qualquer SGSI auditável. É transversal às demais histórias; isolada como história
para tornar a imutabilidade e a ausência de dados sensíveis explicitamente verificáveis.

**Independent Test**: Executar uma amostra das ações sensíveis e verificar que cada uma gera
exatamente um registro de auditoria com ator, ação, tipo/id do alvo, contexto de tenant,
timestamp e resultado (sucesso/negado); que nenhum registro contém segredo/PII; e que registros
não podem ser editados nem apagados.

**Acceptance Scenarios**:

1. **Given** qualquer ação sensível enumerada, **When** ela ocorre (com sucesso ou negada),
   **Then** é gravado exatamente um registro de auditoria contendo ator, ação, tipo e id do
   alvo, contexto de tenant (quando aplicável), timestamp e resultado.
2. **Given** registros de auditoria existentes, **When** qualquer ator (incluindo Super Admin)
   tenta editá-los ou apagá-los, **Then** a operação não é suportada — a trilha é append-only.
3. **Given** uma ação envolvendo senha, token, chave ou PII, **When** ela é auditada, **Then**
   nenhum desses dados aparece em texto claro no registro de auditoria.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler/alterar um usuário,
   convite ou registro de outra organização (Organização B) referenciando seu identificador,
   **Then** o sistema nega (404/403 sem revelar existência) e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da
   Organização A, **Then** apenas dados da Organização A são visíveis/alteráveis; dados de B só
   no contexto de B; e dados de uma Organização C (não vinculada) nunca são acessíveis.
3. **Given** qualquer usuário não-Super-Admin, **When** ele lista organizações, **Then** apenas
   a(s) organização(ões) à(s) qual(is) pertence é(são) retornada(s) — nunca a existência de
   outras.
4. **Given** o Super Admin da plataforma, **When** ele opera entre organizações, **Then** o
   acesso cross-tenant é permitido (único papel cross-tenant), porém toda ação é auditada.

### Edge Cases

- O que acontece com uma sessão ativa quando a organização do usuário é **suspensa**? → A
  próxima requisição é negada (fail-closed); a sessão deixa de operar até a reativação.
- Bootstrap executado quando já existe Super Admin → recusado, sem criar segundo via bootstrap.
- Convite para um e-mail que **já possui vínculo** ativo naquela organização → recusado/sem
  duplicação de vínculo.
- Convite para uma pessoa que **já existe** na plataforma (ex.: Consultor) → adiciona novo
  vínculo (membership), não cria identidade duplicada.
- Aceite de convite enquanto autenticado como **outro** usuário → o aceite vincula-se ao
  destinatário correto do convite, não ao usuário logado.
- Solicitação de redefinição de senha para e-mail **inexistente** → resposta genérica, sem
  enumeração de e-mails.
- Tentativa de remover/desativar o **único** Super Admin da plataforma ou o **único** Admin de
  uma organização → impedida (salvaguarda contra perda de administração).
- Mudança de papel que deixaria a organização **sem nenhum administrador** → impedida.
- Reuso de token de sessão após logout ou após expiração → negado.
- Convite expirado durante o aceite (corrida com a expiração) → tratado como expirado.
- Falha do mecanismo de revogação de sessão (infra) → autenticação permanece disponível
  (fail-open) e o evento é logado como warning.
- Falha no envio de e-mail (convite/redefinição) → operação tratada graciosamente (reenviável),
  sem vazar detalhes internos nem confirmar existência de e-mail.

## Requirements *(mandatory)*

### Functional Requirements

**Bootstrap e organizações (tenants)**

- **FR-001**: O sistema MUST permitir, por um mecanismo de bootstrap único, a criação do
  primeiro Super Admin da plataforma somente quando nenhum Super Admin existir; tentativas
  posteriores de bootstrap MUST ser recusadas.
- **FR-002**: O sistema MUST permitir que o Super Admin crie organizações com nome e um
  identificador único, e MUST impedir identificadores duplicados.
- **FR-002a**: O administrador inicial de uma organização recém-criada MUST ser estabelecido
  pelo Super Admin por meio do **fluxo de convite normal** (FR-016/FR-017) — convidando um Admin
  da organização ou um Consultor — sem caminho especial de criação direta de conta. Até o aceite,
  o Super Admin pode operar a organização (papel cross-tenant), e essa janela é auditada.
- **FR-003**: Cada organização MUST possuir um estado de ciclo de vida e suportar as transições
  **ativar**, **suspender** e **reativar**; cada transição MUST ser auditada.
- **FR-004**: Quando uma organização está suspensa, seus usuários MUST ser impedidos de
  autenticar e de operar (fail-closed), preservando os dados; sessões ativas MUST ser negadas na
  próxima requisição.
- **FR-005**: A listagem e a consulta de organizações MUST ser escopadas: o Super Admin vê
  todas; qualquer outro usuário vê apenas a(s) organização(ões) à(s) qual(is) pertence.

**Autenticação e sessão**

- **FR-006**: O sistema MUST autenticar usuários por credenciais e, em caso de sucesso, emitir
  uma sessão com tempo de expiração configurável.
- **FR-007**: O logout MUST encerrar a sessão imediatamente, de modo que o mesmo token não possa
  ser reutilizado.
- **FR-008**: O tempo de expiração de sessão MUST ser configurável sem alteração de código.
- **FR-009**: O sistema MUST bloquear temporariamente a conta após um número configurável de
  tentativas de login consecutivas malsucedidas, recusando novas tentativas durante o bloqueio.
- **FR-009a**: O bloqueio MUST ser removível por três meios: (a) **auto-expiração** após uma
  janela de bloqueio configurável; (b) **desbloqueio manual** por papel autorizado (Admin da
  organização para usuários da sua organização; Super Admin); e (c) **redefinição de senha**
  bem-sucedida. O desbloqueio manual MUST ser auditado.
- **FR-010**: Os endpoints de autenticação e de senha MUST ser protegidos por limitação de taxa
  (rate limiting) configurável.
- **FR-011**: Falhas de autenticação MUST retornar uma mensagem genérica que não revele se o
  e-mail informado existe.

**Senha**

- **FR-012**: No aceite de convite, o usuário MUST definir uma senha que atenda a uma política
  mínima configurável.
- **FR-013**: O sistema MUST permitir solicitar redefinição de senha por e-mail, respondendo de
  forma genérica (sem revelar existência do e-mail) e, quando o e-mail existir, emitindo um meio
  de redefinição com validade configurável e de uso único.
- **FR-014**: A redefinição bem-sucedida de senha MUST consumir o meio de redefinição e
  invalidar as sessões ativas anteriores do usuário.
- **FR-015**: Senhas MUST ser armazenadas, transmitidas internamente e registradas apenas de
  forma não recuperável; senhas em texto claro NUNCA aparecem em armazenamento persistente,
  logs, respostas de erro ou auditoria.

**Convites e usuários**

- **FR-016**: O sistema MUST permitir que papéis autorizados (Admin da organização, Super Admin
  e Consultor com permissão na organização) convidem um e-mail para uma organização atribuindo
  um papel, com prazo de expiração configurável.
- **FR-017**: O aceite de um convite válido MUST ativar o vínculo (membership) do usuário com a
  organização no papel atribuído e permitir a definição de senha; se a pessoa já existir na
  plataforma, MUST adicionar um novo vínculo sem duplicar a identidade.
- **FR-018**: Convites expirados, já aceitos ou revogados MUST ser recusados no aceite, com
  mensagem genérica, e a tentativa MUST ser auditada.
- **FR-019**: Papéis autorizados MUST poder revogar e reenviar convites pendentes da sua
  organização.
- **FR-020**: O papel é uma propriedade do vínculo (membership). **Apenas o papel Consultor**
  MUST poder manter mais de um vínculo (múltiplas organizações); qualquer pessoa que possua um
  vínculo de qualquer outro papel MUST pertencer a **exatamente uma** organização (esse vínculo é
  o único da pessoa).
- **FR-021**: Papéis autorizados MUST poder alterar o papel de um usuário dentro da sua
  organização e desativar/remover um vínculo; toda alteração MUST ser auditada.
- **FR-022**: O sistema MUST impedir operações que deixem a plataforma sem Super Admin ou uma
  organização sem nenhum administrador.

**Papéis e autorização (RBAC)**

- **FR-023**: O sistema MUST reconhecer os papéis: Super Admin da plataforma, Admin da
  organização, Consultor, Cliente, Gestor, Dono de processo, Dono de controle, Auditor interno e
  Colaborador convidado.
- **FR-024**: Toda ação sensível MUST verificar a permissão do papel do usuário; na ausência da
  permissão necessária, a ação MUST ser negada (sem alteração de estado) e o evento auditado.
- **FR-025**: O Super Admin da plataforma MUST ser o único papel cross-tenant; ele pode operar
  entre organizações, mas NUNCA tem bypass de auditoria.
- **FR-026**: As permissões MUST ser granulares por papel, de modo que cada ação da fundação
  (gerir organizações, gerir ciclo de vida, convidar usuários, alterar papéis, etc.) seja
  associada a uma permissão verificável.

**Isolamento de tenant**

- **FR-027**: Todo dado de domínio MUST ser escopado pela organização do usuário autenticado, a
  partir de um ponto único e não-contornável de resolução/filtragem de tenant.
- **FR-028**: Tentativas de leitura, listagem ou alteração de dado de outra organização MUST ser
  negadas com 404/403 sem revelar a existência do recurso, e MUST ser auditadas.
- **FR-029**: Para um usuário vinculado a múltiplas organizações (Consultor), o sistema MUST
  operar sob um contexto de organização explícito por requisição, restrito às organizações às
  quais o usuário está vinculado.

**Auditoria**

- **FR-030**: O sistema MUST registrar em auditoria cada ação sensível: login, logout, falha de
  login, bloqueio de conta, desbloqueio de conta (manual ou por redefinição), bootstrap,
  criação/alteração/mudança de estado de organização, criação/alteração/desativação de usuário,
  convite/aceite/revogação de convite, mudança de papel, solicitação/conclusão de redefinição de
  senha e tentativa de acesso cross-tenant.
- **FR-031**: A trilha de auditoria MUST ser append-only: registros NUNCA podem ser editados ou
  apagados por nenhum ator, incluindo o Super Admin.
- **FR-032**: Registros de auditoria NUNCA MUST conter senhas, tokens, chaves ou PII em texto
  claro.
- **FR-033**: Cada registro de auditoria MUST capturar ator, ação, tipo e identificador do alvo,
  contexto de tenant (quando aplicável), timestamp e resultado (sucesso ou negado).

**Tratamento de erros e degradação**

- **FR-034**: Mensagens de erro ao usuário NUNCA MUST expor detalhes internos (nomes de tabela,
  stack traces, ou a existência de recursos de outro tenant).
- **FR-035**: O isolamento de tenant MUST ser sempre fail-closed; o mecanismo de revogação de
  sessão MAY ser fail-open (autenticação permanece disponível) com registro de warning; falhas
  de envio de e-mail MUST ser tratadas graciosamente sem vazar detalhes internos.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado manipulado por esta feature é escopado pela
  organização do usuário. Recursos afetados: **Organização** (visível apenas a membros e ao
  Super Admin), **Vínculo Usuário↔Organização (Membership)**, **Convite** e qualquer
  listagem/detalhe derivado. Acesso cross-tenant ⇒ **404/403 sem revelar existência** + audit
  log. A identidade de **Usuário** é global, mas só é operável dentro de um contexto de vínculo;
  o Super Admin é o único papel cross-tenant.
- **SEC-002 (Papéis e permissões)**: Papéis que executam cada ação:
  - *Bootstrap do 1º Super Admin*: mecanismo de instalação/sistema (uma vez).
  - *Criar organização e gerir ciclo de vida (ativar/suspender/reativar)*: **Super Admin**
    (permissão `manage_organizations`).
  - *Convidar usuários / revogar / reenviar convite*: **Admin da organização**, **Super Admin**,
    **Consultor** com vínculo na organização (permissão `invite_users`).
  - *Alterar papel / desativar vínculo / desbloquear conta de usuário*: **Admin da organização**,
    **Super Admin** (permissão `manage_memberships`).
  - *Autenticar, logout, solicitar/redefinir senha, aceitar convite*: qualquer usuário/convidado.
  - *Ver dados da própria organização*: todos os papéis membros, conforme suas permissões.
  - Demais papéis (**Cliente, Gestor, Dono de processo, Dono de controle, Auditor interno,
    Colaborador convidado**) são definidos aqui e recebem permissões de negócio nas features
    seguintes; nesta fundação participam como membros sujeitos a verificação de permissão.
- **SEC-003 (Auditoria)**: Operações que geram audit log: login, logout, falha de login,
  bloqueio de conta, desbloqueio de conta, bootstrap, criação/alteração/mudança de estado de organização,
  criação/alteração/desativação de usuário, convite/aceite/revogação, mudança de papel,
  solicitação/conclusão de redefinição de senha e tentativa de acesso cross-tenant. Cada registro
  grava `[actor, operation, entity_type, entity_id, tenant_context, timestamp, outcome]`, mais
  metadados de segurança forense (`ip`, `user_agent`) — tratados como **dados de segurança**, não
  como conteúdo/PII do tenant — e **nunca** inclui senhas, tokens, chaves ou PII de conteúdo em
  texto claro. Ações do Super Admin são auditadas sem exceção.
- **SEC-004 (Dados sensíveis)**: **Sim** — a feature trata credenciais e PII. Campos sensíveis:
  senha (armazenada de forma não recuperável/hash), tokens de sessão/convite/redefinição
  (opacos, de uso único quando aplicável, nunca logados), e PII (nome, e-mail). Proteção: senhas
  e tokens nunca em logs/erros/auditoria; PII não aparece em texto livre de auditoria;
  e-mail/PII em repouso protegidos conforme política de cifragem de campos sensíveis da
  plataforma; mensagens de erro mascaram existência de recursos e detalhes internos.
- **SEC-005 (Evidências/versionamento)**: **Não** cria artefato versionável de compliance
  (evidência, SoA, risco, constatação) — esses chegam em features posteriores. A única trilha
  imutável desta feature é o **audit log** (append-only), coberto por SEC-003.
- **SEC-006 (Degradação)**: Isolamento de tenant e suspensão de organização são **sempre
  fail-closed**. O mecanismo de revogação de sessão é **fail-open** (autenticação permanece
  disponível em indisponibilidade da infra), registrando warning — justificativa:
  disponibilidade > segurança absoluta em falha transitória de infra, sem comprometer
  isolamento. Envio de e-mail (convite/redefinição) **degrada graciosamente**: a operação é
  reenviável e nunca vaza existência de e-mail nem detalhes internos.

### Key Entities *(include if feature involves data)*

<!-- Toda entidade escopada por tenant carrega tenant_id e relaciona-se a Organização. -->

- **Organização (Tenant)**: raiz da tenancy. Atributos-chave: nome, identificador único, estado
  de ciclo de vida (ex.: ativa/suspensa), metadados de criação. É o referencial de `tenant_id`
  das demais entidades escopadas.
- **Usuário**: identidade global da pessoa (e-mail único na plataforma), credencial de senha
  (não recuperável), nome, estado (ex.: pendente/ativo/desativado), contador de tentativas e
  estado de bloqueio. A identidade é global; a atuação ocorre sempre via um vínculo.
- **Vínculo Usuário↔Organização (Membership)**: associa um Usuário a uma Organização com
  **exatamente um papel**. Carrega `tenant_id`. Consultor pode ter vários vínculos; os demais
  papéis, exatamente um. É a entidade escopada por tenant que materializa a pertença.
- **Papel / Permissão**: conjunto enumerado de papéis e o mapeamento granular para permissões
  verificáveis. Referência de configuração que governa a autorização.
- **Convite**: destinatário (e-mail), organização (`tenant_id`), papel atribuído, quem convidou,
  meio/segredo de aceite (opaco), estado (pendente/aceito/expirado/revogado) e prazo de
  expiração. Escopado por tenant.
- **Sessão**: emitida no login; referencia o usuário e o contexto de organização ativo; possui
  expiração e pode ser revogada (logout, troca de senha).
- **Meio de Redefinição de Senha**: referencia o usuário; segredo opaco de uso único com
  validade; estado (válido/usado/expirado).
- **Registro de Auditoria**: ator, ação, tipo e id do alvo, contexto de tenant (quando
  aplicável; pode ser nulo para eventos de plataforma como bootstrap), timestamp e resultado.
  **Append-only** — nunca editado ou apagado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das tentativas de acesso cross-tenant são negadas sem revelar a existência do
  recurso, verificado por testes automatizados de isolamento que cobrem todos os tipos de recurso
  expostos pela feature (organização, vínculo, convite).
- **SC-002**: 100% das ações sensíveis enumeradas produzem exatamente um registro de auditoria
  imutável; 0% dos registros contêm senha, token, chave ou PII em texto claro (verificado por
  checagem automatizada).
- **SC-003**: Contas são bloqueadas após o número configurado de falhas consecutivas de login
  (padrão 5) e não conseguem autenticar durante o bloqueio; o acesso é restaurado por
  auto-expiração após a janela configurada, por desbloqueio manual de admin autorizado, ou por
  redefinição de senha — cada desbloqueio manual auditado.
- **SC-004**: Sessões tornam-se inutilizáveis imediatamente após o logout e automaticamente após
  a expiração configurada (padrão 20 minutos), verificado por tentativa de reuso.
- **SC-005**: 100% das tentativas de aceitar convites expirados, já aceitos ou revogados são
  recusadas; convites só são aceitáveis dentro do prazo de validade configurado.
- **SC-006**: 100% das ações executadas por usuários sem a permissão necessária são negadas sem
  alteração de estado e registradas em auditoria.
- **SC-007**: O bootstrap do primeiro Super Admin é bem-sucedido exatamente uma vez; qualquer
  tentativa subsequente é recusada.
- **SC-008**: Um Consultor vinculado a N organizações consegue operar em cada uma delas e nunca
  acessa dado de uma organização à qual não está vinculado.
- **SC-009**: Um usuário convidado consegue, sem intervenção de administrador, ir do recebimento
  do convite ao acesso autenticado completando um único fluxo guiado (aceitar → definir senha →
  autenticar).
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar ou alterar dado de uma organização
  à qual não pertence — verificado por teste automatizado dedicado de isolamento de tenant.

## Assumptions

- **Baseline para testes independentes**: cada história assume um baseline mínimo seedado
  conforme necessário (ex.: uma organização ativa e um usuário ativo) para ser testada de forma
  isolada antes de US2/US3 estarem prontas.
- **Modelo de identidade**: a identidade do usuário é global e única por e-mail; a pertença a
  uma organização é materializada por um vínculo (membership) com exatamente um papel. O papel
  Consultor admite múltiplos vínculos; os demais papéis, exatamente um. Esta é a leitura direta
  de "um Consultor pode atuar em múltiplas organizações; os demais papéis são por organização".
- **Autoridade de criação de organizações** (decidido — ver Clarifications): **apenas** o Super
  Admin da plataforma provisiona organizações e designa o Admin/Consultor inicial via convite
  (FR-002a). Autosserviço de criação por Consultores ou por clientes fica fora de escopo desta
  feature (pode ser adicionado depois sem quebrar o contrato).
- **Autenticação de fator único**: MFA/2FA não faz parte desta fundação; pode ser adicionado em
  feature futura sem quebrar este contrato.
- **Parâmetros configuráveis** (sem mudança de código): expiração de sessão (padrão 20 min),
  limite de tentativas de login (padrão 5), validade de convite e de redefinição de senha,
  limites de rate limiting e política mínima de senha. Configuração específica por tenant, se
  necessária, fica em dados, não em variáveis de ambiente.
- **Entrega de e-mail**: convites e redefinições de senha dependem de um canal de e-mail externo;
  sua indisponibilidade é tratada como degradação graciosa, não como falha de segurança.
- **Suspensão preserva dados**: suspender uma organização bloqueia o acesso mas não apaga dados;
  a reativação restaura o acesso.
- **Escopo estritamente de fundação**: nenhum módulo de negócio (Diagnóstico e Contexto, Gap
  Analysis, SoA, Plano de Ação, Gestão de Evidências, Riscos, Auditoria Interna, Revisão pela
  Direção, IA, Dashboards) é especificado aqui; cada um virá em sua própria spec reutilizando
  esta fundação.
