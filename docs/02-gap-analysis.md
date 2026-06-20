# Prompt para `/speckit.specify` — Módulo 2: Gap Analysis ISO/IEC 27001:2022

Pré-requisitos: Fundação multi-tenant (001), Módulo 1 — Diagnóstico e Contexto (002) e **Motor de
Workflow de Preenchimento (003)** já implementados. Esta feature introduz o **seed editável dos
requisitos das cláusulas 4–10 e dos 93 controles do Anexo A** — base para o SoA e o Plano de Ação.
Agnóstico de stack.

> **Enriquecido a partir do estudo de caso real (Nexim Tech)** — ver
> `material_de_contexto/02_Estudo de Caso Nexim/(02) GapAnalysis_ISO27001_2022_NeximTech.xlsx`
> (abas: Requisitos Cláusulas 4-10 · 93 Controles Anexo A · Dashboard · Estimativas de Esforço).
> Reutiliza o padrão transversal **"Documento Controlado SGSI (7.5)"** — definição canônica em
> [iso27001-documento-controlado.md](iso27001-documento-controlado.md).

> **Relação com o Motor de Workflow (003) — para o `/speckit.plan`:** a Gap Analysis é um **módulo
> próprio** (catálogo-seed + matriz de avaliação + dashboards de aderência), **não** um formulário
> genérico do motor. Porém **deve reusar os primitivos da 003** em vez de reinventá-los: (a) o ciclo
> **atribuir → preencher → assinar** para delegar a condução da avaliação a um preenchedor (membro
> ou externo via link tokenizado) e (b) o **congelamento de baseline** como Documento Controlado
> versionado/assinável. A 003 já entrega máquina de estados, trilha append-only, assinatura avançada
> (Lei 14.063/2020), RBAC, isolamento de tenant + RLS e auditoria — tudo a ser reaproveitado no plano.

---

```
Módulo de Gap Analysis ISO/IEC 27001:2022 da plataforma SaaS multi-tenant de Gestão de SGSI.
Avalia a aderência da organização à norma em DUAS dimensões e gera lacunas, indicadores e insumo
para o Plano de Ação e o SoA:
1. Requisitos do sistema de gestão — Cláusulas 4 a 10 da ISO/IEC 27001:2022.
2. Controles do Anexo A — os 93 controles da ISO/IEC 27002:2022, em 4 temas: Organizacional
   (A.5, 37 controles), Pessoas (A.6, 8), Físico (A.7, 14) e Tecnológico (A.8, 34).

Esta feature roda sobre a fundação multi-tenant e o Módulo 1 (Diagnóstico/Contexto) já existentes.
Todo dado pertence a uma organização e respeita o isolamento de tenant; acesso cross-tenant é
negado (404/403 sem revelar existência) e auditado.

== Catálogo-base (seed) versionável ==
A plataforma fornece como dado inicial (seed), mantido por ela e versionável:
- Os requisitos das Cláusulas 4–10 (com cláusula, subcláusula e resumo do requisito da norma).
- Os 93 controles do Anexo A (identificador ex.: A.5.1, nome do controle, tema e texto/objetivo
  do controle conforme a norma).
Cada organização recebe sua própria cópia editável do catálogo: pode personalizar (renomear,
adicionar requisitos/controles próprios, agrupar) e marcar itens como não aplicáveis, sem afetar
outras organizações nem o catálogo-base. Atualização da norma/seed (nova versão) nunca apaga
avaliações já feitas — é uma migração versionada e rastreável.

== Avaliação (matriz de gap analysis, por organização) ==
Para CADA item das duas dimensões, registrar:
- Status de conformidade (escala da norma): Atende totalmente | Atende parcialmente | Não atende |
  Não aplicável | (Não preenchido).
- Constatações ("o que foi constatado") — situação atual observada.
- Ações de adequação necessárias.
- Prioridade: Crítica | Alta | Média | Baixa.
- Responsável.
- Prazo.
- Evidência existente (referência textual nesta fase; o vínculo com arquivos reais vem no Módulo
  de Evidências).
- Observações (ex.: nota do consultor).
- (Controles do Anexo A) Justificativa de exclusão quando "Não aplicável" — alimenta diretamente
  o SoA.
- (Opcional) Nível de maturidade e estimativa de esforço do item — insumo para priorização e para
  o Plano de Ação.

== Condução atribuível e assinável (reusa o motor de workflow) ==
A condução da Gap Analysis pode ser DELEGADA: um Consultor/Admin atribui a avaliação (ou um recorte
dela) a um preenchedor — membro da organização ou respondente externo via link tokenizado — que é
notificado, assume, preenche e envia, com a mesma mecânica de ciclo de vida, trilha imutável e
notificação já existente. Concluída a avaliação, ela pode ser ASSINADA eletronicamente (nível
avançada) e congelada como uma baseline versionada (documento controlado), gerando selo de
integridade. Acesso cross-tenant negado (404/403) e auditado, como no restante da plataforma.

== Indicadores e visões (dashboard) ==
- Percentual de aderência calculado de forma consistente com os status, considerando apenas itens
  aplicáveis — geral e por dimensão (Cláusulas 4–10 vs Controles do Anexo A).
- Distribuição por status (contagem de Atende/Parcial/Não atende/Não aplicável) por dimensão.
- Aderência por cláusula (4 a 10) e por tema do Anexo A (Organizacional/Pessoas/Físico/Tecnológico).
- Lista de lacunas: itens aplicáveis com status "Não atende" ou "Atende parcialmente", ordenável
  por prioridade — é o insumo direto do Plano de Ação (Módulo 4).
- (Opcional) Estimativa de esforço consolidada das ações de adequação.

== Linha de base (baseline) e rastreabilidade ==
- O gap analysis pode ser "congelado" como uma linha de base versionada (snapshot), reaproveitando
  o padrão de Documento Controlado SGSI (versão, data, status, aprovador, histórico imutável),
  permitindo comparar a evolução da aderência entre baselines ao longo do tempo.
- Cada avaliação de controle do Anexo A é rastreável até o item correspondente do SoA (Módulo 3);
  cada lacuna é rastreável até a ação correspondente do Plano de Ação (Módulo 4).

Requisitos observáveis (critérios de aceitação):
- A matriz de uma organização só é visível/editável por usuários dela com a permissão adequada;
  acesso cross-tenant é negado (404/403) e auditado.
- Personalizar o catálogo de uma organização nunca altera o de outra nem o seed-base da plataforma.
- O percentual de aderência é calculado de forma consistente com os status registrados e considera
  apenas itens aplicáveis; geral, por dimensão, por cláusula e por tema batem com os itens.
- O seed cobre integralmente as Cláusulas 4–10 e os 93 controles do Anexo A 2022, e é versionável
  (uma atualização do seed não apaga nem sobrescreve silenciosamente avaliações existentes).
- Marcar um controle como "Não aplicável" exige justificativa, que fica disponível para o SoA.
- Alterações em itens da matriz geram histórico (e baseline gera versão) e registro de auditoria.
- A condução da avaliação pode ser atribuída a um preenchedor (membro ou externo via link tokenizado)
  e, ao ser assinada, congela uma baseline imutável com selo de integridade verificável.

Fora de escopo desta feature:
- Declaração de Aplicabilidade formal (SoA) — Módulo 3, que consome a aplicabilidade/justificativas
  daqui.
- Plano de Ação consolidado e acompanhamento de execução — Módulo 4, que consome as lacunas daqui.
- Upload e versionamento de arquivos de evidência — Módulo de Evidências.
- Avaliação/cálculo de risco — Módulo de Riscos.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
