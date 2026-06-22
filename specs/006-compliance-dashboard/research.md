# Phase 0 — Research: Dashboard de Conformidade

Sem `NEEDS CLARIFICATION` pendentes (resolvidos no spec + `/speckit-clarify`). Esta pesquisa
consolida as decisões técnicas de **como** compor os serviços existentes.

---

## D1 — Agregação no backend (endpoint único) vs composição no frontend

**Decision**: Um único endpoint `GET /dashboard` agrega no servidor. O frontend faz **uma** chamada.

**Rationale**:
- Habilita `require_permission("view_dashboard")` server-side (SEC-002) e log central de tentativas
  não autorizadas (SEC-003) — impossível de garantir com composição no cliente.
- Permite **um único** teste de isolamento de tenant (SC-ISO) em vez de confiar no isolamento de
  cada endpoint separadamente.
- **Corrige dois bugs latentes** da home atual (que compõe no frontend):
  1. Ela chama `/gap-assessment/dashboard`, mas o endpoint real é **`/gap/assessment/dashboard`**
     (prefix do router). O `catchError(()=>of(null))` mascarava o 404 ⇒ Gap aparecia sempre como
     "não iniciado".
  2. Ela mapeia status `under_review`/`approved`, mas o backend emite `DocStatus` =
     `draft`/`in_review`/`in_force` ⇒ rótulos nunca batiam para "em revisão"/"aprovado".
  O endpoint backend define o **vocabulário de status normalizado** uma única vez.

**Alternatives considered**:
- *Composição no frontend (status quo)*: rejeitado — não permite enforcement nem audit server-side,
  e replica o acoplamento a rotas/contratos de cada módulo no cliente.
- *Materializar uma tabela `dashboard_snapshot`*: rejeitado — adiciona modelo de domínio,
  invalidação e migration para dados que já existem; contraria "sem novo modelo".

---

## D2 — Onde mora a lógica de agregação

**Decision**: `services/dashboard_service.py` com uma função `build_dashboard(db, ctx)` que devolve
um dict/DTO; o router `dashboard.py` é fino (só dependency + chamada). Segue o padrão de
`gap_metrics_service` / `soa_consolidation_service`.

**Rationale**: testável isoladamente (sem TestClient), reutilizável, e mantém o router enxuto como
nos demais módulos. Constituição proíbe repository layer mas incentiva `services/` para lógica
reutilizável.

**Alternatives considered**: lógica inline no router — rejeitado por dificultar teste unitário e
fugir do padrão dos módulos 2–3.

---

## D3 — Composição por módulo (fontes de verdade)

**Decision**: o service reusa as funções já existentes, sem reimplementar regra de negócio:

| Card | Status | Progresso | Responsável/Prazo | Revisão vencida |
|------|--------|-----------|-------------------|-----------------|
| **Contexto (Cl. 4)** | `draft_status` + `current_version_id` dos 3 artefatos via helpers de `context_analysis`/`scope`/`stakeholders` | derivado: nº de artefatos aprovados / 3 | atribuição ativa (`form_assignments` kind diagnóstico) se houver | `cds.review_overdue(current_version)` do escopo |
| **Gap Analysis** | há `GapAssessment`? `draft_status` + `current_version_id`; senão "não iniciado" | `compute_dashboard(...)["completeness"]` (e `overall_adherence` p/ KPI) | item-level `responsible`/`deadline` agregado (próximo prazo) | `review_overdue` da baseline corrente |
| **SoA** | `Soa.draft_status` + `current_version_id`; senão "não iniciado" | itens com `implementation_status` não nulo / total | `responsible`/`deadline` dos itens (próximo prazo) | `review_overdue` da versão corrente |

**Rationale**: fonte de verdade única por módulo; o dashboard só lê e normaliza. `compute_dashboard`
já exclui N/A e not_filled corretamente.

**Alternatives considered**: recomputar métricas no service do dashboard — rejeitado (duplicação de
regra, risco de divergência com a tela do módulo).

---

## D4 — Vocabulário de status normalizado do card

**Decision**: enum de apresentação `DashboardCardStatus`: `not_started`, `draft`, `in_review`,
`in_force`, `needs_review` (aprovado porém `review_overdue`). Derivado de `DocStatus` +
`current_version_id` + `review_overdue`.

Mapa: sem artefato/dados ⇒ `not_started`; `draft_status=in_review` ⇒ `in_review`;
`current_version_id` presente e **não** vencido ⇒ `in_force`; presente e vencido ⇒ `needs_review`;
caso contrário ⇒ `draft`.

**Rationale**: resolve o desalinhamento de rótulos (D1) e dá ao frontend um vocabulário estável,
agnóstico do `DocStatus` interno.

**Alternatives considered**: expor `DocStatus` cru — rejeitado: vaza semântica de documento
controlado e não cobre o caso "aprovado mas vencido".

---

