# Phase 0 — Research: Módulo de Gestão de Riscos

**Feature**: `012-risk-management` · **Date**: 2026-06-26 · **Input**: [spec.md](spec.md), [plan.md](plan.md)

Todas as decisões abaixo resolvem os pontos de "Technical Context" e as clarificações de 2026-06-26.
Nenhum `NEEDS CLARIFICATION` permanece. O princípio condutor: **reusar os padrões já provados** dos
módulos Gap (004/007), SoA (005), Dashboard (006) e Ativos (011) — sem novidade arquitetural.

---

## R0 — Metas de performance / escala

- **Decision**: Sem alvo numérico de latência/throughput além do critério de UX do spec
  (SC-001: avaliar um risco em < 5 min). Listagem paginada e filtrável; heat map/dashboard/SoA-feed
  agregados em uma chamada cada.
- **Rationale**: Volume de PME (dezenas a poucas centenas de riscos/org). O gargalo é UX, não carga.
- **Alternatives**: Metas de p95/QPS — rejeitado por overengineering para o MVP.

## R1 — "Um módulo, três fases" (engenharia vs. esteira)

- **Decision**: Um domínio `risk_*` e **um** router `/risk`; a esteira expõe **três passos** (Ameaças/
  Vulnerabilidades · Avaliação · Tratamento) como rotas/telas distintas que compartilham o mesmo modelo
  de risco e a mesma metodologia.
- **Rationale**: A metodologia (escalas/matriz/critério) e o registro de risco são transversais às três
  fases; separar em módulos duplicaria modelo e RBAC. A continuidade da esteira é uma questão de
  navegação/telas, não de modelo.
- **Alternatives**: Três features separadas — rejeitado (acoplamento alto, duplicação de metodologia e
  permissões). Uma única tela monolítica — rejeitado (contraria a esteira guiada).

## R2 — Metodologia de risco: armazenamento e default 5x5

- **Decision**: Tabela `risk_methodology` **única por org** com a configuração em **colunas JSON**:
  `probability_scale` (lista de `{order:1..5, label}`), `impact_scale` (idem), `risk_levels`
  (lista de `{key, label, severity, color, order}`), `risk_matrix` (mapa `"<prob>x<impact>" → level_key`,
  25 células), `acceptance` (mapa `level_key → accepted:bool`) e `cia_impact_map` (mapa
  `CiaLevel → impact_order`). Um serviço `risk_methodology_service.get_or_default(tenant)` devolve a
  configuração da org **ou** um **default 5x5 in-code** quando não há linha (pré-requisito suave, FR-006).
  O cálculo de nível e a marcação de aceitação são funções puras sobre esse objeto.
- **Default 5x5**: probabilidade e impacto rotulados 1=Muito Baixa … 5=Muito Alta; níveis de risco
  Baixo/Médio/Alto/Crítico por faixas do produto `prob×impact` (1–4 Baixo, 5–9 Médio, 10–15 Alto,
  16–25 Crítico); critério de aceitação default = aceitar `≤ Médio`.
- **Rationale**: JSON evita 5 tabelas de configuração e mantém a matriz editável sem migration; o
  default in-code garante o gate suave sem exigir setup. Espelha a flexibilidade do `schema` JSON dos
  `FormTemplate` (Feature 003).
- **Alternatives**: Tabelas normalizadas para escala/célula — rejeitado (peso desproporcional ao MVP).
  Hardcode 5x5 sem persistência — rejeitado (FR-002..004 exigem configurável por org).

## R3 — Derivação do impacto a partir da CIA (clarificação Q1)

