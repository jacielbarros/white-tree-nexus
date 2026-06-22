# Gap Analysis — Orientação de avaliação por item + Evidências por item

Duas features encadeadas para enriquecer a **matriz do Gap Analysis** (Módulo 2). Planejamento e
prompts `/speckit.specify` prontos. **Nada implementado ainda.**

- **Feature A — Orientação de avaliação por item** (objetivo / como avaliar / evidências esperadas
  por controle, + legenda global de status/prioridade).
- **Feature B — Evidências por item** (anexar arquivos auditáveis a cada item; primeira fatia do
  Módulo 5 de Evidências, ancorada na matriz do Gap).

Referência de domínio: planilha do curso Lead Implementer em
`material_de_contexto/02_Estudo de Caso Nexim/(02) GapAnalysis_ISO27001_2022_NeximTech.xlsx`
(TI Exames). Ela validou o conceito e refinou os requisitos abaixo.

---

## Parte 1 — Feature A: Orientação de avaliação por item

### Contexto
Hoje cada item da matriz tem só `ref_code` + `name`. As colunas operacionais (status, constatações,
ações, prioridade, responsável, prazo, evidência existente, justificativa de exclusão, observações)
**já existem** no `GapAssessmentItem`. Falta a **orientação de avaliação** (conteúdo de referência),
para reduzir subjetividade e guiar quem preenche — especialmente em autosserviço (sem consultor).

### O que a planilha do curso ensinou
- Tem uma coluna por item **"Resumo dos requisitos" / "Requisito do Controle (texto da norma)"** →
  valida o campo **objetivo**. **Mas usa o texto literal da norma — nós NÃO podemos** (direito
  autoral). Autoramos paráfrase original em PT-BR.
- A aba "Introdução" traz uma **legenda GLOBAL** de Status e de Prioridade (definições genéricas) →
  adotar como legenda única (não por item). Isso **substitui** a ideia de "critério de status por
  item" e evita ~400 micro-textos.
- Distinguir **evidência existente** (input da org, já temos `evidence_ref`) de **evidências
  esperadas** (orientação — campo novo).

### Modelo de campos
**Por item (orientação, no catálogo compartilhado, somente leitura, paráfrase original):**
| Campo | Conteúdo |
|-------|----------|
| `referencia` | rótulo factual: "ISO/IEC 27001:2022 — A.8.24" |
| `objetivo` | 1–2 frases: o que o controle/requisito busca |
| `como_avaliar` | lista de perguntas práticas |
| `evidencias_esperadas` | lista de exemplos de comprovação |
| `nota` | opcional (ex.: "ver ABNT ISO 31000") — padrão "NOTA" da planilha |

**Global (uma vez, não por item):** legenda de **Status** (Não atende / Atende Parcialmente / Atende
Totalmente / Não Aplicável) e de **Prioridade** (Crítica / Alta / Média / Baixa), com definições
próprias em PT-BR (inspiradas na aba Introdução).

### Arquitetura (para o /plan)
- Orientação é conteúdo de referência → reside no **catálogo compartilhado** (`gap_seed_item`),
  exibida na matriz via vínculo do `gap_catalog_item` da org → seed (sem duplicar ~500 blocos por
  tenant). **Precisa de migration** (novas colunas no seed) + seed aditivo/idempotente (nova versão
  `2022.2` ou colunas preenchidas idempotentemente).
- A legenda global pode ser conteúdo estático no front (ou config por org no futuro).
- **IP/legal (regra dura):** textos **originais**; proibido reproduzir texto normativo da ISO/IEC
  27001 ou guidance da 27002. Permitido: códigos e títulos curtos dos controles.
- **UI:** a orientação aparece no **painel lateral** da matriz (o painel de 348px já existe) numa
  seção "Orientação de avaliação" acima dos campos. **Deixar o painel preparado** para receber, em
  seguida, a seção de **Evidências** (Feature B).

### Edição administrativa da orientação (nível de plataforma)
A orientação é **conteúdo canônico da plataforma**, mas **editável** por um papel de permissão
elevada — não fica "congelada" no código.
- **Quem:** o **Super Admin da plataforma** (único papel cross-tenant; suas ações já são
  especialmente auditadas). Operação de **plataforma**, sem `X-Org-Context` → usa `require_super_admin`
  (não `require_permission`, que é escopado por org). Uma permissão dedicada de "editor de conteúdo"
  pode ser criada depois, se quiser separar do Super Admin.
- **O quê:** os campos de orientação dos `gap_seed_item` (`referencia`, `objetivo`, `como_avaliar`,
  `evidencias_esperadas`, `nota`) e, opcionalmente, os textos da legenda global de status/prioridade.
