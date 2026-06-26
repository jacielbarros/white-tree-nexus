# Research — Gestão de Ativos / Processos / Escopo (Feature 011)

Sem marcadores `NEEDS CLARIFICATION` pendentes (a sessão `/speckit-clarify` de 2026-06-26 resolveu os
pontos de produto). Este documento consolida as **decisões técnicas** de planejamento, ancoradas nos
padrões já existentes (Gap Analysis 004, Evidências 008, SoA 005).

---

## D1 — Domínio novo, tenant-scoped (não reaproveitar `gap_*`/`soa_*`)

- **Decisão**: criar um domínio próprio `asset_*` com 4 tabelas (`asset_items`, `asset_relationships`,
  `asset_gap_links`, `asset_item_events`), todas com `tenant_id` + RLS.
- **Rationale**: ativos/processos/escopo são uma entidade de domínio distinta, base dos próximos
  módulos. Reaproveitar o catálogo do Gap acoplaria conceitos diferentes. O padrão "tabela própria +
  `tenant_id` + RLS + trilha append-only" já é o do projeto.
- **Alternativas**: (a) estender `gap_catalog_item` — rejeitada (mistura avaliação de norma com
  inventário); (b) usar o SoA — rejeitada explicitamente na spec (SoA é Pré-SoA/Catálogo de Controles).

## D2 — Classificação CIA e criticidade (enum novo de 4 níveis)

- **Decisão**: novo enum `CiaLevel = {baixa, media, alta, critica}` (ordenado). C/I/A e a criticidade
  geral usam esse enum. Criticidade = `max(C, I, A)` quando não houver ajuste manual; flag
  `criticality_is_manual` marca override (com autor/data no histórico). Ordem para o `max`:
  `baixa(0) < media(1) < alta(2) < critica(3)`.
- **Rationale**: o enum `Level` existente é de 3 níveis (`alto/medio/baixo`) e semântica de
  impacto/contexto — não serve para CIA de 4 níveis. Criar enum dedicado evita acoplamento.
- **Alternativas**: reusar `Level` — rejeitada (3 níveis, falta "crítica"); inteiro 1–4 — rejeitada
  (enum é mais legível e consistente com o projeto).
- **Divergência calculada vs. ajustada** (edge case): no read, o serviço compara a criticidade
  armazenada com `max(C,I,A)` atual e expõe um flag `criticality_divergent` quando `is_manual` e os
  valores diferem (FR-007). Não muta o dado automaticamente.

## D3 — Código interno: prefixo por tipo + sequência por tipo, imutável

- **Decisão**: `code = f"{PREFIX[type]}-{seq:04d}"`, sequência **por tipo dentro da organização**,
  único no tenant (UniqueConstraint `(tenant_id, code)`), **imutável** após criação. Mapa de prefixos
  em `settings.ASSET_CODE_PREFIXES` (ex.: ATV, SIS, BD, PROC, INFRA, SVC, FORN, DOC, PESS, AMB, OUTRO).
- **Rationale**: confirma a clarificação. Legível para consultores/PMEs e estável (não muda se o tipo
  do item mudar depois — o código é identidade).
- **Geração atômica**: calcular o próximo `seq` como `max(seq existente do tipo no tenant)+1` dentro
  da transação de criação; a `UniqueConstraint (tenant_id, code)` + retry em `IntegrityError` cobre
  corrida concorrente (o handler global de `IntegrityError` já existe em `main.py`). Para o MVP
  (baixa concorrência por org) isso basta; não há sequência dedicada no banco.
- **Alternativas**: sequência global por org — rejeitada (menos informativa); UUID/opaco — rejeitada
  (pouco amigável); sequência PG nativa — rejeitada (excesso para a escala do MVP e complica RLS).

## D4 — Situação de escopo vs. status do registro vs. situação de revisão (3 conceitos distintos)

- **Decisão**: três campos/conceitos independentes, todos explícitos:
  - `scope_status` (`AssetScopeStatus = in_scope | out_of_scope | under_analysis`) — manual.
  - `record_status` (`AssetRecordStatus = active | in_review | archived`) — manual; `archived` é o
    arquivamento lógico.
  - `review_status` (`AssetReviewStatus = up_to_date | due_soon | overdue | undefined`) — **derivado**
    no read a partir de `next_review_at` + `ASSET_REVIEW_DUE_SOON_DAYS` (default 30). Não é coluna.
- **Rationale**: o prompt lista os três separadamente; derivar a situação de revisão (FR-026) evita
  job de atualização e mantém consistência. Manter `record_status` e `scope_status` separados evita
  confundir "em revisão" (estado do registro) com "revisão vencida" (situação temporal).
- **Validações condicionais** (no serviço, no create/update):
  - `in_scope` ⇒ `responsible_user_id` **e** C, I, A obrigatórios (FR-010).
  - `out_of_scope` ⇒ `scope_justification` obrigatória (FR-009).
  - `under_analysis` ⇒ não bloqueia; resposta marca `pending_fields` (responsável/CIA ausentes) (FR-011).

## D5 — Relacionamentos: tabela flexível direcional (mesmo tenant)

- **Decisão**: `asset_relationships(source_item_id, relationship_type, target_item_id, description)`,
  enum `AssetRelationshipType` com os 11 tipos da spec. Regras: `source != target`; ambos do mesmo
  tenant (checado na app + garantido por RLS); `UniqueConstraint(tenant_id, source_item_id,
  relationship_type, target_item_id)` para evitar duplicata. Exibição: saída (source) + entrada
  (target) na tela de detalhe de cada item.
