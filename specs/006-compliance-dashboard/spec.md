# Feature Specification: Dashboard de Conformidade

**Feature Branch**: `006-compliance-dashboard`

**Created**: 2026-06-21

**Status**: Draft

**Input**: Dashboard de Conformidade — página inicial de cada organização na plataforma SGSI
ISO/IEC 27001:2022; visão única e atualizada do estado de conformidade, agregando sobre os módulos
existentes (Contexto/Cláusula 4, Gap Analysis, SoA e módulos futuros).

---

## Visão Geral

O **Dashboard de Conformidade** é a página inicial de cada organização na plataforma.
Oferece, em uma única tela de leitura, o estado atual de conformidade ISO/IEC 27001:2022 da
organização: um card por módulo do SGSI com status, progresso, responsável, prazo e atalho para
a próxima ação recomendada. É a tela-âncora da revisão de UX — já desenhada no Claude Design —
e serve como ponto de entrada para auditorias internas e revisões pela direção.

---

## Clarifications

### Session 2026-06-21

- Q: Onde a agregação dos dados do dashboard deve acontecer (backend vs frontend)? → A: Endpoint
  dedicado `GET /dashboard` no backend, que agrega os serviços já existentes no servidor —
  habilitando a permissão `view_dashboard`, o log de tentativas não autorizadas e um único teste
  de isolamento de tenant. O frontend faz uma única chamada.
- Q: Qual a granularidade do atalho de "próxima ação" (FR-007)? → A: Navega para a rota do módulo
  com a seção/ação relevante em foco; deep-link a um passo específico apenas onde a rota já existir
  — não exige reescrever as rotas dos módulos.
- Q: Como tratar audit log de acesso ao dashboard (SEC-003)? → A: Registrar apenas tentativas de
  acesso não autorizadas (cross-tenant/negado); leituras bem-sucedidas da home **não** geram audit
  log (evita inflar a trilha append-only, alinhado a "operação relevante" da constitution).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Visão consolidada do estado de conformidade (P1)

O gestor de SGSI acessa a plataforma e, sem navegar por módulos individuais, obtém imediatamente
o panorama completo: quais etapas estão aprovadas, quais estão em rascunho ou em revisão, qual
o percentual de aderência do Gap Analysis e quais módulos ainda não foram iniciados. A partir do
dashboard, navega diretamente para a etapa que precisa de atenção.

**Por que P1**: É o primeiro ponto de contato após o login; sem ele o usuário precisa visitar cada
módulo separadamente para construir mentalmente o estado geral — custo alto de cognição em cada
sessão.

**Independent Test**: Com um tenant que possui Contexto aprovado, Gap Analysis em 68% e SoA em
rascunho, o dashboard deve exibir 3 cards com os dados corretos sem navegar para outros módulos.

**Acceptance Scenarios**:

1. **Given** um usuário autenticado com organização ativa que possui os módulos Contexto, Gap
   Analysis e SoA em estados distintos, **When** ele acessa o dashboard, **Then** vê um card para
   cada módulo exibindo o status correto (aprovado / em revisão / rascunho / não iniciado), o
   percentual de progresso derivado do módulo e o nome do responsável (quando houver atribuição).

2. **Given** o módulo Plano de Ação ainda não foi iniciado pela organização, **When** o usuário
   acessa o dashboard, **Then** o card do Plano de Ação aparece com status "Não iniciado" e
   atalho "Iniciar", sem exibir progresso inventado.

3. **Given** a próxima análise crítica do Contexto está vencida (data de revisão ultrapassada),
   **When** o usuário acessa o dashboard, **Then** o card do Contexto exibe indicador visual de
   alerta ("revisão vencida") destacado, com informação da data vencida.

4. **Given** o usuário clica no card do Gap Analysis, **When** a navegação ocorre, **Then** o
   sistema redireciona para a tela principal do Gap Analysis (dentro do contexto da mesma
   organização ativa).

5. **Given** o card do SoA exibe "próxima ação: Consolidar avaliação do Gap", **When** o usuário
   clica no botão/link de próxima ação, **Then** o sistema navega para o passo específico de
   consolidação dentro do SoA (não apenas para a página do módulo).

---

