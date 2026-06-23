# Feature Specification: Anexos e Evidências na Matriz do Gap Analysis

**Feature Branch**: `008-gap-evidence-attachments`

**Created**: 2026-06-22

**Status**: Draft

**Input**: User description: "Implementar anexos/evidências documentais na Matriz do Gap Analysis, permitindo que usuários autorizados anexem, consultem e rastreiem evidências reais da organização diretamente em cada item avaliado."

## Clarifications

### Session 2026-06-22

- Q: Como a classificação da evidência deve afetar o acesso ao conteúdo do arquivo no MVP? → A: Usuários com `view_gap` veem metadados de todas as evidências; download/conteúdo de evidências públicas ou internas também usa `view_gap`; evidências confidenciais ou restritas exigem `manage_gap`.
- Q: A classificação/sensibilidade da evidência deve ser obrigatória no upload? → A: Sim; a classificação é obrigatória no upload inicial e na substituição por nova versão, com valor padrão "Uso interno" no envio inicial e valor atual pré-preenchido na substituição, sempre editável antes de enviar.
- Q: Quais consultas de evidência devem gerar audit log no MVP? → A: Listar metadados no painel não gera audit; visualizar/baixar conteúdo do arquivo gera audit; upload, substituição, inativação e tentativas negadas sempre geram audit.
- Q: Quando uma evidência for substituída, como ela deve aparecer na matriz por padrão? → A: A lista principal exibe apenas a versão corrente; versões anteriores ficam no histórico da evidência para usuários com `manage_gap`.
- Q: Quem pode ver versões anteriores e evidências inativadas no histórico? → A: Apenas usuários com `manage_gap` veem histórico, versões anteriores e evidências inativadas.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Anexar Evidência a um Item do Gap (Priority: P1)

Um usuário autorizado seleciona um controle na Matriz do Gap Analysis e anexa um arquivo ou registro documental que comprova, sustenta ou complementa a avaliação daquele item. O usuário informa uma descrição curta, confirma o envio e passa a ver a evidência associada ao item correto, com autor e data.

**Why this priority**: É o valor central da feature. Sem anexos, a matriz registra conclusões, mas não preserva a comprovação documental necessária para auditoria e certificação.

**Independent Test**: Com uma organização autenticada e um item do Gap existente, um usuário com permissão de gerenciar Gap Analysis anexa uma evidência válida ao item. A evidência aparece na lista daquele item, associada à organização correta, com metadados de autoria, data, tamanho, tipo e integridade.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de gerenciar Gap Analysis está no painel de detalhe de um item, **When** ele seleciona um arquivo permitido, informa uma descrição opcional e confirma o envio, **Then** a evidência é registrada naquele item e aparece na seção "Evidências anexadas".
2. **Given** um usuário tenta anexar um arquivo vazio, grande demais ou não permitido pela política da plataforma, **When** ele confirma o envio, **Then** o sistema recusa a evidência com mensagem clara e mantém a avaliação do item funcionando.
3. **Given** uma evidência foi anexada com sucesso, **When** o usuário consulta os detalhes dela, **Then** o sistema mostra título/nome, descrição quando houver, autor, data/hora, tipo, tamanho, classificação quando aplicável e indicador de integridade.
4. **Given** o usuário está anexando uma evidência, **When** o formulário de envio é exibido, **Then** a classificação aparece obrigatória com valor padrão "Uso interno" e pode ser alterada antes da confirmação.

---

### User Story 2 - Consultar Evidências Anexadas no Painel da Matriz (Priority: P2)

Um avaliador seleciona um item da matriz e visualiza, em uma seção separada, quais evidências reais da organização já foram anexadas àquele controle. A tela deixa claro que "evidências esperadas" são orientação da plataforma e que "evidências anexadas" são documentos enviados pela organização.

**Why this priority**: A consulta contextual evita que o usuário saia da matriz para procurar documentos e reduz confusão entre orientação esperada e comprovação real.

**Independent Test**: Com evidências previamente anexadas a um item, abrir a Matriz do Gap Analysis, selecionar o item e verificar que a seção "Evidências anexadas" lista apenas evidências daquele item e daquela organização.