- **Rationale**: estrutura genérica pedida na spec; cobre o grafo de dependências sem N tabelas.
- **Campos "X relacionado" do cadastro** (sistema/processo/fornecedor relacionados): modelados como
  **FKs de conveniência opcionais** no próprio item (`related_system_id`, `related_process_id`,
  `related_supplier_id` → `asset_items.id`, mesmo tenant), exibidos no cadastro; o grafo rico fica na
  tabela de relacionamentos. Trade-off documentado: dois caminhos para "relacionar", mas o cadastro
  fica fiel ao prompt e o grafo continua flexível. (Alternativa de modelar tudo só via tabela de
  relacionamentos foi considerada; mantida a conveniência por fidelidade ao formulário pedido.)

## D6 — Vínculo a Gap: catálogo da própria org, sem alterar o módulo Gap

- **Decisão**: `asset_gap_links(item_id, gap_catalog_item_id, note)` referenciando `gap_catalog_item`
  (cópia editável por tenant). `UniqueConstraint(tenant_id, item_id, gap_catalog_item_id)`. A tela do
  Gap **não** é alterada (exibição reversa deferida — clarificação). O vínculo é criado/listado/
  removido pela tela do item.
- **Rationale**: confirma a clarificação; mantém escopo limpo e o módulo Gap intacto.
- **Robustez**: se o `gap_catalog_item` vinculado for marcado `is_discontinued`, o vínculo permanece e
  a UI indica indisponibilidade (edge case da spec) — não há cascade delete.

## D7 — Histórico append-only por item (artefato versionável — SEC-005)

- **Decisão**: `asset_item_events` append-only (triggers SQLite `RAISE(ABORT)` + PG `BEFORE UPDATE OR
  DELETE` function/trigger), padrão idêntico a `gap_evidence_event`. Campos: `event_type`,
  `field_name`, `old_value`, `new_value`, `reason`, `actor_id`, `occurred_at`, `details(JSON)`.
- **Rationale**: a constituição (Princípio IV) e SEC-005 exigem trilha imutável com autor/data/ação;
  o histórico do item é o artefato versionável desta feature (não há "documento controlado" aqui).
- **Justificativa obrigatória** (FR-024): `event_type ∈ {SCOPE_EXCLUSION, CRITICALITY_CHANGE,
  ARCHIVE}` exige `reason` não-vazio; o serviço rejeita a operação sem justificativa.
- **Diffing**: o `asset_service` compara o estado anterior e o novo e emite um evento por campo
  relevante alterado (escopo/criticidade/responsável) + eventos de ciclo (CREATE/ARCHIVE/REL/GAP).

## D8 — Dados sensíveis: sem cifragem de campo (clarificação)

- **Decisão**: armazenar os campos em texto; proteção por RBAC + isolamento de tenant + regra "sem PII
  bruta nas observações". Sem uso de `FIELD_ENCRYPTION_KEY` nesta feature.
- **Rationale**: o módulo guarda **indicadores** (`has_personal_data`/`has_sensitive_data`) e notas de
  compliance — não o dado pessoal. Cifrar quebraria a busca textual (FR-030) sobre observações.
  Coerente com o Princípio V ("cifrado **quando aplicável**"). Reavaliável em feature futura.
- **Alternativas**: cifrar observações com Fernet — rejeitada no MVP (custo/complexidade e perda de
  busca, sem ganho real porque não há PII bruta).

## D9 — Métricas/dashboard: serviço de agregação + endpoints de leitura

- **Decisão**: `asset_metrics_service` calcula os cards de resumo (FR-028) e as distribuições do
  dashboard (FR-031) com queries agregadas tenant-scoped. Dois endpoints de leitura
  (`GET /assets/summary`, `GET /assets/dashboard`) com `view_asset`.
- **Rationale**: espelha `gap_metrics_service`; mantém a lógica de agregação fora do router e
  testável isoladamente. Leitura simples não gera audit (consistente com os demais módulos).

## D10 — "Criar item a partir do contexto" (FR-019): backend fornece fontes, frontend pré-preenche

- **Decisão**: `GET /assets/context-sources` retorna elementos compatíveis da Análise de Contexto da
  org (partes interessadas, issues/contexto interno-externo, escopo preliminar) como sugestões; o
  frontend pré-preenche o formulário de novo item e o usuário completa/salva (POST normal). Vínculo de
  origem opcional gravado em `context_origin_type`/`context_origin_id` no item.
- **Rationale**: evita importação automática complexa (fora de escopo) mas entrega o acelerador;
  reutiliza modelos de contexto já existentes (`stakeholder_model`, `context_analysis_model`,
  `scope_model`) **somente leitura**, sem alterá-los.
- **Alternativas**: importação em lote — rejeitada (fora de escopo do MVP); cópia automática — rejeitada
  (risco de duplicidade e de itens sem revisão humana).

## D11 — Migration idempotente encadeada no head atual

- **Decisão**: `b1c2d3e4f015_asset_process_scope_module.py`, `down_revision="a6b7c8d9e014"` (head
  atual = print_template_variable_catalog). Idempotente: `_table_exists`/`_index_exists`/`_fk_exists`,
  triggers com `CREATE OR REPLACE`/`DROP ... IF EXISTS`/`IF NOT EXISTS`, RLS com `DROP POLICY IF
  EXISTS`. Segue o template de `c1d2e3f4a509`.
- **Rationale**: regra obrigatória do projeto (migrations idempotentes por causa do `create_all()`).
- **Nota**: o head `a6b7c8d9e014` está no working tree ainda **não commitado** (trabalho de print
  templates). A migration de 011 encadeia nele; ambos devem ser commitados na ordem correta.