### User Story 2 — Percepção de progresso ao longo do tempo (P2)

O gestor ou auditor interno quer visualizar a evolução da conformidade da organização ao longo
dos ciclos de melhoria, entendendo se a aderência subiu ou caiu entre baselines.

**Por que P2**: Agrega valor analítico mas não bloqueia o uso do dashboard como ponto de entrada;
depende de histórico de baselines que pode ainda ser escasso em tenants novos.

**Independent Test**: Com um tenant que possui 3 baselines do Gap Analysis aprovadas em datas
distintas, o indicador deve exibir a série de aderência (ex.: 45% → 62% → 78%) sem exigir
interação com outros módulos.

**Acceptance Scenarios**:

1. **Given** a organização possui ao menos duas baselines aprovadas do Gap Analysis, **When** o
   usuário acessa o dashboard, **Then** o indicador de conformidade ao longo do tempo exibe a
   série cronológica de percentuais de aderência.

2. **Given** a organização não possui nenhuma baseline aprovada ainda, **When** o usuário acessa
   o dashboard, **Then** o indicador de evolução não é exibido (ou exibe estado vazio
   "nenhuma baseline disponível") — sem dado inventado ou projetado.

---

### Tenant Isolation Scenarios *(mandatory)*

1. **Given** um usuário autenticado na Organização A, **When** ele tenta acessar o dashboard
   da Organização B (por manipulação de header ou URL), **Then** o sistema nega o acesso com
   404/403 sem revelar a existência dos dados da Organização B e registra a tentativa no
   audit log.

2. **Given** um Consultor vinculado às Organizações A e B, **When** ele acessa o dashboard no
   contexto da Organização A (header `X-Org-Context: A`), **Then** apenas os dados de conformidade
   da Organização A são exibidos — nenhum dado da Organização B vaza, nem mesmo em forma
   de estatística agregada.

3. **Given** a organização do usuário está suspensa, **When** ele tenta acessar o dashboard,
   **Then** o sistema nega o acesso e o redireciona para tela de organização suspensa, sem expor
   dados de outras organizações.

---

### Edge Cases

- **Módulo sem dados**: quando um módulo foi iniciado mas não possui nenhum dado preenchido
  (ex.: Gap Analysis com seed não adotado), o card exibe progresso 0% e status "Não iniciado",
  sem erro.
- **Dados parcialmente indisponíveis**: se a agregação de um módulo falhar (timeout ou erro
  interno), o card desse módulo exibe estado de erro localizado ("dados indisponíveis") enquanto
  os demais cards carregam normalmente — falha isolada, não derruba o dashboard inteiro.
- **Organização sem responsável atribuído**: o campo de responsável é omitido no card (não exibe
  "null" ou vazio sem significado).
- **Prazo sem data**: quando a atribuição não possui prazo definido, o campo de prazo é omitido.
- **Usuário sem permissão de visualizar um módulo específico**: o card desse módulo é omitido
  ou exibido como bloqueado, conforme política de acesso, sem revelar o conteúdo.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE exibir um card por módulo do SGSI (Contexto/Cláusula 4, Gap
  Analysis, SoA e, quando existirem, Plano de Ação e Evidências) na tela inicial da organização.

- **FR-002**: Cada card DEVE exibir o **status atual** do módulo, derivado do estado real do
  artefato: rascunho, em revisão, aprovado-em vigor, não iniciado, ou obsoleto/precisa revisão
  (quando o artefato está aprovado mas a data de análise crítica está vencida). Estes rótulos
  mapeiam para o vocabulário normalizado `DashboardCardStatus` (ver data-model / research D4):
  `draft` · `in_review` · `in_force` · `not_started` · `needs_review`.

- **FR-003**: Cada card DEVE exibir o **percentual de progresso** do módulo, calculado conforme
  a natureza do módulo: completude de preenchimento (Contexto/formulários), aderência ponderada
  (Gap Analysis), completude de itens avaliados (SoA).

- **FR-004**: Cada card DEVE exibir o **responsável** pela etapa (nome e/ou avatar) e o **prazo**
  de conclusão, quando houver atribuição ativa associada ao módulo. Campos são omitidos quando
  ausentes (não exibir valores vazios ou nulos).