**Acceptance Scenarios**:

1. **Given** um item possui evidências anexadas, **When** o usuário seleciona o item na matriz, **Then** o painel lateral exibe a seção "Evidências anexadas" com a lista de evidências daquele item.
2. **Given** um item não possui evidências anexadas, **When** o usuário seleciona o item, **Then** o painel informa claramente que nenhuma evidência foi anexada ainda, sem bloquear a avaliação.
3. **Given** a orientação de avaliação está visível no painel, **When** há evidências anexadas, **Then** a tela mantém separadas as seções "Evidências esperadas" e "Evidências anexadas".

---

### User Story 3 - Preservar Cadeia de Custódia das Evidências (Priority: P3)

Um responsável por compliance ou auditor precisa confiar que uma evidência anexada tem histórico rastreável, não foi apagada silenciosamente e mantém informação suficiente para verificar sua integridade ao longo do tempo.

**Why this priority**: Evidências são registros de compliance. A utilidade delas depende tanto do arquivo quanto da rastreabilidade de quem enviou, quando enviou, qual item sustenta e se houve substituição ou remoção lógica.

**Independent Test**: Anexar uma evidência, substituí-la por uma nova versão ou marcá-la como inativa, e verificar que o histórico preserva autor, data, ação executada e relação com o item original, sem apagar o registro anterior.

**Acceptance Scenarios**:

1. **Given** uma evidência já anexada, **When** um usuário autorizado substitui a evidência por uma nova versão e confirma a classificação obrigatória, **Then** o sistema preserva a versão anterior no histórico e marca a versão atual de forma clara.
2. **Given** uma evidência foi anexada por engano, **When** um usuário autorizado solicita sua remoção, **Then** o sistema realiza remoção lógica ou inativação, preservando histórico e rastreabilidade.
3. **Given** uma evidência tem seu conteúdo visualizado/baixado, substituído ou inativado, **When** a ação é concluída ou negada, **Then** a ação relevante fica auditada sem registrar conteúdo sensível do arquivo.
4. **Given** uma evidência foi substituída por nova versão, **When** o usuário consulta a seção "Evidências anexadas" do item, **Then** a lista principal exibe apenas a versão corrente e disponibiliza as versões anteriores no histórico apenas para usuários com `manage_gap`.
5. **Given** uma evidência foi inativada, **When** um usuário sem `manage_gap` consulta a seção "Evidências anexadas", **Then** a evidência inativada não aparece na lista principal nem no histórico visível para esse usuário.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta ler, baixar, substituir, inativar ou inferir evidência vinculada a item da Organização B, **Then** o sistema nega a ação com resposta genérica, sem revelar existência do recurso, e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da Organização A, **Then** apenas evidências anexadas por ou para a Organização A são visíveis e manipuláveis.
3. **Given** um Super Admin da plataforma está autenticado, **When** ele acessa evidências de uma organização, **Then** o acesso exige contexto explícito de organização, respeita as mesmas regras de auditoria e não lista evidências de múltiplos tenants em uma única visão operacional.

### Edge Cases

