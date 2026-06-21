# Research — Gap Analysis (Feature 004)

Decisões técnicas (Phase 0). Cada item: Decisão · Justificativa · Alternativas rejeitadas.

## 1. Catálogo-base (seed) compartilhado × cópia por organização

**Decisão**: Duas camadas.
- `gap_seed_item` (+ `gap_seed_version`): catálogo-base **da plataforma**, **compartilhado** (sem
  `tenant_id`), **somente leitura** para a aplicação; versionado por `seed_version`.
- `gap_catalog_item`: **cópia editável por organização** (com `tenant_id` + RLS), referenciando o
  item-seed de origem (`seed_item_id`), com flags de personalização (`is_custom`, `is_renamed`) e de
  aplicabilidade.

A cópia é **materializada na adoção** (opt-in): quando a organização inicia o gap analysis (ou adota
uma nova versão do seed), o serviço copia os itens da versão escolhida para `gap_catalog_item`.

**Justificativa**: o conteúdo da norma é idêntico para todos os tenants e mantido pela plataforma —
mantê-lo único evita N cópias só-leitura e centraliza o versionamento; a edição/avaliação acontece na
cópia por org, preservando o isolamento. Alinha com FR-001..004 e a decisão de Clarifications
(opt-in versionado, aditivo).

**Alternativas rejeitadas**:
- *Seed por tenant desde o início*: duplicação massiva idêntica; complica versionar o seed central.
- *Seed só em código (sem tabela), materializado on-the-fly*: dificulta versionar e auditar a
  evolução do catálogo-base e comparar versões.

## 2. Modelagem da avaliação (matriz) e histórico

**Decisão**: `GapAssessment` (1 por organização, padrão "1 vigente + histórico" do Módulo 1) como
container; `GapAssessmentItem` por `gap_catalog_item` com os campos da avaliação (status,
constatações, ações, prioridade, responsável, prazo, evidência textual, observações, justificativa de
exclusão, maturidade/esforço opcionais). Histórico de alterações **append-only** em
`gap_assessment_item_event` (gatilho como em `audit_logs`/`document_versions`).

**Justificativa**: reaproveita o padrão consolidado nos Módulos 1/3; volume pequeno (~100 itens);
append-only atende SEC-005 sem reescrever o item a cada mudança.

**Alternativas rejeitadas**:
- *Versão imutável do item inteiro a cada edição*: custo/ruído alto para ~100 itens com muitas
  pequenas edições; o snapshot completo já existe na **baseline**.
- *Múltiplos GapAssessment ativos por org*: contraria o modelo "1 vigente"; baselines cobrem o
  histórico.

## 3. Baseline via Documento Controlado

**Decisão**: a baseline reusa `controlled_document_service.approve_document` + `document_versions`,
com **novo `DocType.gap_baseline`**. O `snapshot_factory` serializa a matriz inteira (itens + status +
campos) e a **aderência consolidada** no momento do congelamento. `current_version_id` no
`GapAssessment` aponta a baseline vigente; baselines anteriores ficam imutáveis (gatilho append-only)
e comparáveis por `version_number`.

**Justificativa**: o padrão já entrega versão imutável, aprovador/data/status, histórico e a derivação
de obsolescência por recência (`is_superseded`) — exatamente o que a baseline precisa. Zero
reinvenção.

**Alternativas rejeitadas**:
- *Tabela própria de baseline*: duplicaria a mecânica de Documento Controlado já testada.

## 4. Reuso do Motor de Workflow 003 na condução (US5)

**Decisão**: entidade dedicada `GapAssignment` (com `tenant_id`) que **reusa os serviços
transversais do 003**: trilha (`form_assignment_event`), assinatura (`FormSignature` + OTP via
`signature_service`), notificação (`notification_service`) e a máquina de estados
(pending→in_progress→submitted→signed→completed + return/cancel). `GapAssignment` referencia o
`GapAssessment` e um **escopo** (`whole` | `theme:A.5|A.6|A.7|A.8`). A assinatura congela a baseline
(item 3).