- **FR-005**: Quando a data de próxima análise crítica do módulo estiver vencida, o card DEVE
  exibir um **indicador visual de alerta** ("revisão vencida") com a data correspondente.

- **FR-006**: O **card inteiro** DEVE ser clicável e navegar para a tela principal do módulo
  correspondente.

- **FR-007**: Cada card DEVE exibir um **atalho para a próxima ação recomendada** do módulo
  (ex.: "Consolidar avaliação", "Enviar para revisão", "Aprovar", "Iniciar"). Ao clicar nesse
  atalho, o sistema navega para a **rota do módulo com a seção/ação relevante em foco**; o
  deep-link para um passo específico é aplicado apenas onde a rota do módulo já oferecer esse
  ponto de entrada — esta feature **não** reescreve as rotas internas dos módulos para criar
  novos pontos de deep-link.

- **FR-008**: Módulos ainda não iniciados DEVEM aparecer no dashboard com status "Não iniciado"
  e atalho "Iniciar", sem exibir progresso ou responsável inventados.

- **FR-009**: A tela é **somente leitura** — nenhuma edição de dados dos módulos ocorre no
  dashboard; toda ação de edição leva para a tela do módulo correspondente.

- **FR-010**: O dashboard DEVE exibir **exclusivamente** dados da organização ativa do usuário
  autenticado; não há modo de visualizar dados de outra organização sem trocar o contexto de org.

- **FR-011** *(opcional, P2)*: O dashboard PODE exibir um **indicador de conformidade ao longo
  do tempo** (série de aderência derivada de baselines aprovadas do Gap Analysis), exibido apenas
  quando existir histórico suficiente (≥ 2 baselines aprovadas).

---

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todos os dados exibidos são escopados pela organização
  ativa do usuário autenticado (`tenant_id` derivado do JWT + header `X-Org-Context`). Acesso
  cross-tenant ⇒ 404/403 sem revelar existência + audit log. Entidades agregadas: `gap_catalog_item`,
  `gap_assessment`, `soa`, `soa_item`, `document_versions`, `form_assignments`, `context_overview`,
  `gap_assessment_baselines`.

- **SEC-002 (Papéis e permissões)**: Qualquer papel vinculado à organização pode acessar o
  dashboard (visão de leitura). Permissão necessária: `view_dashboard` (nova, de baixo custo —
  atribuída por padrão a todos os papéis exceto Colaborador convidado, que recebe apenas se o
  Admin liberar), **verificada no servidor** no endpoint dedicado de dashboard. Cards de módulos
  com permissões mais restritivas (ex.: `view_gap`, `view_soa`) são exibidos/ocultados conforme as
  permissões do usuário — o dashboard não eleva permissões.

- **SEC-003 (Auditoria)**: Leituras **bem-sucedidas** do dashboard **não** geram audit log — é a
  home, carregada a cada login/navegação, e registrá-la infla a trilha append-only sem agregar
  valor de auditoria (alinhado ao princípio de "operação relevante" da constitution). Apenas
  **tentativas de acesso não autorizadas** (cross-tenant ou organização suspensa) geram log com
  `operation: UNAUTHORIZED_ACCESS`, `entity_type: "dashboard"`, `entity_id: tenant_id` solicitado,
  `user_id`. **Nunca** PII ou conteúdo de evidência no audit log.

- **SEC-004 (Dados sensíveis)**: O dashboard exibe apenas metadados de status e progresso
  (percentuais, nomes de responsáveis, datas). Não exibe conteúdo de evidências, respostas de
  formulários ou dados classificados. Nomes de usuários (responsáveis) são dados
  não-sensíveis dentro da organização.

- **SEC-005 (Evidências/versionamento)**: O dashboard não cria nem altera artefatos. É read-only.
  Não há versionamento de estado do dashboard (é derivado ao vivo dos módulos). N/A para
  append-only.

- **SEC-006 (Degradação)**: Falha de um módulo ao agregar dados ⇒ card exibe estado de erro
  localizado; os demais cards carregam normalmente (fail-open por card). O isolamento de tenant é
  sempre fail-closed: em caso de dúvida sobre o tenant do dado, o sistema nega e loga.

