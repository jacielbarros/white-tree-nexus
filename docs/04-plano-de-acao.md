# Prompt para `/speckit.specify` — Módulo 4: Plano de Ação

Pré-requisitos: Fundação multi-tenant, Módulo 1 (Diagnóstico), Módulo 2 (Gap Analysis) e Módulo 3
(SoA) especificados. Agnóstico de stack.

> **Enriquecido a partir do estudo de caso real (Nexim Tech)** — ver
> `material_de_contexto/02_Estudo de Caso Nexim/(13) ...SOA + Ativos.xlsx` (aba PTR),
> `material_de_contexto/04_Templates para Alunos/Mod 4 Plano de Tratamento Risco Detalhado.xlsx`
> e `(03) Cronograma_SGSI_NeximTech.xlsx` (fases PDCA, WBS, marcos, entregáveis).

---

```
Módulo de Plano de Ação da plataforma SaaS multi-tenant de Gestão de SGSI ISO/IEC 27001:2022.
Centraliza as ações de remediação, tratamento e melhoria do SGSI — originadas de lacunas do Gap
Analysis, do tratamento de riscos, de constatações de auditoria interna ou de controles
específicos — com responsáveis, prazos, prioridade, dependências e acompanhamento de progresso.

Esta feature roda sobre a fundação multi-tenant e os Módulos 1–3 já existentes. Todo dado pertence
a uma organização e respeita o isolamento de tenant; acesso cross-tenant é negado (404/403 sem
revelar existência) e auditado.

== Ação / tarefa ==
Cadastro e gestão de ações com:
- Título e descrição.
- Origem (tipada, com referência rastreável ao item de origem quando aplicável):
  - Lacuna do Gap Analysis (Módulo 2);
  - Tratamento de risco (Módulo de Riscos) — incluindo a opção de tratamento da ISO/IEC 27005:2022:
    Modificar (reduzir) | Reter (aceitar) | Evitar | Compartilhar (transferir);
  - Constatação de auditoria interna (módulo posterior);
  - Controle do Anexo A / requisito de cláusula (vínculo ao SoA / Gap Analysis);
  - Ação avulsa de melhoria.
- Controles do Anexo A relacionados (quando a ação implementa/reforça controles).
- Responsável (e apoio/co-responsável).
- Prazo; prioridade: Crítica | Alta | Média | Baixa; esforço estimado (ex.: Baixo/Médio/Alto).
- Status: Não iniciada | Em andamento | Concluída | Cancelada; e percentual de progresso.
- Dependências entre ações (predecessoras), para sequenciamento.
- Evidências vinculadas (referência; o arquivo real vem do Módulo de Evidências).
- Comentários.
- Histórico de alterações append-only (mudanças de status, responsável, prazo, progresso).

== Organização e acompanhamento ==
- Agrupamento opcional por fase do projeto (modelo PDCA: Plan/Do/Check/Act) e por marcos críticos
  (marco com data-limite, atraso máximo tolerado, risco se atrasar e status) — para visão de
  cronograma de implementação do SGSI.
- Listagem e filtros das ações (por responsável, status, prioridade, origem, fase, prazo), com
  destaque para ações atrasadas (prazo vencido e não concluídas) e ações críticas.
- Visão consolidada de progresso: % concluído geral, por fase e por origem; contagem por status;
  ações atrasadas/críticas. Insumo direto para a Revisão pela Direção.
- Notificações e lembretes automáticos por e-mail (atribuição, proximidade do prazo, atraso),
  tratando falha de envio de forma graciosa (fail-soft): registra aviso e não bloqueia a operação.

== Rastreabilidade ==
- Cada ação é rastreável até sua origem: lacuna (Gap Analysis), risco (Registro de Riscos / Plano
  de Tratamento), constatação (Auditoria) ou controle (SoA).
- O conjunto de ações de tratamento de um risco compõe, em conjunto, o Plano de Tratamento de
  Riscos daquele risco (consumido pelo Módulo de Riscos).

Requisitos observáveis (critérios de aceitação):
- As ações de uma organização só são visíveis/editáveis por usuários dela com a permissão
  adequada; acesso cross-tenant é negado (404/403) e auditado.
- Mudanças de status, responsável, prazo e progresso ficam registradas no histórico imutável da
  ação.
- Uma ação atrasada é identificada de forma consistente (prazo vencido e não concluída); ações
  críticas são destacadas.
- O percentual de progresso consolidado (geral/por fase/por origem) é consistente com as ações.
- Ações com origem registram referência rastreável ao item de origem (lacuna/risco/constatação/
  controle).
- Lembretes são disparados conforme regras configuráveis; falha de e-mail é registrada como aviso
  e não impede o uso do módulo.
- Toda criação/alteração relevante gera registro de auditoria.

Fora de escopo desta feature:
- Cadastro/cálculo de riscos e o registro de riscos em si (Módulo de Riscos) — aqui apenas as
  ações de tratamento e a referência ao risco.
- Constatações de auditoria interna (módulo próprio) — aqui apenas a ação derivada e a referência.
- Upload/versionamento de arquivos de evidência (Módulo de Evidências).
- Gestão de projeto avançada (diagrama de Gantt detalhado/WBS completa, orçamento, alocação de
  recursos) — pode ser uma evolução posterior; aqui basta fase/marcos/dependências/progresso.
- Sugestão de plano de ação por IA (Módulo de IA, posterior e opt-in por organização).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