**Justificativa**: a Gap Analysis não é um `FormTemplate` de campos genéricos (a "resposta" é a
matriz), então **forçá-la** em `FormAssignment` distorceria o modelo. Uma `GapAssignment` fina
reusa as mesmas peças sem acoplar a matriz ao formato de formulário. Granularidade conforme
Clarifications (inteira por padrão; opção por tema).

**Alternativas rejeitadas**:
- *Reusar `FormAssignment` com um "kind=gap"*: `FormAssignment` carrega `fields_snapshot`/`answers`
  de formulário; a matriz não cabe nesse formato sem gambiarra.
- *Generalizar `FormAssignment` para qualquer "subject"*: refactor grande e arriscado no 003 já
  estável; melhor extrair serviços compartilhados (eventos/assinatura) e ter `GapAssignment` própria.

> US5 é P5: o MVP (US1–US2) e US3–US4 não dependem dela. Se o esforço de `GapAssignment` for alto,
> pode ser entregue após o núcleo, sem bloquear.

## 5. Fórmula de aderência (confirmada em Clarifications)

**Decisão**: `gap_metrics_service` calcula, sobre **itens aplicáveis** (exclui "Não aplicável" e
"Não preenchido"): peso Atende totalmente=1.0, Atende parcialmente=0.5, Não atende=0.0. Aderência =
soma(pesos)/contagem(aplicáveis). Recorte sem itens aplicáveis ⇒ `null`/"—". Mesma função serve
geral, por dimensão, por cláusula e por tema (garante consistência entre as visões — SC-002).

**Justificativa**: determinístico, recomputável em teste, consistente entre recortes.

**Alternativas rejeitadas**: binário (só Atende=100%) e incluir "Não preenchido" no denominador —
descartadas pela resposta do `/clarify`.

## 6. RLS para tabela compartilhada (seed)

**Decisão**: `gap_seed_item`/`gap_seed_version` **não** têm RLS (são compartilhadas, só-leitura). O
acesso de escrita ao seed é exclusivo de processo de plataforma/migração (não exposto a endpoints de
organização). Todas as tabelas por-org (`gap_catalog_item`, `gap_assessment*`, `gap_assignment`)
têm RLS + gatilho append-only onde aplicável, como no módulo 003.

**Justificativa**: RLS protege dado por-tenant; aplicá-la a uma tabela de referência compartilhada
não faz sentido e quebraria a leitura. O risco (escrita indevida) é mitigado por não haver endpoint
de escrita no seed para organizações.

**Alternativas rejeitadas**: RLS com policy "leitura para todos" — complexidade sem ganho; a tabela
não tem `tenant_id` para escopar.

## 7. Permissões (RBAC)

**Decisão**: novas permissões `view_gap`, `manage_gap`, `approve_gap_baseline`. A **condução** reusa
`assign_form`/`fill_form`/`sign_form` do 003 (é literalmente o motor de workflow). Matriz:
`org_admin`/`consultant` = manage; `manage_gap`/`view_gap` distribuídos a gestor/auditor/cliente
conforme o padrão do Módulo 1. `approve_gap_baseline` no `org_admin` (alinhado a
`approve_context_document`).

**Justificativa**: reuso máximo; granularidade suficiente sem inflar a matriz de permissões.

## 8. Seed da norma (conteúdo inicial)

**Decisão**: `wtnapp/data/iso27001_seed.py` com as Cláusulas 4–10 e os 93 controles do Anexo A
(A.5=37, A.6=8, A.7=14, A.8=34), derivado do estudo de caso real (Nexim) em `material_de_contexto/`.
Carregado para `gap_seed_item` via migração/seed idempotente. `seed_version` inicial = "2022.1".

**Justificativa**: dado de referência estável; idempotente; rastreável por versão.

**Alternativas rejeitadas**: importar de planilha em runtime — frágil e não versionável.
