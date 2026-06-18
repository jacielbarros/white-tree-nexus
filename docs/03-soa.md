# Prompt para `/speckit.specify` — Módulo 4: Statement of Applicability (SoA)

Pré-requisitos: Fundação, Diagnóstico e Gap Analysis especificados.
Agnóstico de stack.

---

```
Módulo de Statement of Applicability (Declaração de Aplicabilidade — SoA) da plataforma
SaaS multi-tenant de Gestão de SGSI ISO/IEC 27001:2022. Gera o documento de SoA exigido
pela norma a partir do gap analysis, consolidando a decisão de aplicabilidade e o status
de cada controle do Anexo A.

Esta feature roda sobre a fundação multi-tenant e os módulos de Diagnóstico e Gap
Analysis já existentes. Todo dado respeita o isolamento de tenant.

Escopo desta feature:
- Geração da SoA da organização a partir dos controles do Anexo A e dos dados do gap
  analysis, exibindo por controle:
  - Controle (identificador, título, tema).
  - Aplicabilidade (aplicável / não aplicável).
  - Justificativa de inclusão ou exclusão.
  - Status de implementação.
  - Evidências vinculadas (referência; o arquivo real vem do módulo de Evidências).
  - Riscos relacionados (referência; o vínculo efetivo depende do módulo de Riscos).
  - Responsável.
  - Observações.
- Edição manual dos campos da SoA, independentemente do gap analysis, com indicação de
  quando um valor diverge do gap analysis de origem.
- Versionamento da SoA: cada emissão/revisão é uma versão imutável, com autor, data e
  identificação da versão; versões anteriores permanecem consultáveis.
- Exportação da SoA em formato de documento (ex.: PDF) refletindo uma versão específica.

Requisitos observáveis (critérios de aceitação):
- A SoA de uma organização só é visível/editável/exportável por usuários dela com
  permissão; acesso cross-tenant é negado e auditado.
- Emitir uma nova versão nunca altera nem apaga versões anteriores (append-only).
- O documento exportado corresponde exatamente à versão selecionada.
- Toda emissão, edição e exportação gera registro de auditoria.

Fora de escopo desta feature:
- Upload/versionamento de arquivos de evidência (módulo de Evidências).
- Cálculo e cadastro de riscos (módulo de Riscos).
- Geração de rascunho de SoA por IA (módulo de IA, posterior e opt-in).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
