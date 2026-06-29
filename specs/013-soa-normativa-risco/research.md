# Phase 0 — Research: SoA Normativa dirigida pelo Tratamento de Riscos

Nenhum `NEEDS CLARIFICATION` pendente (4 clarificações resolvidas no `/speckit-clarify` + 4 no authoring
da spec). Esta pesquisa consolida as decisões técnicas de **reuso** sobre o módulo de SoA (005), o
insumo de Risco (012) e o padrão de Documento Controlado.

## R1. Insumo de risco já exposto (read-only)

- **Decisão**: consumir `risk_treatment_service.soa_feed(db, tenant_id)` (exposto em `GET /risk/soa-feed`,
  schema `SoaFeedItem`: `gap_catalog_item_id`, `ref_code`, `inclusion_reason="risk_treatment"`,
  `risk_ids[]`, `risk_codes[]`). Diretamente a função de serviço (mesmo processo), não via HTTP.
- **Rationale**: já agrega o vínculo controle←risco por `gap_catalog_item_id`, exclui riscos arquivados,
  é tenant-scoped, e o enum `SoaInclusionReason.risk_treatment` já existe. Zero reimplementação.
- **Alternativas rejeitadas**: recalcular o vínculo a partir de `RiskTreatmentControl` na SoA (duplicaria
  lógica do módulo de Risco — proibido pelas restrições da spec); chamar o endpoint HTTP internamente
  (overhead desnecessário, mesmo processo).

## R2. Casamento feed → item de SoA

- **Decisão**: indexar o feed por `gap_catalog_item_id` e casar com `SoaItem.catalog_item_id`
  (= `gap_catalog_item.id`). Itens de SoA são criados a partir do Anexo A do catálogo (passo Gap
  existente).
- **Rationale**: `SoaItem.catalog_item_id` já referencia `gap_catalog_item`; o feed usa a mesma chave.
- **Edge** (resolvido no clarify): feed aponta `gap_catalog_item` **fora** do conjunto Anexo A da SoA
  (custom/descontinuado) ⇒ não há `SoaItem`; a consolidação **não cria** item e **reporta notice**.

## R3. Armazenar riscos tratados: JSON vs. tabela

- **Decisão**: coluna **`risk_links` JSON** em `soa_item` (`list[{risk_id, risk_code}]`).
- **Rationale**: os vínculos são **projeção derivada** do feed (sem ciclo de vida próprio). JSON espelha
  `inclusion_reasons` (já JSON no mesmo modelo), evita tabela + RLS + trigger + migration pesada, e
  basta para snapshot/PDF e para a divergência (comparar `risk_links` vs. feed vivo). O texto legado
  `risks_treated` é preservado (coexistência, transição não destrutiva).
- **Alternativas rejeitadas**: tabela `soa_item_risk_link` (normalização desnecessária para projeção
  read-only; mais migration/RLS/append-only sem ganho); só derivar do feed sem persistir (impede selar
  os riscos no snapshot imutável da versão e detectar "risco órfão" após mudança do feed).

## R4. Divergência por fonte (Gap + risco)

- **Decisão**: estender `DivergenceField` com `source` (`gap`|`risk`) e `source_value`; manter
  `gap_value` como alias para `source=gap` (compat de frontend durante a transição). `compute_divergence`
  (Gap, existente) + `compute_risk_divergence` (novo) alimentam a mesma lista por item. Feed calculado
  **1×/requisição**.
- **Rationale**: reusa o contrato de divergência/reconciliação que a SoA já tem vs. o Gap (mesmo padrão
  de UX), evita N+1, e mantém as duas fontes independentes (reconciliáveis sem conflito).
- **Alternativas rejeitadas**: lista de divergência separada por fonte na resposta (duplica estrutura,
  complica o frontend); recomputar feed por item (N+1 sobre riscos).

## R5. Gate duro = rótulo imutável da versão

- **Decisão**: `has_approved_risk_plan = (RiskPlan.current_version_id is not None)` (tenant-scoped). Na
  aprovação, gravar `soa_kind` (`normative`|`pre_soa`) + `risk_plan_version_number` no `content_snapshot`.
  Aprovação **não** é bloqueada pela ausência de plano (emite como Pré-SoA); bloqueio só por **completude**
  (`_incomplete_refs`, já existente, cobre FR-009a).
- **Rationale**: `current_version_id` é o ponteiro "em vigor" do Documento Controlado (definido por
  `cds.approve_document`, nunca limpo hoje). Rótulo no snapshot ⇒ **imutável** por versão sem coluna
  nova (snapshot é JSON). Coerente com o padrão da 005 (assinatura/summary também vivem no snapshot).
- **Nota de evolução**: se um fluxo de revogação do Plano for adicionado no futuro, ele deve limpar
  `current_version_id` para que o gate volte a "Pré-SoA".
- **Alternativas rejeitadas**: coluna nova na `Soa`/`document_version` para o tipo (snapshot JSON já
  resolve, append-only); "ever-approved" (não-conforme — a SoA deve refletir o tratamento **vigente**).

## R6. Consolidação aditiva/idempotente "1ª-mão" para risco

- **Decisão**: aplicar risco (applicable + `risk_treatment` + `risk_links`) **apenas** quando o item
  nunca carregou vínculo de risco (`risk_treatment` ausente **e** `risk_links` vazio); itens já tocados
  por risco não são alterados na consolidação — drift vira divergência (R4) reconciliável.
- **Rationale**: espelha o contrato da 005 (consolidação preserva edições; drift via divergência). Evita
  sobrescrita silenciosa de decisão do usuário (constitution: corretude > velocidade). Idempotente.
- **Alternativas rejeitadas**: auto-sync a cada consolidação (sobrescreve decisões; divergência ficaria
  sempre zero, perdendo rastreabilidade); só flag sem nunca aplicar (perderia o ganho "uma ação").

## R7. Exportação PDF

- **Decisão**: enriquecer `soa_export_service.render_pdf` lendo do snapshot: rótulo da versão no
  cabeçalho; por controle, razões tipadas + riscos estruturados (códigos de `risk_links`, fallback ao
  texto legado) + origem. Reusa **reportlab** (já dependência da 005).
- **Rationale**: o PDF já lê do `content_snapshot`; basta o snapshot carregar os campos novos. Sem libs
  novas, sem mudança de pipeline.

## R8. Segurança / isolamento na agregação do feed

- **Decisão**: a consolidação chama `soa_feed(db, ctx.tenant_id)` com o tenant do contexto; nenhum acesso
  por id cru sem escopo. Teste de isolamento dedicado: org A com riscos/feed; usuário de B consolidando
  no contexto de B **não** vê itens/risk_links de A; consolidar em A só agrega feed de A.
- **Rationale**: Princípio I (fail-closed sempre, inclusive na agregação). RLS no PG reforça.
