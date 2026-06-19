# Prompt para `/speckit.specify` — Módulo 1: Diagnóstico e Contexto da Organização

Pré-requisito: a Fundação multi-tenant (`00-fundacao-multi-tenant.md`) já especificada/implementada.
Agnóstico de stack — a stack vem do `/speckit.plan`, guiado pela constitution.

> **Enriquecido a partir do estudo de caso real (Nexim Tech) do material de curso Lead
> Implementer** — ver `material_de_contexto/02_Estudo de Caso Nexim/` (artefatos SGSI-DOC-001/002/003).
> O padrão **"Documento Controlado SGSI (cláusula 7.5)"** citado abaixo é **transversal** — definição
> canônica e reutilizável em [iso27001-documento-controlado.md](iso27001-documento-controlado.md),
> referenciada por todos os módulos e realizada como capacidade no Módulo 5.

---

```
Módulo de Diagnóstico e Contexto da Organização da plataforma SaaS multi-tenant de Gestão de
SGSI ISO/IEC 27001:2022. Cobre a Cláusula 4 da norma (Contexto da organização): entender a
organização e seu contexto (4.1), entender as necessidades e expectativas das partes
interessadas (4.2) e determinar o escopo do SGSI (4.3). É a base de que dependem Gap Analysis,
Gestão de Riscos e SoA.

Esta feature roda sobre a fundação multi-tenant já existente (organizações, autenticação, RBAC,
isolamento de tenant e auditoria). Todo dado deste módulo pertence a uma organização (tenant) e
respeita estritamente o isolamento de tenant; acesso cross-tenant é negado (404/403 sem revelar
existência) e auditado.

== Artefatos produzidos ==
O módulo produz três documentos controlados, inter-relacionados e rastreáveis entre si, mais um
diagnóstico-questionário que os alimenta:
1. Análise de Contexto da Organização (cláusula 4.1) — questões internas e externas.
2. Mapa de Partes Interessadas (cláusula 4.2) — partes, requisitos e estratégia de relacionamento.
3. Declaração de Escopo do SGSI (cláusula 4.3) — derivada das duas anteriores.
A Declaração de Escopo referencia explicitamente a Análise de Contexto e o Mapa de Partes
Interessadas como suas entradas (rastreabilidade verificável).

== Documento Controlado SGSI (cláusula 7.5) — padrão transversal ==
Os três artefatos deste módulo são "documentos controlados": identificador estável (ex.:
SGSI-DOC-002), versão + histórico append-only (data/autor/natureza da alteração/aprovador), status
no ciclo de vida (rascunho → em revisão → aprovado/em vigor → obsoleto → retido → descartado),
classificação (Público/Uso Interno/Confidencial/Restrito), datas de emissão e próxima análise
crítica, cadeia elaborado/revisado/aprovado, referências cruzadas e normativas. Definição canônica
e reutilizável em docs/iso27001-documento-controlado.md; a capacidade de versionamento/aprovação/
classificação/retenção é realizada pelo Módulo 5 (Gestão de Evidências / Informação Documentada).
Estes campos não são reinventados por documento (Princípio IV da constitution).

== Escopo desta feature ==

Diagnóstico-questionário (entrada de dados, incremental):
- Preenchível de forma incremental: salvar rascunho e retomar sem perda de dados.
- Seções de levantamento: Identificação (razão social, segmento, porte, nº de colaboradores,
  nº de clientes, filiais, países/regiões, modelo de trabalho presencial/remoto/híbrido);
  Estrutura (organograma, departamentos, responsáveis por área, donos de processo); Negócio
  (produtos/serviços, processos críticos, fontes de receita); Tecnologia (tecnologias, provedores
  de nuvem/região, sistemas internos, modelo SaaS/multitenant se aplicável); Dados tratados
  (pessoais, sensíveis, financeiros; papel de controlador/operador LGPD); Cadeia de suprimento
  (fornecedores críticos); Requisitos (legais, regulatórios, contratuais).
- O diagnóstico alimenta os três artefatos abaixo; campos do diagnóstico são reutilizados como
  entradas das análises (não redigitar).

Análise de Contexto da Organização (4.1):
- Registro de "questões" (issues) internas e externas, cada uma com: descrição, origem
  (interno/externo), classificação por framework e impacto potencial sobre os resultados
  pretendidos do SGSI em três níveis (Alto / Médio / Baixo).
- Organização das questões por frameworks de análise: contexto externo via PESTEL (Político,
  Econômico, Social, Tecnológico, Ecológico/ambiental, Legal/regulatório); contexto interno via
  SWOT (forças, fraquezas, oportunidades, ameaças). Os frameworks são o esquema de classificação;
  o usuário pode registrar a metodologia/fontes utilizadas.
- Síntese dos "resultados pretendidos do SGSI" da organização (referência para avaliar impacto).

Mapa de Partes Interessadas (4.2):
- Cadastro de partes interessadas (internas e externas), cada uma com: nome/categoria, tipo
  (interna/externa), requisitos e expectativas (classificados como legal / regulatório /
  contratual / expectativa), e como o SGSI endereça cada requisito.
- Classificação por matriz Poder × Interesse (Mendelow), derivando a estratégia de relacionamento:
  Poder alto + Interesse alto = "Gerenciar de perto"; Poder alto + Interesse baixo/médio = "Manter
  satisfeito"; Poder baixo/médio + Interesse alto = "Manter informado"; Poder baixo/médio +
  Interesse baixo/médio = "Monitorar".

Declaração de Escopo do SGSI (4.3):
- Determinada a partir das TRÊS entradas obrigatórias da cláusula 4.3: (a) as questões internas e
  externas (da Análise de Contexto); (b) os requisitos das partes interessadas (do Mapa); (c) as
  interfaces e dependências entre as atividades da organização e de terceiros.
- Conteúdo: limites e aplicabilidade do SGSI; inclusões e exclusões justificadas (o que está
  dentro/fora e por quê); unidades/processos/localizações/ativos cobertos; interfaces e
  dependências (ex.: provedores de nuvem).
- Rastreabilidade: a Declaração referencia a Análise de Contexto e o Mapa de Partes Interessadas
  vigentes que a fundamentaram.

Visão consolidada e sugestões:
- Visão consolidada legível do contexto (Cláusula 4) a partir das respostas e dos três artefatos,
  refletindo sempre a versão mais recente aprovada (ou o rascunho corrente, claramente marcado).
- Sugestão de questões, partes interessadas, requisitos e controles potencialmente relevantes,
  derivada por heurística/regras a partir do diagnóstico (ex.: trata dados pessoais ⇒ sugerir
  ANPD/titulares como partes interessadas e requisitos LGPD). As sugestões são apenas indicativas,
  nunca aplicadas sem ação explícita do usuário, e sempre editáveis/descartáveis. (IA é módulo
  posterior e opt-in por organização — fora desta feature.)

== Requisitos observáveis (critérios de aceitação) ==
- Os dados e artefatos de uma organização só são visíveis/editáveis por usuários dela com a
  permissão adequada; tentativa de acesso cross-tenant é negada (404/403 sem revelar existência) e
  registrada em auditoria.
- O diagnóstico pode ser salvo parcialmente como rascunho e retomado sem perda de dados.
- Cada documento controlado expõe identificador, versão, status, classificação, datas (emissão e
  próxima análise crítica) e a cadeia de aprovação (elaborado/revisado/aprovado por).
- Toda alteração relevante gera nova versão e uma entrada imutável no histórico de versões (data,
  autor, natureza da alteração, aprovador); o histórico nunca é editado nem apagado.
- A transição de status segue o ciclo de vida (rascunho → em revisão → aprovado/em vigor →
  obsoleto) e cada transição é auditada; aprovar exige o papel autorizado.
- A Declaração de Escopo referencia a Análise de Contexto e o Mapa de Partes Interessadas que a
  fundamentaram; remover/obsoletar um artefato referenciado é sinalizado (não quebra silenciosa da
  rastreabilidade).
- A classificação Poder × Interesse de uma parte interessada determina automaticamente a estratégia
  de relacionamento sugerida (Gerenciar de perto / Manter satisfeito / Manter informado / Monitorar).
- A visão consolidada reflete fielmente os dados mais recentes.
- Sugestões automáticas nunca são aplicadas sem ação explícita do usuário.

== Fora de escopo desta feature ==
- Cálculo de Gap Analysis, Statement of Applicability (SoA) e avaliação/tratamento de riscos
  (módulos próprios) — embora o contexto/escopo aqui produzidos sejam entradas deles.
- Geração de sugestões por IA (módulo de IA, posterior e opt-in por organização).
- Um motor de workflow de aprovação genérico/complexo: aqui basta o ciclo de vida de status com
  papel aprovador registrado e auditado.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