---

### Key Entities *(leitura agregada — sem novo modelo de domínio)*

O dashboard **não cria entidades novas**. Agrega dados de:

- **GapAssessment + GapMetrics**: aderência ponderada, completude, distribuição de status dos
  93 controles.
- **SoA + SoaItems**: quantidade de itens avaliados / total, status do documento controlado.
- **DocumentVersions**: versão vigente de cada artefato (Contexto, Gap baseline, SoA),
  `next_review_at`, `current_version_id`, `draft_status`.
- **FormAssignments**: atribuição ativa por módulo — `responsible_name`, `deadline_at`,
  `respondent_email`.
- **ContextOverview**: status do escopo, análise de contexto, stakeholders (derivado do
  endpoint `/context/overview`).
- **GapBaselines** *(P2)*: série histórica de baselines aprovadas com `overall_adherence` e
  `created_at`, para o indicador de evolução.

Todos carregam `tenant_id`; o endpoint de dashboard filtra por `tenant_id` do usuário.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: O dashboard carrega e exibe todos os cards disponíveis em menos de 2 segundos em
  condições normais de rede, sem interação adicional do usuário.

- **SC-002**: 100% dos status e percentuais exibidos nos cards refletem o estado real dos
  módulos — verificado por teste automatizado que compara os dados do dashboard com os dados
  brutos de cada módulo para o mesmo tenant.

- **SC-003**: Um usuário que acessa a plataforma consegue identificar a próxima ação necessária
  em cada módulo sem navegar para fora do dashboard.

- **SC-004**: Quando um módulo está com análise crítica vencida, o alerta visual é perceptível
  sem interação adicional (não requer hover, scroll ou clique para ser visto).

- **SC-005**: A falha de agregação de um único módulo não impede a exibição dos demais cards
  — verificado por teste que simula erro no endpoint de um módulo e confirma que os outros
  carregam corretamente.

- **SC-ISO (mandatory)**: Nenhum usuário consegue visualizar dados de conformidade de uma
  organização à qual não pertence — verificado por teste automatizado de isolamento de tenant
  que testa com JWTs de organizações distintas e valida que a resposta é 404/403 e que o
  audit log registra a tentativa.

---

## Assumptions

- Há um **único endpoint de leitura dedicado** (`GET /dashboard`) que agrega, no servidor, os
  dados dos serviços já existentes (`gap_metrics_service`, `soa_consolidation_service`,
  `context_overview`, `form_assignments`, `document_versions`) — **sem novo modelo de domínio** e
  sem nova tabela de banco de dados. O frontend faz uma única chamada (decisão de clarificação:
  agregação no backend, não no frontend). O dashboard montado na revisão de UX, que compõe
  endpoints no frontend, será migrado para consumir esse endpoint.

- A "próxima ação recomendada" de cada módulo é determinada por lógica heurística baseada no
  estado atual do artefato (mesmo padrão do `suggestion_service` do Módulo 1); não requer
  módulo de IA.

- Os dados de responsável e prazo são derivados da atribuição ativa (`form_assignments` ou
  campo `responsible`/`deadline` dos artefatos de módulo); quando não há atribuição, esses
  campos ficam ausentes no card.

- O card de "Plano de Ação" e o card de "Evidências" são exibidos como placeholders com status
  "Em breve" / "Módulo futuro" quando os módulos correspondentes (Módulo 4 e 5) ainda não
  estiverem implementados — a estrutura de cards suporta extensão futura sem redesign.

- A permissão `view_dashboard` é nova e de baixo custo; não cria hierarquia complexa. Todos
  os papéis ativos da organização a recebem por padrão, exceto Colaborador convidado (que requer
  concessão explícita pelo Admin).

- O indicador de conformidade ao longo do tempo (FR-011, P2) usa exclusivamente baselines do
  Gap Analysis aprovadas — não extrapola, não projeta, não interpola dados faltantes.

- A resolução de org ativa usa o mecanismo já existente (`X-Org-Context` + JWT), sem nova
  lógica de seleção de tenant.

- Design visual já definido no Claude Design (handoff em `docs/design/`); a especificação não
  redefine layout — apenas descreve comportamento e dados.