- **Como (recomendado):** edição **in-place** dos campos de orientação no seed + **trilha
  append-only** das alterações (quem/quando/antes→depois) + **audit log**. Evita re-versionar o seed
  inteiro a cada ajuste de texto. (Alternativa: gerar nova versão de seed por edição — mais pesado,
  reservado para mudanças estruturais do catálogo, não para tweaks de texto.)
- **Propagação:** como a orientação mora no seed e é exibida por vínculo (catálogo da org → seed),
  a edição **reflete imediatamente em todas as organizações**. É o efeito desejado de conteúdo de
  sistema. Para a org continua **somente leitura**.
- **Escopo:** edição é **só de plataforma**. **Override por organização fica deferido** (futuro: um
  admin da org sobrescrever a orientação só para a sua org — exigiria cópia/override por tenant).

### Sinergias
- `evidencias_esperadas` (esperado) ↔ **evidências anexadas** (Feature B): permite, no futuro,
  mostrar "X de Y evidências esperadas anexadas".
- `como_avaliar` (perguntas) → pode gerar um template do Motor de Workflow (003) para atribuir a
  avaliação ao dono do controle.

### Prompt `/speckit.specify` (pronto)
> **Orientação de avaliação por item na matriz do Gap Analysis ISO/IEC 27001:2022.** Hoje cada item
> (7 cláusulas 4–10 + 93 controles do Anexo A) tem só código e nome. Enriquecer cada item com
> orientação estruturada, em português, para reduzir subjetividade e guiar o avaliador:
> **referência** (rótulo factual, ex. "ISO/IEC 27001:2022 — A.8.24"), **objetivo** (o que o controle
> busca), **como avaliar** (lista de perguntas práticas), **evidências esperadas** (lista de
> comprovações). Além disso, exibir uma **legenda global** das escalas de **Status** (Não atende /
> Atende Parcialmente / Atende Totalmente / Não Aplicável) e de **Prioridade** (Crítica / Alta /
> Média / Baixa) com definições objetivas — uma única vez, não por item. Campo opcional **nota** por
> item para observações (ex.: referência cruzada a outra norma).
>
> **Requisitos observáveis:** para a organização, a orientação aparece ao selecionar o item na
> matriz (**somente leitura**), sem alterar o fluxo de avaliação; cobre todos os 93 controles e as 7
> cláusulas; o painel da matriz deve ser desenhado para acomodar, em feature seguinte, uma seção de
> evidências por item. A orientação é **conteúdo de plataforma editável por um administrador da
> plataforma** (papel de permissão elevada / Super Admin): há uma área administrativa para **editar**
> os textos de orientação (e a legenda global), cada edição gera **audit log** e fica numa **trilha
> append-only** (quem/quando/antes→depois); a alteração **reflete em todas as organizações**
> (conteúdo canônico). Organização **não** edita a orientação neste escopo.
>
> **Restrição legal (obrigatória):** todos os textos são **originais em português** — proibido
> reproduzir o texto normativo da ISO/IEC 27001 ou a guidance da ISO/IEC 27002 (direito autoral);
> permitido apenas códigos e títulos curtos dos controles.
>
> **Fora de escopo:** override/edição da orientação **por organização** (só plataforma neste escopo);
> geração automática de questionário; sugestão automática de status; anexação de evidências (é a
> feature seguinte) — apenas distinguir "evidência existente" (input da org, já existe) de
> "evidências esperadas" (orientação).
>
> **NÃO especificar stack.** No /plan: orientação no catálogo compartilhado (`gap_seed_item`),
> exibida via vínculo do catálogo da org ao seed (leitura) e editável por administrador da plataforma
> (`require_super_admin`, sem contexto de org) com trilha append-only + audit; prever migration de
> colunas (orientação + trilha) + seed aditivo/idempotente.

---

## Parte 2 — Feature B: Evidências por item (próxima)

Pela natureza **auditável** do produto (system of record de um SGSI), evidências precisam de cadeia
de custódia. Esta é a **primeira fatia do Módulo 5 (Gestão de Evidências)**, ancorada na matriz do
Gap. O `.env` já antecipa isso (`EVIDENCE_STORAGE_DIR`, `EVIDENCE_MAX_FILE_BYTES`,
`FIELD_ENCRYPTION_KEY`).

### Entidade de Evidência
Recomendação: **entidade genérica e reutilizável** (não exclusiva do Gap), para já servir o Módulo 5:
- `tenant_id` (obrigatório, + RLS) — isolamento inegociável.
- **Vínculo polimórfico**: `entity_type` (ex.: `gap_assessment_item`) + `entity_id`. (A matriz do Gap
  é o primeiro consumidor; depois SoA, Plano de Ação, etc.) — alternativa mais simples seria
  `gap_assessment_item_id` FK direto, mas o polimórfico evita retrabalho no Módulo 5.