- **Decision**: Impacto inerente **derivado** = `cia_impact_map[ max(C,I,A) entre os ativos vinculados ]`.
  A CIA do Ativos tem 4 níveis (`baixa<media<alta<critica`, `CIA_ORDER` em `settings.py`); o
  `cia_impact_map` default mapeia para a escala de 5: `baixa→2, media→3, alta→4, critica→5` (nível 1
  reservado para "muito baixo"/cenários manuais). **Override** manual do impacto é sempre permitido e
  **exige justificativa** (gravada em `risk_event`); `impact_is_override` distingue derivado de ajustado
  e o sistema sinaliza **divergência** se a CIA mudar depois. **Sem ativos** (cenário simples): não há
  CIA → impacto **manual obrigatório**. **CIA incompleta** num ativo: avisa e cai no manual.
- **Rationale**: Coerente com `max(C,I,A)` já usado para criticidade no Ativos; o mapa configurável
  resolve o descompasso 4→5 sem travar a escala. Por-dimensão (C/I/D) é refinamento futuro (alinhado ao
  adiamento do apetite por categoria).
- **Alternatives**: Por dimensão (3 impactos/risco) — deferido (multiplica entidades/UX). Impacto sempre
  manual — rejeitado (perde o valor de derivar da classificação já feita no Ativos).

## R4 — Catálogos de ameaças/vulnerabilidades: semente + cópia da org

- **Decision**: Reusar **exatamente** o padrão do Gap (Feature 004): tabelas-semente **platform-level
  sem `tenant_id`** (`threat_seed_item`, `vulnerability_seed_item`, somente leitura, editáveis só pelo
  Super Admin) + **cópia editável por org** (`org_threat`, `org_vulnerability`, com `tenant_id`+RLS e
  `seed_item_id` apontando para a semente). `risk_catalog_service.load_seed()` semeia idempotentemente;
  `adopt_seed(tenant)` materializa/atualiza a cópia da org de forma **aditiva e idempotente** (itens
  novos entram; personalizações e itens próprios preservados; itens removidos do seed marcados
  `is_archived`/descontinuados, nunca deletados). Sem tabela de versão do seed (conjunto único 27005;
  chaveado por `code`).
- **Rationale**: Padrão comprovado e testado; evita reinventar adoção/idempotência. A exceção "seed sem
  tenant" já existe e é aceita pela constitution (conteúdo de plataforma).
- **Alternatives**: Catálogo só por org (sem semente) — rejeitado (perde o conteúdo de partida 27005).
  Versão de seed como no Gap — rejeitado (sem necessidade de múltiplas versões de 27005 no MVP).
- **Conteúdo**: PT-BR **original** (não reproduzir texto normativo ISO 27005), em `data/iso27005_seed.py`.
  Ameaça: `code, name, description, category` (humana/ambiental/técnica; deliberada/acidental).
  Vulnerabilidade: `code, name, description, category`.

## R5 — Identificador interno do risco

- **Decision**: `RSK-####` — prefixo fixo `RISK_CODE_PREFIX="RSK"` (em `settings.py`) + sequência por
  organização, imutável após a criação. Geração reaproveita a abordagem do `asset_service` (contar/
  max+1 por tenant sob a mesma transação; `UniqueConstraint(tenant_id, code)`).
- **Rationale**: Consistência com o código de Ativos (ATV-0001). Ameaças/vulnerabilidades usam `code`
  próprio (AME-/VUL-) herdado da semente ou gerado no custom.
- **Alternatives**: UUID exposto — rejeitado (ruim para humanos/relatórios). Sequência global — rejeitado
  (vaza volume entre tenants e quebra isolamento conceitual).

## R6 — Plano de Tratamento como Documento Controlado

- **Decision**: `RiskPlan` **único por org** (ponteiro `current_version_id` + `draft_status`), reusando
  `controlled_document_service` (`submit_review`/`approve_document`) e `document_versions` com **novo**
  `DocType.risk_treatment_plan`. A aprovação grava uma **versão imutável** com `content_snapshot` do
  registro de riscos + tratamentos + residuais; **assinatura avançada opcional** reusa o
  `signature_service` (003) na aprovação (selo SHA-256 no snapshot), exatamente como na SoA (005).
