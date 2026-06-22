# Phase 0 — Research: Orientação de Avaliação por Item

Sem `NEEDS CLARIFICATION` pendentes (spec + `/speckit-clarify` resolveram). Decisões técnicas de
**como** implementar, ancoradas no código existente do Módulo 2 (Gap Analysis).

---

## D1 — Onde mora a orientação

**Decision**: nos itens do **catálogo-base compartilhado** (`gap_seed_item`). `objetivo` **já existe**
lá (campo `objective`, autorado no `data/iso27001_seed.py`). Adicionar **`referencia`** (String),
**`como_avaliar`** (JSON), **`evidencias_esperadas`** (JSON), **`nota`** (Text). A matriz da org lê a
orientação por **join** `gap_catalog_item.seed_item_id → gap_seed_item` (FK já existente).

**Rationale**: conteúdo canônico único; 1 edição reflete em todas as orgs (FR-005/SC-003); sem
duplicar ~100×N blocos. Reusa o vínculo `seed_item_id` já populado em `adopt_seed`.

**Alternatives**: copiar orientação para `gap_catalog_item` (rejeitado — edição não propagaria, exige
re-sync); tabela separada de orientação (rejeitado — orientação 1:1 com o item do seed cabe como
colunas do próprio item).

---

## D2 — Forma de `como_avaliar` / `evidencias_esperadas`

**Decision**: **listas de strings** (JSON array de itens curtos). Renderizadas como tópicos.

**Rationale**: clarificação Q2; simples de editar e de cruzar com "evidências esperadas × anexadas"
(Feature B). SQLAlchemy `JSON` (igual ao `fields_snapshot`/`answers` já usados no projeto).

**Alternatives**: texto único (pior para cruzar contagem); objetos ricos por item (exagero p/ escopo).

---

## D3 — Legenda global (Status + Prioridade)

**Decision**: tabela de plataforma **`gap_legend_entry`** (sem `tenant_id`): `kind`
(`status`|`priority`), `code` (ex.: `meets`/`partial`/`not_meet`/`not_applicable` e
`critical`/`high`/`medium`/`low`), `label`, `definition`, `order`. Editável pelo Super Admin, com
audit + trilha.

**Rationale**: como é **editável e auditada**, uma tabela é melhor que texto estático. Definições
iniciais (PT-BR próprio) inspiradas na aba "Introdução" da planilha do curso.

**Alternatives**: texto fixo no front (rejeitado — não editável/auditável); config em `.env`
(rejeitado — conteúdo, não parâmetro operacional).

---

## D4 — Trilha de edição (append-only)

**Decision**: tabela de plataforma **`gap_guidance_event`** (sem `tenant_id`): `target_type`
(`seed_item`|`legend`), `target_id`, `field`, `old_value`, `new_value`, `actor_id`, `created_at`.
**Append-only** via triggers (SQLite `CREATE TRIGGER IF NOT EXISTS`; PG `CREATE OR REPLACE FUNCTION`
+ `DROP TRIGGER IF EXISTS` + `CREATE TRIGGER`), mesmo padrão de `document_versions`/
`gap_assessment_item_event`.

**Rationale**: rastreabilidade (Princípio IV) sem transformar a orientação em documento controlado
versionado. Valor corrente é mutável in-place; o histórico vive na trilha.

**Alternatives**: versionar o seed por edição (rejeitado — pesado p/ tweaks de texto); só audit_log
(rejeitado — não guarda antes→depois de forma consultável na UI).

---

## D5 — RBAC (leitura × edição)

**Decision**: **leitura** via `require_permission("view_gap")` (contexto de org — quem vê a matriz).
**Edição** via `require_super_admin` (operação de plataforma, sem `X-Org-Context`). **Sem permissão
nova** no MVP (Super Admin tem bypass, mas é auditado).

**Rationale**: alinha à spec; o Super Admin é o único papel cross-tenant e o conteúdo é de plataforma.

**Alternatives**: permissão dedicada de "curadoria de conteúdo" separada do Super Admin — **deferida**
(anotada como evolução).

---

## D6 — Estratégia de seed do conteúdo