- O item do Gap não possui evidências anexadas: a matriz mostra estado vazio claro e continua permitindo avaliação.
- O arquivo enviado está vazio, excede o limite configurado, possui formato não permitido ou falha em validação de segurança: o envio é recusado com mensagem clara.
- O envio falha no meio do processo: nenhuma evidência incompleta aparece como válida; o usuário pode tentar novamente.
- A organização está suspensa: leitura e escrita de evidências ficam bloqueadas, preservando os registros existentes.
- A evidência contém PII ou informação confidencial: o sistema trata o arquivo como conteúdo sensível e impede exposição em logs, mensagens de erro e trilhas de auditoria.
- Dois usuários tentam anexar evidências ao mesmo item ao mesmo tempo: ambas podem ser preservadas como evidências distintas, desde que passem nas validações.
- Uma evidência é substituída: a versão anterior permanece rastreável no histórico e apenas a versão corrente aparece na lista principal do item.
- Uma evidência é inativada: ela deixa de aparecer como evidência ativa padrão, mas continua disponível no histórico apenas para usuários com `manage_gap`, conforme políticas de retenção.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema MUST permitir associar múltiplas evidências anexadas a um item específico da Matriz do Gap Analysis de uma organização.
- **FR-002**: O sistema MUST exibir, no painel de detalhe do item, uma seção separada chamada "Evidências anexadas".
- **FR-003**: O sistema MUST distinguir visual e textualmente "Evidências esperadas" (orientação canônica da plataforma) de "Evidências anexadas" (documentos reais da organização).
- **FR-004**: Usuários com permissão adequada MUST conseguir anexar nova evidência a um item do Gap Analysis.
- **FR-005**: Cada evidência anexada e cada versão de evidência MUST registrar, no mínimo, nome visível ou título, descrição opcional, item vinculado, organização, usuário responsável pelo envio, data/hora de envio, tamanho, tipo/formato, classificação obrigatória e indicador de integridade.
- **FR-005a**: O formulário de upload MUST apresentar a classificação como campo obrigatório com valor padrão "Uso interno"; o formulário de substituição MUST apresentar classificação obrigatória pré-preenchida com a classificação corrente da evidência, permitindo alteração antes do envio.
- **FR-006**: O sistema MUST aceitar os tipos de evidência definidos pela política da plataforma, incluindo categorias comuns como PDFs, imagens/prints, documentos de escritório, planilhas e arquivos compactados quando permitidos.
- **FR-007**: O sistema MUST recusar arquivos vazios, inválidos, acima do limite configurado ou não permitidos pela política de segurança.
- **FR-008**: A existência de uma ou mais evidências anexadas MUST NOT alterar automaticamente o status, prioridade ou conclusão de avaliação do item.
- **FR-009**: O sistema MUST permitir consultar a lista de evidências anexadas de um item sem sair da Matriz do Gap Analysis.
- **FR-010**: O sistema MUST permitir que evidências sejam inativadas ou removidas logicamente por usuários autorizados, preservando histórico e rastreabilidade.
- **FR-011**: O sistema MUST permitir substituição ou nova versão de uma evidência, preservando a versão anterior, exigindo classificação para a nova versão, identificando a versão corrente e exibindo apenas a versão corrente na lista principal da matriz.
- **FR-012**: O sistema MUST manter a matriz utilizável mesmo quando nenhum item possui evidências anexadas.
- **FR-013**: O sistema SHOULD preparar as evidências anexadas para reutilização futura em SoA, auditoria interna, plano de ação e dashboards, sem implementar essas integrações avançadas nesta feature.
- **FR-014**: O sistema MUST exibir uma mensagem clara quando a visualização, download, upload, inativação ou substituição de evidência não puder ser concluída.
- **FR-015**: A feature MUST NOT executar análise automática por IA, OCR, assinatura eletrônica, exportação de pacote de auditoria ou integração avançada com outros módulos neste escopo.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Evidências anexadas são dados da organização e são sempre escopadas ao tenant. Recursos afetados: evidência anexada, versão/histórico de evidência, vínculo com item do Gap Analysis e eventos de evidência. Acesso cross-tenant deve ser negado sem revelar existência e deve gerar audit log.
- **SEC-002 (Papéis e permissões)**: Usuários com permissão de visualizar Gap Analysis podem ver metadados de todas as evidências ativas/correntes do item no tenant ativo. Download ou acesso ao conteúdo de evidências públicas ou de uso interno exige `view_gap`; download ou acesso ao conteúdo de evidências confidenciais ou restritas exige `manage_gap`. Usuários com permissão de gerenciar Gap Analysis podem anexar, inativar, substituir evidências e consultar histórico, versões anteriores e evidências inativadas. Super Admin da plataforma só acessa evidências dentro de contexto explícito de organização e com auditoria.
- **SEC-003 (Auditoria)**: Operações que geram audit log: upload/envio, visualização ou download de conteúdo do arquivo, substituição/versionamento, inativação/remoção lógica, tentativa não autorizada e tentativa cross-tenant. Listar metadados de evidências no painel da matriz não gera audit log por si só. Audit log registra operação, entidade, identificador, usuário, organização e resultado, mas nunca conteúdo do arquivo, caminhos internos, tokens, dados sensíveis ou PII.
- **SEC-004 (Dados sensíveis)**: Esta feature pode tratar PII e dados confidenciais porque evidências são documentos reais da organização. Conteúdo de arquivo e metadados sensíveis devem ser protegidos em repouso quando aplicável e nunca expostos em logs, erros, telemetria ou mensagens de validação.
- **SEC-005 (Evidências/versionamento)**: A feature cria artefatos versionáveis de evidência. Alterações preservam autor, data, ação e vínculo com o item original; registros anteriores não são apagados por operações comuns e ficam acessíveis no histórico da evidência apenas para usuários com `manage_gap`.
- **SEC-006 (Degradação)**: Falhas no armazenamento ou validação de evidência bloqueiam upload/download daquele arquivo de forma fail-closed, com mensagem clara. A matriz e a avaliação do item continuam funcionando sem anexos. Isolamento de tenant é sempre fail-closed.

