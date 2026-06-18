# Prompt para `/speckit.specify` — Módulo 5: Plano de Ação

Pré-requisitos: Fundação, Diagnóstico, Gap Analysis e SoA especificados.
Agnóstico de stack.

---

```
Módulo de Plano de Ação da plataforma SaaS multi-tenant de Gestão de SGSI ISO/IEC
27001:2022. Centraliza as tarefas de remediação e melhoria do SGSI, originadas de
lacunas do gap analysis, riscos, constatações de auditoria ou controles específicos.

Esta feature roda sobre a fundação multi-tenant e os módulos já existentes. Todo dado
respeita o isolamento de tenant.

Escopo desta feature:
- Cadastro e gestão de ações/tarefas com:
  - Título e descrição.
  - Origem: gap analysis, risco, auditoria ou controle — com referência ao item de
    origem quando aplicável.
  - Responsável.
  - Prazo.
  - Prioridade.
  - Status (ex.: aberta, em andamento, concluída, cancelada).
  - Evidências vinculadas (referência; o arquivo real vem do módulo de Evidências).
  - Comentários.
  - Histórico de alterações (append-only).
- Listagem e filtros das ações (por responsável, status, prioridade, origem, prazo;
  destaque para ações atrasadas).
- Notificações e lembretes automáticos por e-mail (ex.: atribuição, proximidade do
  prazo, atraso), tratando falha de envio de forma graciosa (não bloquear a operação).

Requisitos observáveis (critérios de aceitação):
- As ações de uma organização só são visíveis/editáveis por usuários dela com permissão;
  acesso cross-tenant é negado e auditado.
- Mudanças de status, responsável e prazo ficam registradas no histórico imutável da ação.
- Uma ação atrasada é identificável de forma consistente (prazo vencido e não concluída).
- Lembretes são disparados conforme regras configuráveis; falha de e-mail é registrada
  como aviso e não impede o uso do módulo.
- Toda criação/alteração relevante gera registro de auditoria.

Fora de escopo desta feature:
- Upload/versionamento de arquivos de evidência (módulo de Evidências).
- Sugestão de plano de ação por IA (módulo de IA, posterior e opt-in).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
