# Prompt para `/speckit.specify` — Módulo 1: Diagnóstico e Contexto da Organização

Pré-requisito: a Fundação multi-tenant (`00-fundacao-multi-tenant.md`) já especificada.
Agnóstico de stack — a stack vem do `/speckit.plan`.

---

```
Módulo de Diagnóstico e Contexto da Organização da plataforma SaaS multi-tenant de
Gestão de SGSI ISO/IEC 27001:2022. Apoia o entendimento do contexto da organização
(cláusula 4 da norma) como base para gap analysis, riscos e escopo do SGSI.

Esta feature roda sobre a fundação multi-tenant já existente (organizações, autenticação,
RBAC, isolamento de tenant e auditoria). Todo dado deste módulo pertence a uma
organização e respeita o isolamento de tenant.

Escopo desta feature:
- Questionário de contexto da organização, preenchível de forma incremental (salvar
  rascunho e retomar), com as seções:
  - Identificação: nome, segmento de atuação, tamanho, nº de colaboradores, nº de
    clientes, nº de filiais, países/regiões de atuação, modelo de trabalho
    (presencial/remoto/híbrido).
  - Estrutura: organograma, departamentos, responsáveis por área, donos de processo.
  - Negócio: produtos e serviços principais, processos críticos.
  - Tecnologia: tecnologias utilizadas, provedores de nuvem, sistemas internos.
  - Dados tratados: dados pessoais, dados financeiros, dados sensíveis.
  - Cadeia de suprimento: fornecedores críticos.
  - Requisitos: legais e regulatórios, contratuais.
  - Partes interessadas: partes interessadas e suas necessidades e expectativas.
  - Escopo preliminar do SGSI.
- Visão consolidada do contexto da organização, legível, a partir das respostas.
- Sugestão de riscos, controles e requisitos potencialmente relevantes derivada das
  respostas (heurística/regras nesta fase; IA é um módulo posterior e opt-in). As
  sugestões são apenas indicativas e sempre editáveis/descartáveis pelo usuário.
- Versionamento do diagnóstico: cada revisão preserva o histórico (quem alterou, quando,
  o quê), pois o contexto muda ao longo do tempo e isso alimenta a Revisão pela Direção.

Requisitos observáveis (critérios de aceitação):
- O diagnóstico de uma organização só é visível e editável por usuários dela com a
  permissão adequada; tentativa cross-tenant é negada e auditada.
- O rascunho pode ser salvo parcialmente e retomado sem perda de dados.
- A visão consolidada reflete fielmente as respostas mais recentes.
- Sugestões automáticas nunca são aplicadas sem ação explícita do usuário.
- Alterações no diagnóstico geram histórico imutável e registro de auditoria.

Fora de escopo desta feature:
- Cálculo de gap analysis e SoA (módulos próprios).
- Geração de sugestões por IA (módulo de IA, posterior e opt-in por organização).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