## D5 — Próxima ação recomendada

**Decision**: heurística por estado no service, devolvendo `{ label, route, fragment? }`. `route` é
a **rota de entrada do módulo**; `fragment` (âncora/seção) só quando a rota do módulo já oferece o
ponto de entrada — esta feature **não** cria novas rotas internas (decisão de clarificação, FR-007).

Exemplos: Contexto sem análise ⇒ "Completar análise de contexto" → `context-analysis`; Gap com
catálogo não adotado ⇒ "Adotar catálogo" → `gap-catalog`; Gap incompleto ⇒ "Avaliar controles" →
`gap-analysis`; SoA não consolidada ⇒ "Consolidar do Gap" → `soa`; SoA completa ⇒ "Enviar para
revisão" → `soa`; aprovado ⇒ "Ver versões" → `soa-versions`.

**Rationale**: reaproveita a ideia heurística do `suggestion_service` (Módulo 1) sem IA; pragmático
e sem reescrever roteamento dos módulos.

**Alternatives considered**: deep-link a passo exato em todos os módulos — rejeitado (custo de
integração por módulo, fora do escopo da clarificação).

---

## D6 — RBAC: a permissão `view_dashboard`

**Decision**: adicionar `"view_dashboard"` à matriz estática `PERMISSIONS` em `helpers/permissions.py`
para **todos os papéis exceto `guest_collaborator`** (default da SEC-002). Os cards são filtrados por
`has_permission(role, "view_context"/"view_gap"/"view_soa")` — usuário sem a permissão do módulo não
recebe aquele card.

**Rationale**: a plataforma só tem matriz **estática** papel→permissão (sem override por tenant). O
trecho da SEC-002 "convidado recebe se o Admin liberar" pressupõe um mecanismo de elevação por tenant
que **não existe** hoje; construí-lo seria uma feature à parte. Honramos o **default** (todos menos
convidado) e **deferimos** a elevação por tenant.

**Alternatives considered**:
- Conceder a todos inclusive convidado — rejeitado: contraria o default explícito da spec.
- Construir override de permissão por tenant agora — rejeitado: fora de escopo; vira feature de RBAC.

**Deferred / documented**: elevação de `view_dashboard` para `guest_collaborator` por organização
(precisa de um modelo de override de permissões por tenant — não existe no MVP).

---

## D7 — Auditoria

**Decision**: o router **não** chama `AuditService` no caminho de sucesso. Tentativas não
autorizadas já são auditadas pelas dependencies centrais: `get_org_context` emite
`CROSS_TENANT_DENIED` (cross-tenant) e bloqueia org suspensa (403); `require_permission` emite
`PERMISSION_DENIED`.

**Rationale**: cumpre SEC-003 (só não autorizadas) **reusando** o que já existe, sem código novo de
auditoria e sem inflar a trilha com leituras de home.

**Alternatives considered**: logar todo READ — rejeitado pela clarificação (volume e ruído na trilha
append-only).

---

## D8 — Degradação por card (resiliência)

**Decision**: o service envolve a montagem de **cada card** em try/except; falha ao agregar um
módulo ⇒ aquele card volta com `status="error"` e os demais seguem normais (fail-open por card).
Isolamento de tenant continua fail-closed (erro na resolução do tenant ⇒ 404/403, nunca dado
parcial de outro tenant).

**Rationale**: SC-005 / edge case da spec — falha localizada não derruba a home.

**Alternatives considered**: 500 global se qualquer módulo falhar — rejeitado (uma avaliação
malformada de Gap tiraria toda a home do ar).

---

## D9 — Conformidade ao longo do tempo (FR-011, P2)

**Decision**: derivar a série de `DocumentVersion` com `document_type = DocType.gap_baseline`,
lendo `content_snapshot["dashboard"]["overall_adherence"]` + `emitted_at`/`version_number`. Exposto
como `adherence_trend: [{date, adherence}]`, **somente** com ≥ 2 baselines; senão `null`/vazio. P2 —
pode ser entregue na mesma rodada ou logo depois, sem alterar o contrato dos cards (campo aditivo).

**Rationale**: usa exclusivamente baselines aprovadas (sem projeção/interpolação), conforme spec.

**Alternatives considered**: série a partir de snapshots ad-hoc por data — rejeitado (sem fonte
imutável; baselines são o registro versionado correto).

---

## D10 — Performance & cache

**Decision**: agregação **ao vivo** a cada request, sem cache, no MVP. As consultas são pequenas e
escopadas por tenant (índices por `tenant_id` já existem). Meta < 2 s (SC-001) folgada.

**Rationale**: simplicidade e dado sempre fresco (a home reflete o estado real). Cache introduz
invalidação — custo desnecessário agora.

**Alternatives considered**: cache curto em Redis por tenant — **deferido**; só se medições futuras
mostrarem latência. Documentado como evolução, não MVP.