**Decision**: estender `data/iso27001_seed.py` (`build_seed_items`) com os campos de orientação dos
**100 itens** (PT-BR original) + seed da legenda. `load_seed` (e o passo de dados da migration)
**preenche os campos de orientação SOMENTE quando vazios** — **nunca sobrescreve** valor não-vazio
(preserva edições do admin). Mantém a versão de seed **2022.1** (sem bump).

**Rationale**: `load_seed` roda a cada startup; sobrescrever reverteria edições do admin. "Preenche
lacuna, edição vence" é idempotente e respeita FR-007/SC-003/SC-004. Orgs que já adotaram veem a
orientação imediatamente via join (sem readoção).

**Alternatives**: nova versão `2022.2` (rejeitado — semântica de re-adoção desnecessária p/ texto);
sobrescrever sempre (rejeitado — apaga curadoria do admin).

---

## D7 — Endpoint de leitura

**Decision**: `GET /gap/guidance` (gated `view_gap`) devolve, em **uma** resposta: a lista de
orientações dos itens do seed corrente (`seed_item_id`, `ref_code`, `referencia`, `objetivo`,
`como_avaliar`, `evidencias_esperadas`, `nota`) + a `legend` (status[] e priority[]). O frontend
mapeia por `ref_code` e exibe no painel ao selecionar o item.

**Rationale**: 1 chamada por sessão de matriz; evita N requisições por item; conteúdo é o mesmo para
todos (cacheável no cliente).

**Alternatives**: orientação embutida na resposta de `GET /gap/assessment` (rejeitado — acopla e
infla a resposta da matriz); 1 fetch por item selecionado (rejeitado — N chamadas).

---

## D8 — Endpoints de edição (admin)

**Decision**: `PUT /gap/guidance/items/{seed_item_id}` (campos de orientação) e
`PUT /gap/guidance/legend/{entry_id}` (label/definition), ambos `require_super_admin`. Cada gravação:
compara antes→depois por campo, grava `gap_guidance_event` para cada mudança e chama
`AuditService.log_from_request`. Endpoint de histórico opcional `GET /gap/guidance/events` (admin).

**Rationale**: edição é operação de plataforma; trilha + audit por campo dão rastreabilidade fina.

---

## D9 — Tabelas platform-level sem `tenant_id` (RLS)

**Decision**: `gap_seed_item` (já existe), `gap_legend_entry` e `gap_guidance_event` **não** têm
`tenant_id` e **não** recebem RLS — são conteúdo de plataforma compartilhado, como o catálogo-base do
Gap (Feature 004). O acesso é controlado por papel (view_gap p/ ler; Super Admin p/ editar), não por
tenant.

**Rationale**: isolamento de tenant se aplica a **dado de org**; orientação não é dado de org. Mesma
exceção já documentada/aprovada na Feature 004 (Complexity Tracking).

---

## D10 — Frontend

**Decision**: (a) na matriz (`gap-analysis.ts`), seção **"Orientação de avaliação"** (somente leitura)
no painel lateral, acima dos campos de avaliação, alimentada por `GET /gap/guidance` (mapa por
`ref_code`), com espaço reservado para a futura seção de Evidências (FR-010); (b) **legenda** de
status/prioridade acessível na tela do Gap; (c) **área administrativa** `pages/gap-guidance-admin/`
(rota guardada para **Super Admin**) para editar orientação + legenda.

**Rationale**: reusa o painel de 348px já existente; mantém o fluxo de avaliação intacto; separa a
curadoria (admin) da leitura (org).

**Alternatives**: edição inline na matriz só p/ Super Admin (rejeitado p/ MVP — mistura curadoria com
avaliação; área dedicada é mais clara).

---

## D11 — Fonte do `objetivo` exibido

**Decision**: exibir **todos** os campos de orientação (incl. `objetivo`) a partir do **seed** (via
join), não da cópia `gap_catalog_item.objective`. Assim, edições do admin ao `objetivo` propagam. A
coluna `objective` do catálogo permanece (não é exibida na matriz hoje) — tratada como legado.

**Rationale**: consistência — toda a orientação vem de uma fonte (o seed), garantindo propagação.