- Metadados do arquivo: `filename`, `content_type`, `size_bytes`, **`sha256`** (integridade).
- Storage: caminho/chave no `EVIDENCE_STORAGE_DIR` (local) ou objeto/S3 em produção; nunca o binário
  no banco.
- Autoria: `uploaded_by`, `uploaded_at`.
- **Classificação/sensibilidade** (reusa `helpers/classification_access` do Módulo 1) + acesso por
  classificação.
- **Trilha append-only** (eventos: upload, download, exclusão lógica) — nunca apagar de fato
  (Princípio IV). Exclusão é **lógica** (soft-delete) com autor/data/motivo.
- **Audit log** em upload, download e exclusão lógica (Princípio III) — **nunca** logar conteúdo do
  arquivo, PII ou o binário; só metadados (id, nome, hash, ator).

### Integridade
- `sha256` calculado no upload (mesmo padrão do `signature_service` da Feature 003). Endpoint/serviço
  de **verificação** ("o arquivo bate com o hash?") para a UI mostrar status de integridade.

### RBAC
- Novas permissões sugeridas: `manage_evidence` (anexar/excluir) e `view_evidence` (listar/baixar) —
  ou reusar `manage_gap`/`view_gap` no MVP e generalizar no Módulo 5. Definir na spec.

### UI (no painel lateral da matriz)
- Seção **"Evidências"**: botão **Anexar evidência**, lista de arquivos (nome, tamanho, data, autor),
  **status de integridade/hash**, link **visualizar/baixar**, ação **excluir** (lógica).
- Indicador de **quantidade na linha** da matriz (ex.: "3 evidências").
- Cruzamento com a Feature A: "X de Y evidências esperadas anexadas".

### Isolamento e degradação
- Acesso cross-tenant ⇒ 404/403 + audit (fail-closed). Falha de storage no upload ⇒ erro claro
  (fail-closed: não registra evidência "fantasma" sem arquivo). Download de evidência de outro
  tenant ⇒ 404.

### Prompt `/speckit.specify` (pronto)
> **Evidências por item na matriz do Gap Analysis (cadeia de custódia auditável).** Permitir anexar
> arquivos de evidência a cada item da matriz do Gap Analysis (controles do Anexo A e cláusulas),
> com integridade e rastreabilidade — primeira fatia do módulo de Gestão de Evidências.
>
> **Entidade de Evidência** (genérica/reutilizável): pertence a uma organização (`tenant_id`,
> isolamento estrito); vincula-se a um item via referência polimórfica (`entity_type` +
> `entity_id`, começando por `gap_assessment_item`); guarda `filename`, `content_type`,
> `size_bytes`, **hash SHA-256**, caminho no storage, **quem anexou e quando**, e
> **classificação/sensibilidade**. Arquivo vai para storage de objetos/arquivos (não no banco), com
> limite de tamanho configurável.
>
> **Requisitos observáveis:** anexar, listar, visualizar/baixar e **excluir logicamente** (soft
> delete — nunca apagar de fato) evidências de um item; ver **status de integridade** (o arquivo
> confere com o hash registrado); ver a **quantidade de evidências** na linha da matriz e a lista no
> painel lateral; upload, download e exclusão geram **audit log** (sem expor conteúdo/PII); trilha
> **append-only** de eventos por evidência; acesso por classificação respeitado.
>
> **Segurança/compliance (obrigatório):** isolamento de tenant fail-closed (cross-tenant ⇒ 404/403 +
> audit); nunca registrar conteúdo do arquivo, PII ou binário em logs; integridade por SHA-256;
> exclusão é lógica e preserva a trilha (cadeia de custódia). Definir as permissões (anexar vs
> visualizar/baixar).
>
> **Fora de escopo:** tags de criticidade (crítica/informativa/pendente), busca/galeria global de
> evidências e timeline cross-módulo — ficam para o Módulo 5 completo. Aqui o foco é anexar/baixar/
> verificar/excluir por item do Gap.
>
> **NÃO especificar stack.** No /plan: reusar `tenant_scope`+RLS, RBAC, auditoria, classificação
> (Módulo 1), padrão de hash do `signature_service` (003) e `EVIDENCE_STORAGE_DIR`/
> `EVIDENCE_MAX_FILE_BYTES`/`FIELD_ENCRYPTION_KEY` do `.env`. Prever migration (tabela de evidências
> + trilha append-only com triggers, como nos módulos anteriores).

---

## Sequência recomendada
**Feature A (orientação) → Feature B (evidências).** A orientação prepara o painel lateral e o campo
`evidencias_esperadas`; a evidência preenche a contraparte (anexadas) e abre o Módulo 5. As duas são
aditivas e cada uma exige sua migration (diferente da Feature 006, que não teve).
