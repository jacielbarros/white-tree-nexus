# Feature Specification: Preview Interativo e Posicionamento Visual de Assinatura em PDF

**Feature Branch**: `010-interactive-pdf-signature`

**Created**: 2026-06-23

**Status**: Draft

**Input**: User description: "Implementar a feature Preview Interativo e Posicionamento Visual de Assinatura em Documentos PDF para evoluir a capacidade de documentos imprimíveis, pré-visualizáveis e assináveis da plataforma White Tree Nexus."

## Clarifications

### Session 2026-06-23

- Q: Quando a posição do selo deve ser persistida no fluxo de assinatura? → A: Salvar uma posição confirmada no preview antes da assinatura; ao assinar, essa posição é congelada no documento assinado.
- Q: Qual sistema de coordenadas deve ser persistido para a posição do selo? → A: Armazenar posição em coordenadas canônicas da página do PDF, incluindo dimensões da página usadas na validação.
- Q: Como zoom, escala e rolagem devem afetar o posicionamento? → A: Zoom/escala/rolagem afetam apenas a visualização; ao confirmar, a posição é convertida para coordenadas canônicas do PDF.
- Q: O selo pode ser posicionado em qualquer área da página? → A: Posição livre dentro da página, exceto áreas bloqueadas ou reservadas pelo template/política documental.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Visualizar PDF de preview inline (Priority: P1)

Como usuário autorizado dos módulos de Contexto, Gap Analysis ou SoA, quero abrir o PDF preliminar diretamente na tela, navegar pelas páginas e confirmar o conteúdo antes de decidir baixar ou assinar o documento.

**Why this priority**: O usuário precisa revisar o documento que será assinado sem sair do fluxo de trabalho. Sem preview inline, a assinatura continua dependendo de download manual e perde fluidez operacional.

**Independent Test**: Gerar um preview existente de Contexto, Gap Analysis ou SoA, abrir o visualizador na própria tela, navegar entre páginas e confirmar que o documento exibido corresponde ao preview ativo, com indicação clara de documento preliminar/não assinado.

**Acceptance Scenarios**:

1. **Given** um usuário com permissão de visualizar Gap Analysis e um preview ativo, **When** ele seleciona "Pré-visualizar", **Then** o PDF preliminar é exibido na tela com status claro de "Preview / Não assinado".
2. **Given** um PDF preliminar com múltiplas páginas, **When** o usuário navega entre páginas e altera o zoom, **Then** o conteúdo permanece legível e o usuário consegue retornar ao fluxo de assinatura sem baixar o arquivo.
3. **Given** um preview expirado, desatualizado ou bloqueado por classificação, **When** o usuário tenta abrir o preview inline, **Then** o sistema impede a visualização e apresenta uma mensagem clara sem expor conteúdo do documento.

---

### User Story 2 - Posicionar selo visual de assinatura (Priority: P1)

Como usuário autorizado a assinar documentos, quero escolher visualmente em qual página e posição o selo de assinatura será aplicado, para que o PDF final assinado seja adequado ao layout do documento e aos padrões da organização.

**Why this priority**: O valor principal da evolução é controlar onde a assinatura aparece. Isso reduz retrabalho, evita selos sobre conteúdo relevante e prepara documentos para uso em auditorias e aprovações formais.

**Independent Test**: Abrir um preview ativo, posicionar o selo em uma página válida, confirmar a posição, assinar o documento e verificar que o PDF final contém o selo na posição escolhida.

**Acceptance Scenarios**:

1. **Given** um preview ativo, **When** o usuário move o selo de assinatura para uma área válida da página e confirma, **Then** o sistema registra a página, coordenadas, dimensões e origem da posição como escolha do usuário.
2. **Given** um preview ativo sem posicionamento manual, **When** o usuário assina usando a posição padrão, **Then** o sistema aplica o selo no canto inferior direito da última página, salvo quando o template indicar outro local padrão.
3. **Given** uma posição fora dos limites da página ou incompatível com o documento, **When** o usuário tenta assinar, **Then** o sistema bloqueia a assinatura e solicita um posicionamento válido.
4. **Given** uma posição confirmada em um preview ativo, **When** o usuário assina o documento, **Then** o sistema congela exatamente essa posição no documento assinado e preserva o registro confirmado no histórico.
5. **Given** um usuário revisando o PDF com zoom, escala ou rolagem alterados, **When** ele confirma a posição do selo, **Then** o sistema converte a posição visual para coordenadas canônicas do PDF antes de persistir e validar.
6. **Given** um template ou política documental com áreas bloqueadas/reservadas, **When** o usuário tenta posicionar o selo sobre uma dessas áreas, **Then** o sistema recusa a posição e orienta o usuário a escolher uma área permitida.

