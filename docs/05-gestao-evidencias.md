# Prompt para `/speckit.specify` — Módulo 6: Gestão de Evidências

Pré-requisitos: Fundação + módulos do MVP anteriores especificados.
Fecha o ciclo do MVP: dá substância real aos "vínculos de evidência" citados nos demais
módulos. Agnóstico de stack.

---

```
Módulo de Gestão de Evidências da plataforma SaaS multi-tenant de Gestão de SGSI
ISO/IEC 27001:2022. É o repositório auditável de evidências de conformidade, com cadeia
de custódia: versionamento, ciclo de aprovação e atribuição de autoria de ponta a ponta.

Esta feature roda sobre a fundação multi-tenant e os módulos já existentes. Todo dado
respeita o isolamento de tenant e a integridade/cadeia de custódia exigida pela
constitution.

Escopo desta feature:
- Upload de arquivos de evidência, com metadados (título, descrição, data).
- Associação de uma evidência a um ou mais itens: controles (gap analysis / SoA),
  riscos, auditorias e ações do plano de ação.
- Versionamento: cada novo upload sobre uma evidência gera nova versão preservando as
  anteriores; nenhuma versão é apagada ou sobrescrita.
- Ciclo de aprovação: estados de envio, aprovação e rejeição, com comentários e
  identificação de quem enviou, aprovou ou rejeitou, e quando.
- Histórico de alterações imutável (append-only) por evidência.
- Controle de acesso por papel: quem pode enviar, ver, aprovar/rejeitar e baixar.
- Tratamento gracioso de falha do storage (não corromper estado; registrar e informar
  sem expor detalhes internos).

Requisitos observáveis (critérios de aceitação):
- Evidências de uma organização só são acessíveis por usuários dela com permissão;
  acesso cross-tenant é negado e auditado.
- Cada versão preserva autor, data e ação; nenhuma versão ou registro de histórico é
  editável ou apagável.
- O ciclo aprovação/rejeição é rastreável de ponta a ponta (quem, quando, decisão,
  comentário).
- Conteúdo confidencial de evidência nunca aparece em logs, auditoria ou mensagens de erro.
- Toda operação sensível (upload, vínculo, aprovação, rejeição, download) gera registro
  de auditoria.

Fora de escopo desta feature:
- Análise automática do conteúdo das evidências por IA (módulo de IA, posterior e opt-in).
- Limites de cota/armazenamento por plano além do necessário para validação básica de
  tamanho/tipo de arquivo.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
