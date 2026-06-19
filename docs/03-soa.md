# Prompt para `/speckit.specify` — Módulo 3: Statement of Applicability (SoA)

Pré-requisitos: Fundação multi-tenant, Módulo 1 (Diagnóstico/Contexto) e Módulo 2 (Gap Analysis)
especificados. Agnóstico de stack.

> **Enriquecido a partir do estudo de caso real (Nexim Tech)** — ver
> `material_de_contexto/02_Estudo de Caso Nexim/Documentos Controles Anexo A/(1) SOA e Documentos
> Associados.xlsx` e `(13) Avaliacao de Riscos + SOA + Ativos.xlsx` (aba SOA).
> Reutiliza o padrão transversal **"Documento Controlado SGSI (7.5)"** — definição canônica em
> [iso27001-documento-controlado.md](iso27001-documento-controlado.md).

---

```
Módulo de Statement of Applicability (Declaração de Aplicabilidade — SoA) da plataforma SaaS
multi-tenant de Gestão de SGSI ISO/IEC 27001:2022. Produz o documento de SoA exigido pela cláusula
6.1.3 d) da norma: para cada um dos 93 controles do Anexo A (ISO/IEC 27002:2022), a decisão de
aplicabilidade, a justificativa de inclusão/exclusão, os riscos tratados e o status de
implementação — consolidando os dados do Gap Analysis num documento controlado e exportável.

Esta feature roda sobre a fundação multi-tenant e os Módulos 1 (Diagnóstico) e 2 (Gap Analysis) já
existentes. Todo dado pertence a uma organização e respeita o isolamento de tenant; acesso
cross-tenant é negado (404/403 sem revelar existência) e auditado.

== Conteúdo da SoA (por controle do Anexo A) ==
A SoA cobre os 93 controles do Anexo A em 4 temas (Organizacional A.5, Pessoas A.6, Físico A.7,
Tecnológico A.8). Para cada controle, registrar:
- ID do controle (ex.: A.5.1), tema e nome do controle.
- Aplicável (Sim/Não).
- Justificativa de inclusão — com a(s) razão(ões) que a norma espera, tipadas: resultado do
  tratamento de riscos | requisito legal/regulatório | requisito contratual | melhor prática /
  requisito de negócio. (Texto livre complementar permitido.)
- Justificativa de exclusão — obrigatória quando "Não aplicável" (pré-carregada do Gap Analysis).
- Riscos tratados — referência aos riscos do registro de riscos que este controle mitiga (ex.:
  R01, R02). Vínculo efetivo depende do Módulo de Riscos; nesta fase, referência rastreável.
- Status de implementação: Implementado | Em andamento | Planejado | Não iniciado | Não aplicável.
- Responsável.
- Prazo de conclusão.
- Evidências objetivas esperadas (descrição textual do que comprova o controle) e referências aos
  documentos/evidências associados (ex.: POL-SI-001, MAN-SGSI-001, PR-IAM-001). O arquivo real e
  seu versionamento vêm do Módulo de Evidências; aqui a referência é rastreável.
- Observações.

== Origem dos dados e edição ==
- A SoA é pré-preenchida a partir do Gap Analysis (Módulo 2): aplicabilidade, justificativa de
  exclusão, status, responsável e prazo vêm de lá.
- Todos os campos são editáveis manualmente na SoA, de forma independente do Gap Analysis. Quando
  um valor da SoA diverge do Gap Analysis de origem, a divergência é sinalizada (sem sobrescrever
  silenciosamente nenhum dos dois).

== Documento controlado e exportação ==
- A SoA é um documento controlado (reusa o padrão "Documento Controlado SGSI 7.5"): identificador,
  versão, status (rascunho → em revisão → aprovado/em vigor → obsoleto), classificação, datas
  (emissão e próxima análise crítica) e cadeia elaborado/revisado/aprovado.
- Versionamento append-only: cada emissão/revisão é uma versão imutável (autor, data, natureza da
  alteração, aprovador); versões anteriores permanecem consultáveis e nunca são apagadas.
- Exportação da SoA em formato de documento (ex.: PDF) refletindo exatamente uma versão específica
  selecionada — é o artefato que o auditor de certificação solicita.

== Rastreabilidade ==
- Cada controle da SoA é rastreável até o item correspondente do Gap Analysis (Módulo 2).
- O campo "Riscos tratados" liga a SoA ao registro de riscos (Módulo de Riscos).
- As "evidências esperadas/referências" ligam a SoA aos artefatos do Módulo de Evidências.

Requisitos observáveis (critérios de aceitação):
- A SoA de uma organização só é visível/editável/exportável por usuários dela com a permissão
  adequada; acesso cross-tenant é negado (404/403) e auditado.
- A SoA cobre os 93 controles do Anexo A; marcar um controle como "Não aplicável" exige
  justificativa de exclusão.
- A justificativa de inclusão registra ao menos uma razão tipada (risco/legal/contratual/melhor
  prática) para controles aplicáveis.
- Emitir uma nova versão nunca altera nem apaga versões anteriores (append-only).
- O documento exportado corresponde exatamente à versão selecionada.
- Divergências entre SoA e Gap Analysis de origem são sinalizadas, não silenciosas.
- Toda emissão, edição, mudança de status e exportação gera registro de auditoria.

Fora de escopo desta feature:
- Cadastro/cálculo de riscos e plano de tratamento de riscos (Módulo de Riscos) — a SoA apenas
  referencia os riscos tratados.
- Upload e versionamento de arquivos de evidência (Módulo de Evidências) — a SoA apenas referencia.
- Geração de rascunho de SoA por IA (Módulo de IA, posterior e opt-in por organização).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