---

### User Story 3 - Assinar com metadados preparados para assinatura digital futura (Priority: P2)

Como organização que usa documentos controlados do SGSI, quero que documentos assinados indiquem claramente o tipo de assinatura utilizado e preservem metadados compatíveis com uma futura evolução para assinatura digital PAdES/ICP-Brasil.

**Why this priority**: A assinatura interna atual resolve o MVP, mas o produto precisa evoluir para padrões formais de assinatura digital sem refazer a cadeia de custódia ou ambiguidade sobre o tipo de assinatura aplicada.

**Independent Test**: Assinar um documento com assinatura eletrônica interna e verificar no PDF final, histórico e metadados que o tipo de assinatura é identificado como interno, com selo visual separado da futura assinatura digital criptográfica.

**Acceptance Scenarios**:

1. **Given** um documento assinado com assinatura eletrônica interna, **When** o usuário visualiza o histórico, **Then** o sistema exibe tipo de assinatura, assinante, data/hora, hash, versão do template e posição do selo.
2. **Given** uma assinatura interna com selo visual, **When** o usuário baixa o PDF final, **Then** o documento não sugere ser uma assinatura PAdES/ICP-Brasil e identifica claramente o tipo de assinatura usado.
3. **Given** a necessidade futura de assinatura digital, **When** novos tipos de assinatura forem adicionados, **Then** os documentos já assinados permanecem imutáveis e verificáveis com o tipo de assinatura original.

---

### Tenant Isolation Scenarios *(mandatory if feature touches domain data)*

1. **Given** um usuário da Organização A autenticado, **When** ele tenta abrir, posicionar selo, assinar, baixar ou verificar preview/documento assinado da Organização B, **Then** o sistema nega com 404/403 sem revelar existência e registra a tentativa em audit log.
2. **Given** um Consultor vinculado às Organizações A e B, **When** ele opera no contexto da Organização A, **Then** apenas previews, PDFs, posições de assinatura e documentos assinados da Organização A são visíveis ou alteráveis.
3. **Given** um Super Admin da plataforma sem contexto explícito de organização, **When** ele tenta visualizar ou assinar um documento de tenant, **Then** o sistema nega a operação ou exige contexto explícito auditado antes de qualquer acesso ao conteúdo.

### Edge Cases