### Key Entities *(include if feature involves data)*

- **Evidência Anexada**: Documento ou arquivo real enviado por uma organização para sustentar um item específico do Gap Analysis. Pertence a uma Organization via tenant e inclui metadados de autoria, classificação, tipo, tamanho, integridade e estado.
- **Versão de Evidência**: Registro de uma versão específica do conteúdo anexado, preservando histórico quando uma evidência é substituída e distinguindo a versão corrente das versões anteriores.
- **Evento de Evidência**: Registro rastreável de ações relevantes sobre uma evidência, como envio, visualização/download, substituição, inativação ou tentativa negada.
- **Vínculo com Item do Gap Analysis**: Associação entre a evidência e o item avaliado da matriz, garantindo que a comprovação apareça no controle correto e no tenant correto.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Usuários autorizados conseguem anexar uma evidência válida a um item da matriz em menos de 1 minuto.
- **SC-002**: Em 100% dos itens com evidências anexadas, a matriz mostra a lista correta de evidências ao selecionar o item.
- **SC-003**: Em 100% dos itens sem evidências anexadas, a matriz mostra estado vazio claro sem bloquear a avaliação.
- **SC-004**: Usuários conseguem diferenciar visualmente "Evidências esperadas" de "Evidências anexadas" em testes de aceitação da tela.
- **SC-005**: Múltiplas evidências podem ser anexadas ao mesmo item e cada uma permanece individualmente identificável.
- **SC-006**: 100% das ações sensíveis sobre evidências geram audit log sem expor conteúdo do arquivo, caminhos internos ou dados sensíveis; a listagem de metadados no painel não gera audit log.
- **SC-007**: Uploads inválidos, vazios, grandes demais ou não permitidos são recusados sem criar evidência válida e sem quebrar a avaliação do item.
- **SC-008**: Substituição ou inativação de evidência preserva histórico, permite identificar a versão ou estado corrente e mantém a lista principal do item limitada às evidências ativas/correntes.
- **SC-011**: Usuários sem `manage_gap` não visualizam histórico, versões anteriores ou evidências inativadas; usuários com `manage_gap` conseguem consultar esses registros no tenant ativo.
- **SC-009**: Evidências confidenciais ou restritas não podem ter conteúdo acessado por usuário que possui apenas permissão de visualizar Gap Analysis.
- **SC-010**: 100% das evidências anexadas e de suas versões possuem classificação registrada; nenhuma evidência ou versão válida é criada sem classificação.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar, baixar, anexar, substituir ou inativar evidência de uma organização à qual não pertence — verificado por teste automatizado de isolamento de tenant.

## Assumptions

- A feature reutiliza a fundação multi-tenant, autenticação, RBAC, tenant scope e audit log já existentes.
- A Matriz do Gap Analysis e a orientação de avaliação da Feature 007 já estão disponíveis.
- A política de tipos de arquivo, tamanho máximo e classificação pode ser definida no planejamento e deve ser configurável sem mudar a experiência descrita nesta spec.
- O MVP registra classificação/sensibilidade obrigatória da evidência; regras avançadas de classificação podem evoluir em feature posterior.
- A lista do painel consulta metadados; "visualizar conteúdo" significa abrir ou baixar o arquivo, respeitando permissões, classificação e auditoria definida nesta spec.
