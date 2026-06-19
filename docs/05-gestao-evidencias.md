# Prompt para `/speckit.specify` — Módulo 5: Gestão de Evidências (Informação Documentada)

Pré-requisitos: Fundação multi-tenant + Módulos 1–4 do MVP especificados.
Fecha o ciclo do MVP: dá substância real aos "vínculos de evidência" e aos "documentos
controlados" citados nos demais módulos. Agnóstico de stack.

> **Enriquecido a partir do estudo de caso real (Nexim Tech)** — ver
> `material_de_contexto/02_Estudo de Caso Nexim/(21)Controle_Documentos.docx` (PROC-DOC-001) e
> `material_de_contexto/04_Templates para Alunos/Mod 5 Procedimento de controle de documentos e
> registros.docx`. Este módulo **realiza** o padrão transversal **"Documento Controlado SGSI (7.5)"**
> (definição em [iso27001-documento-controlado.md](iso27001-documento-controlado.md)) usado pelos
> Módulos 1–4 — versionamento, aprovação, classificação e retenção.

---

```
Módulo de Gestão de Evidências e Informação Documentada da plataforma SaaS multi-tenant de Gestão
de SGSI ISO/IEC 27001:2022. É o repositório auditável central da "informação documentada"
(cláusula 7.5): tanto os REGISTROS/EVIDÊNCIAS evidenciais (uploads que comprovam controles) quanto
os DOCUMENTOS prescritivos controlados (políticas, procedimentos, manuais e os artefatos dos
Módulos 1–4), com cadeia de custódia: identificação, classificação, versionamento, ciclo de
aprovação, retenção e descarte seguro — de ponta a ponta.

Esta feature roda sobre a fundação multi-tenant e os módulos já existentes. Todo dado pertence a
uma organização e respeita o isolamento de tenant e a integridade/cadeia de custódia exigida pela
constitution; acesso cross-tenant é negado (404/403 sem revelar existência) e auditado.

== Item de informação documentada ==
Upload e registro de itens, com metadados:
- Tipo: Documento (prescritivo — política/procedimento/manual/norma) ou Registro (evidencial —
  comprova a execução de um controle).
- Identificador estável (padrão configurável por organização, ex.: POL-SI-001, PROC-DOC-001,
  SGSI-DOC-002), título, descrição e data.
- Classificação da informação: Público | Uso Interno | Confidencial | Restrito.
- Dono/responsável e referências normativas/documentos relacionados.
- Arquivo(s) anexado(s), com validação básica de tipo e tamanho.

== Vínculos (rastreabilidade) ==
- Associação de um item a um ou mais elementos do SGSI: controles (Gap Analysis / SoA), riscos,
  constatações de auditoria, ações do Plano de Ação e requisitos de cláusula.
- As "evidências objetivas esperadas" referenciadas no SoA e os artefatos controlados dos
  Módulos 1–4 resolvem-se aqui (o vínculo textual vira vínculo real ao item versionado).

== Versionamento e ciclo de vida (7.5.3) ==
- Versionamento append-only: cada novo upload/revisão gera nova versão preservando as anteriores;
  nenhuma versão é apagada ou sobrescrita. Cada versão preserva autor, data e ação.
- Ciclo de vida do item: rascunho/capturado → em revisão → aprovado/em vigor → (revisão periódica)
  → obsoleto/substituído → retido → descartado. Cada transição é auditada; aprovar/publicar exige
  o papel autorizado.
- Ciclo de aprovação: estados de envio, aprovação e rejeição, com comentário e identificação de
  quem enviou/aprovou/rejeitou e quando (cadeia de custódia rastreável de ponta a ponta).
- Data de próxima análise crítica (revisão periódica) por item, com destaque para itens vencidos.

== Retenção e descarte ==
- Período de retenção configurável por item/tipo (considerando obrigações legais, ex.: LGPD).
- Descarte seguro/arquivamento controlado: o descarte é uma operação auditada e o registro do
  descarte (quem, quando, o quê) é preservado de forma imutável, mesmo quando o arquivo é removido.

== Controle de acesso e distribuição ==
- Controle por papel E por classificação: quem pode enviar, ver, aprovar/rejeitar, baixar e
  descartar, respeitando o nível de classificação do item.
- Histórico de alterações imutável (append-only) por item.
- Tratamento gracioso de falha do storage (fail-soft): não corromper o estado; registrar e
  informar sem expor detalhes internos.

Requisitos observáveis (critérios de aceitação):
- Itens de uma organização só são acessíveis por usuários dela com a permissão e o nível de
  classificação adequados; acesso cross-tenant é negado (404/403) e auditado.
- Cada versão preserva autor, data e ação; nenhuma versão nem registro de histórico é editável ou
  apagável (append-only), inclusive o registro de descarte.
- O ciclo de aprovação/rejeição é rastreável de ponta a ponta (quem, quando, decisão, comentário).
- O vínculo entre um item e os elementos do SGSI (controle/risco/auditoria/ação) é navegável nos
  dois sentidos.
- Conteúdo confidencial de evidência nunca aparece em logs, auditoria, telemetria ou mensagens de
  erro.
- Itens com revisão periódica vencida e com retenção expirada são identificáveis de forma
  consistente.
- Toda operação sensível (upload, vínculo, aprovação, rejeição, download, descarte) gera registro
  de auditoria.

Fora de escopo desta feature:
- Análise automática do conteúdo das evidências por IA (Módulo de IA, posterior e opt-in por
  organização).
- Sistema de gestão documental (DMS) completo: controle de documentos físicos, fluxos de
  assinatura externa, automação avançada de retenção — pode ser evolução posterior.
- Cotas/limites de armazenamento por plano além da validação básica de tamanho/tipo de arquivo.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