- O que acontece quando o preview expira enquanto o usuário está com o PDF aberto na tela?
- O que acontece quando o documento é atualizado ou o template muda após a abertura do preview e antes da assinatura?
- Como o sistema se comporta quando o usuário tenta posicionar o selo fora da página, com tamanho inválido ou sobre uma área não permitida?
- Como o sistema informa ao usuário que uma região está bloqueada ou reservada pelo template/política documental?
- O que acontece quando o PDF preliminar não pode ser carregado no visualizador inline?
- Como o sistema trata documentos com muitas páginas, página rotacionada, zoom alterado ou dimensões de página diferentes?
- Como o sistema preserva a posição correta quando o usuário confirma o selo em diferentes níveis de zoom, escala de tela ou rolagem?
- O que acontece quando a organização é suspensa durante o fluxo de preview, posicionamento ou assinatura?
- Como o sistema evita que coordenadas manipuladas no cliente sejam aceitas sem validação?
- O que acontece quando um documento assinado antigo é aberto após mudanças futuras no template, artefato original ou política de assinatura?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que usuários autorizados abram o PDF preliminar diretamente na tela, sem exigir download prévio.
- **FR-002**: O sistema DEVE exibir indicação visual inequívoca de que o documento em preview ainda não é o documento final assinado.
- **FR-003**: O usuário DEVE conseguir navegar entre páginas e ajustar a visualização do PDF preliminar durante a revisão.
- **FR-004**: O sistema DEVE garantir que o preview inline corresponda ao mesmo snapshot de dados usado na assinatura.
- **FR-005**: O usuário autorizado a assinar DEVE conseguir posicionar visualmente um selo de assinatura em uma página válida do PDF.
- **FR-006**: O sistema DEVE oferecer uma posição padrão de assinatura quando o usuário não escolher uma posição manual; ao assinar sem posição manual confirmada, o backend DEVE materializar uma posição padrão válida como registro auditável antes de congelá-la no documento assinado.
- **FR-007**: A posição padrão DEVE ser o canto inferior direito da última página, salvo quando o template ou política documental definir outro padrão permitido.
- **FR-008**: O sistema DEVE registrar página, coordenadas canônicas da página do PDF, dimensões do selo, dimensões da página usadas na validação, unidade/sistema de coordenadas, origem do posicionamento, usuário e data/hora da escolha.
- **FR-008a**: O sistema DEVE persistir a posição confirmada no preview antes da assinatura e manter histórico auditável das confirmações/alterações de posição.
- **FR-009**: O sistema DEVE validar no servidor se a posição, página, dimensões do selo e dimensões da página informadas correspondem ao PDF do preview e estão dentro dos limites válidos do documento.
- **FR-009a**: Zoom, escala, viewport e rolagem DEVEM afetar apenas a visualização; a posição persistida e validada DEVE ser sempre convertida para coordenadas canônicas do PDF.
- **FR-010**: O sistema DEVE impedir a assinatura quando a posição do selo for inválida, adulterada, fora da página, expirada ou incompatível com o preview.
- **FR-010a**: O sistema DEVE permitir posicionamento livre dentro da página, exceto em áreas bloqueadas ou reservadas por template ou política documental.
- **FR-010b**: O sistema DEVE validar no servidor que o selo não invade áreas bloqueadas/reservadas antes de confirmar a posição e antes de assinar.
- **FR-011**: O sistema DEVE gerar o PDF final assinado com o selo visual aplicado na posição confirmada.
- **FR-012**: O documento assinado DEVE permanecer imutável, preservando snapshot, versão do template, hash, posição do selo, tipo de assinatura, assinante e data/hora.
- **FR-012a**: Ao assinar, o sistema DEVE congelar a última posição confirmada válida do preview no documento assinado; se nenhuma posição manual existir, DEVE congelar a posição padrão materializada pelo backend; mudanças posteriores no preview, template ou política de posição não alteram o documento já assinado.
- **FR-013**: O histórico de documentos assinados DEVE exibir tipo de assinatura, versão, hash, assinante, data/hora e posição do selo quando aplicável.
- **FR-014**: O sistema DEVE distinguir assinatura eletrônica interna, selo visual e assinatura digital criptográfica futura.
- **FR-015**: O PDF final DEVE identificar claramente o tipo de assinatura usado e não deve apresentar selo visual interno como se fosse assinatura PAdES/ICP-Brasil.
- **FR-016**: A feature DEVE preservar metadados necessários para futura evolução para assinatura digital PAdES/ICP-Brasil, sem implementar essa assinatura no MVP.
- **FR-017**: O usuário DEVE continuar podendo baixar o PDF preliminar e o PDF final assinado quando possuir permissão e classificação permitir.
- **FR-018**: A experiência DEVE funcionar para documentos de Contexto, Gap Analysis e SoA.
- **FR-019**: O sistema DEVE apresentar mensagens claras para falhas de carregamento, posição inválida, preview expirado, preview desatualizado, permissão insuficiente e bloqueio por classificação.
- **FR-020**: O sistema DEVE impedir que a alteração futura do template, do artefato original ou da política de posicionamento altere documentos já assinados.

### Multi-Tenancy & Security Requirements *(mandatory)*