- **Rationale**: Mesmo mecanismo já usado por SoA e Gap baseline; append-only garantido por gatilho
  existente; zero código novo de versionamento.
- **Alternatives**: Versionamento próprio do módulo — rejeitado (duplicação, risco de divergir do
  append-only). Plano por risco (N planos) — rejeitado (o artefato ISO 6.1.3 é único e consolidado).

## R7 — Fronteira com a SoA: alimentar, não finalizar (clarificação Q2)

- **Decision**: O módulo **não grava nem muta** `soa`/`soa_item`. Cada `risk_treatment_control` que
  referencia um `gap_catalog_item` (controle A.5–A.8 da org) é exposto via **`GET /risk/soa-feed`**
  (read-only): para cada `gap_catalog_item_id`, devolve `inclusion_reason = "risk_treatment"` e a lista
  de riscos tratados (texto/ids). A futura feature de finalização da SoA consumirá esse feed para
  preencher `soa_item.inclusion_reasons`/`risks_treated` (campos forward-compatible já existentes).
- **Rationale**: Respeita "alimentar, não finalizar"; mantém a SoA atual como Pré-SoA; evita acoplar a
  escrita da SoA a este módulo (e dois donos do mesmo dado).
- **Alternatives**: Pré-gravar `soa_item` em staging — rejeitado na clarificação (dois donos do dado,
  risco de inconsistência). Configurável por org — rejeitado (complexidade sem demanda no MVP).

## R8 — Histórico append-only do risco

- **Decision**: Tabela `risk_events` (tenant-scoped) com gatilhos append-only (SQLite `RAISE(ABORT)` +
  PG `RAISE EXCEPTION`, no padrão de `asset_item_events`/`soa_item_event`). Grava `event_type,
  field_name, old_value, new_value, reason, actor_id, occurred_at, details`. `risk_service` faz o
  diffing e exige `reason` nas mudanças relevantes (aceitação, mudança de nível, decisão de tratamento,
  aprovação). Auditoria central (`AuditService`) é complementar (não substitui o histórico do domínio).
- **Rationale**: Padrão idêntico aos módulos anteriores; histórico de domínio consultável na tela +
  trilha de auditoria de plataforma.
- **Alternatives**: Só `audit_logs` — rejeitado (audit não guarda valor anterior/novo por campo de forma
  consultável pela tela do risco).

## R9 — Integração com Ativos (preencher placeholders sem alterar o modelo)

- **Decision**: Vínculos `asset_threat_link`/`asset_vulnerability_link` (Fase 1) e `risk_asset_link`/
  `risk_treatment_control` (Fases 2/3) referenciam `asset_items.id`. A tela `pages/asset-detail` é
  **estendida** para chamar `GET /risk/assets/{asset_id}/links` e renderizar nas seções placeholder já
  existentes ("Ameaças/Vulnerabilidades/Riscos vinculados", "Controles relacionados"). O **modelo** de
  Ativos não muda (FR-033); só a tela consome novos endpoints.
- **Rationale**: O 011 já entregou os placeholders; aqui apenas os "ligamos". Mantém o módulo Ativos
  intacto e o acoplamento unidirecional (Risco → Ativos).
- **Alternatives**: FK reversa no `asset_items` — rejeitado (alteraria o modelo de Ativos e inverteria a
  dependência).

## R10 — Readiness na esteira (Dashboard de Conformidade)

- **Decision**: Estender `dashboard_service` com `_risk_card(db, ctx)` gated em `view_risk` (mesmo
  padrão fail-open por card) e adicionar `DashboardModuleId.risk` ao `dashboard_schema`. O card resume:
  status (not_started/draft/in_review/in_force via plano), progresso (riscos avaliados / total;
  tratados / acima do critério), próxima ação (rota da fase pendente) e bloqueios (ex.: riscos não
  avaliados barrando a aprovação do plano). O **dashboard do módulo** (heat map etc.) é endpoint próprio
  `GET /risk/dashboard` (não sobrecarrega a home).
- **Rationale**: Reusa a camada de agregação (Feature 006) sem novo modelo; separa a home (resumo) do
  dashboard analítico do módulo.
- **Alternatives**: Tudo na home — rejeitado (home é resumo; heat map é do módulo).

## R11 — RLS e exceção de seed

- **Decision**: As **10 tabelas tenant-scoped** recebem policy RLS `tenant_isolation` (igual aos módulos
  existentes; `app.tenant_id` via `set_config`): `risk_methodology`, `org_threat`, `org_vulnerability`,
  `asset_threat_link`, `asset_vulnerability_link`, `risk`, `risk_asset_link`, `risk_treatment_control`,
  `risk_plan`, `risk_events`. As 2 tabelas-semente (`threat_seed_item`, `vulnerability_seed_item`)
  **não** recebem RLS (platform-level read-only), mesma exceção documentada do `gap_seed_item`.
- **Rationale**: Consistência e defesa em profundidade; o seed é conteúdo compartilhado por design.

## R12 — Cálculo de nível e heat map (server-side)

- **Decision**: Nível inerente/residual e a marcação acima/abaixo do critério são **calculados no
  backend** (`risk_methodology_service`) e **persistidos desnormalizados** (`inherent_level_key`,
  `above_acceptance`, `residual_level_key`, `residual_above_acceptance`) para listagem/filtro rápidos; ao
  mudar a metodologia, um **recálculo em massa** (FR-008) reescreve esses campos a partir de
  prob/impacto e sinaliza os que mudaram (gera `risk_event` de mudança de nível). O heat map 5x5 é
  agregado em `risk_metrics_service`.
- **Rationale**: Filtros por nível/aceitação e o heat map precisam ser baratos; recalcular sob demanda em
  cada listagem seria custoso e dependente da metodologia.
- **Alternatives**: Calcular tudo on-the-fly — rejeitado (custo + filtro por nível fica difícil).

## R13 — Residual = re-pontuação simples

- **Decision**: O residual é uma **nova pontuação** de prob/impacto na mesma metodologia (sem fórmula de
  eficácia de controle). Disponível para qualquer opção de tratamento; para **"aceitar"**, o residual
  default = inerente (o usuário pode ajustar). O sistema compara inerente×residual, sinaliza aumento e
  marca se o residual atende ao critério (e lista "risco residual pendente" quando não).
- **Rationale**: Spec (restrição 13) exige re-pontuação simples; evita pseudo-precisão.
- **Alternatives**: Redução automática por controle — rejeitado explicitamente no spec.

---

### Resumo de decisões → entidades/endpoints

| Decisão | Impacto no design |
|--------|--------------------|
| R2 metodologia JSON + default | `risk_methodology` (1/org) · `GET/PUT /risk/methodology` |
| R3 impacto da CIA | campos `impact_*` no `risk` · derivação no `risk_service` |
| R4 semente + cópia | `*_seed_item` (plataforma) + `org_threat`/`org_vulnerability` · `POST /risk/{threats,vulnerabilities}/adopt` |
| R5 código RSK | `risk.code` + `RISK_CODE_PREFIX` |
| R6 plano controlado | `risk_plan` + `DocType.risk_treatment_plan` · `/risk/plan/*` |
| R7 SoA-feed | `GET /risk/soa-feed` (read-only; não escreve SoA) |
| R8 histórico | `risk_events` (append-only) · `GET /risk/risks/{id}/history` |
| R9 placeholders | `asset_*_link` + `risk_asset_link`/`risk_treatment_control` · `GET /risk/assets/{id}/links` |
| R10 esteira | `_risk_card` no `dashboard_service` + `GET /risk/dashboard` |
| R12 nível desnormalizado | `inherent_level_key`/`above_acceptance`/`residual_*` + recálculo em massa |