- **SEC-001 (Isolamento de tenant)**: Todo dado manipulado por esta feature é escopado pela organização do usuário. Recursos afetados: previews de PDF, sessões/estado de visualização, posições de selo, documentos assinados, metadados de assinatura e eventos de auditoria. Acesso cross-tenant retorna 404/403 sem revelar existência e gera audit log.
- **SEC-002 (Papéis e permissões)**: Usuários com permissão de visualizar o módulo podem abrir preview inline e baixar documentos permitidos. Usuários com permissão de aprovar/assinar o tipo documental podem posicionar selo e assinar. Admins de organização podem gerenciar padrões de template quando permitido. Super Admin só acessa dados de tenant com contexto explícito e auditado.
- **SEC-003 (Auditoria)**: Operações que geram audit log: abrir preview inline, baixar preview, alterar/confirmar posição, assinar, baixar PDF final, verificar documento, tentativas negadas e falhas relevantes de validação. Cada registro grava metadados mínimos como operação, tipo documental, entidade, usuário, tenant, resultado e motivo sanitizado.
- **SEC-004 (Dados sensíveis)**: Esta feature trata dados confidenciais e potencialmente PII dentro dos PDFs e snapshots. Conteúdo do PDF, storage key, snapshot sensível, tokens, caminhos internos e PII não podem ser gravados em audit log, mensagens de erro ou telemetria. O acesso ao PDF respeita classificação/sensibilidade.
- **SEC-005 (Evidências/versionamento)**: A feature altera artefatos versionáveis de compliance ao criar documentos assinados e metadados de assinatura. Documentos assinados, snapshots, posição do selo e assinaturas são registros imutáveis ou append-only, preservando autor, data/hora e ação.
- **SEC-006 (Degradação)**: Falha de storage, renderização, validação de PDF, assinatura ou verificação de permissões deve bloquear preview/assinatura/download de modo fail-closed. Isolamento de tenant é sempre fail-closed.

### Key Entities *(include if feature involves data)*

- **PDF Preview View State**: Representa a abertura/revisão inline de um preview por um usuário em um tenant, com status de carregamento, página atual e metadados auditáveis, sem armazenar conteúdo do PDF em log.
- **Signature Placement**: Representa a posição confirmada do selo visual vinculada primeiro ao preview e, no momento da assinatura, congelada no documento assinado. Contém tenant, preview, documento assinado quando existir, página, coordenadas canônicas da página do PDF, dimensões do selo, dimensões da página usadas na validação, unidade, origem, usuário responsável, data/hora, status e histórico auditável de alterações.
- **Signature Appearance**: Representa o selo visual aplicado no documento, incluindo textos/metadados visíveis, tipo de assinatura, dimensões, relação com o documento assinado e regras de áreas permitidas/bloqueadas quando definidas pelo template ou política documental.
- **Signature Method**: Representa o tipo de assinatura usada ou preparada, distinguindo assinatura eletrônica interna, PAdES, ICP-Brasil e provedor externo futuro.
- **Signed Document Custody Metadata**: Representa metadados preservados do documento assinado: hash, snapshot, versão do template, posição do selo, tipo de assinatura, assinante, data/hora e identificador verificável.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 95% dos usuários autorizados conseguem abrir o PDF de preview inline em até 5 segundos após a geração do preview em condições normais de uso local.
- **SC-002**: Usuários conseguem revisar, posicionar o selo e iniciar a assinatura de um documento em até 2 minutos para documentos de até 20 páginas.
- **SC-003**: 100% dos documentos assinados com selo visual preservam posição, página, dimensões, tipo de assinatura, hash, snapshot e versão do template no histórico.
- **SC-004**: 100% das tentativas de assinatura com posição inválida são bloqueadas antes da geração do PDF final.
- **SC-005**: 100% dos PDFs finais assinados exibem o selo na posição confirmada ou na posição padrão definida quando o usuário não escolhe manualmente.
- **SC-006**: Usuários conseguem distinguir visualmente documentos em preview, documentos assinados internamente e documentos preparados para assinatura digital futura sem ambiguidade.
- **SC-ISO (mandatory)**: Nenhum usuário consegue ler, listar, abrir, posicionar, assinar, baixar ou verificar documento de uma organização à qual não pertence, verificado por teste automatizado de isolamento de tenant.

## Assumptions

- A feature reutiliza a fundação multi-tenant, RBAC, auditoria, storage de documentos, templates versionados e motor de assinatura interna já implementados pela Feature 009.
- PAdES/ICP-Brasil será preparado conceitualmente por tipo de assinatura e metadados, mas a assinatura digital criptográfica real fica fora do MVP desta feature.
- O selo visual é uma representação de assinatura eletrônica interna e não equivale, por si só, a assinatura digital PAdES/ICP-Brasil.
- A posição padrão do selo será usada quando o usuário autorizado preferir assinar sem posicionamento manual.
- Regras avançadas de múltiplos assinantes, workflow de aprovação em cadeia e carimbo de tempo externo serão tratadas em features futuras.
- A escolha do mecanismo técnico de visualização de PDF será definida na fase de planejamento, mantendo a experiência exigida de visualização inline controlada.
