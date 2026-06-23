# Quickstart — Feature 004 (Gap Analysis)

Validação E2E do fluxo: adotar catálogo → avaliar matriz → dashboard/lacunas → personalizar →
baseline → condução atribuível/assinável → isolamento. Pré-requisitos: features 001/002/003
implementadas; org criada e selecionada (`X-Org-Context`); Super Admin/Consultor/Cliente. Backend
`:8000`, frontend `:4200`. Chamadas REST equivalentes às telas.

## Cenário A — Adotar o catálogo e avaliar (caminho feliz)

1. **Adotar o seed**: `POST /gap/catalog/adopt {"seed_version":"2022.1"}` → materializa a cópia da org
   (7 cláusulas + 93 controles). `GET /gap/catalog` lista os itens.
2. **Abrir a matriz**: `GET /gap/assessment` → avaliação vigente com todos os itens em
   `not_filled`.
3. **Avaliar**: `PUT /gap/assessment/items/{id}` com `{"status":"partial","findings":"...",
   "actions":"...","priority":"high"}`. Salvar e reabrir → persiste; histórico (evento) registrado.
4. **Teste negativo (N/A sem justificativa)**: `PUT .../items/{id}` `{"status":"not_applicable"}`
   **sem** `exclusion_justification` → **422**. Com justificativa → 200, e o item sai do cálculo.

## Cenário B — Indicadores e lacunas

1. `GET /gap/assessment/dashboard` → `overall_adherence` (0..1) + `by_dimension`/`by_clause`/
   `by_theme` + `status_distribution` + `completeness`. Conferir: peso Atende=1.0/Parcial=0.5/
   Não atende=0.0; N/A e Não preenchido fora do denominador; recorte sem aplicáveis ⇒ `null` ("—").
2. `GET /gap/assessment/gaps?order_by=priority` → apenas itens aplicáveis `partial`/`not_meet`,
   ordenados Crítica→Baixa (insumo do Plano de Ação).

## Cenário C — Catálogo editável por organização

1. `POST /gap/catalog/items` (item próprio) → aparece só na Org atual.
2. `PATCH /gap/catalog/items/{id}` (renomear/objetivo) → cópia da org muda; seed-base e Org B intactos.
3. **Adoção aditiva**: publicar `seed_version` nova e `POST /gap/catalog/adopt` → itens novos entram
   como `not_filled`; personalizações e avaliações preservadas; removidos viram `is_discontinued`.

## Cenário D — Baseline versionada e comparação

1. `POST /gap/assessment/submit-review` → `in_review`.
2. `POST /gap/assessment/approve {"classification":"uso_interno","change_nature":"Emissão inicial"}`
   (Admin) → congela **baseline v1** (`DocumentVersion`, imutável). `GET /gap/assessment/baselines`.
   - **Negativo**: aprovar sem revisão ⇒ **409**; aprovar como Consultor ⇒ **403**.
3. Altere itens, aprove de novo → **baseline v2**; `GET /gap/assessment/baselines/compare?from=v1&to=v2`
   → variação de aderência. v1 permanece imutável (gatilho append-only).

## Cenário E — Condução atribuível e assinável (reusa Motor 003)

1. `POST /gap/assignments {"scope":"theme","scope_theme":"technological","respondent_user_id":"..."}`
   → atribui a condução do tema A.8 a um membro (ou `respondent_email` para externo via link/OTP).
   Preenchedor é notificado, assume, preenche os itens e envia (trilha imutável dos eventos).
2. `POST /gap/assignments/{id}/sign` (signatário) → assina (nível avançada) e **congela a baseline**
   com selo de integridade verificável.

## Cenário F — Isolamento de tenant (obrigatório)

1. Com duas organizações, autenticar como membro da Org A (`X-Org-Context: A`).
2. `GET /gap/assessment/items/{id_da_org_B}` / `PATCH /gap/catalog/items/{id_da_org_B}` ⇒ **404**.
3. Confirmar no audit log o registro da tentativa cross-tenant.
4. O catálogo-seed compartilhado é **somente leitura**: nenhum endpoint de organização escreve nele.
5. Coberto por `wtnapp/test/test_tenant_isolation_gap.py`.

## Registro de validacao E2E

Validado em 2026-06-23 contra backend local `http://localhost:8000` e DB real, com o run
`20260623074439`. A validacao parcial anterior foi executada em 2026-06-22 com o run
`20260622214313`.

- Cenários A-D validados via API: adocao idempotente do catalogo, matriz com itens materializados,
  persistencia de avaliacao, negativo de N/A sem justificativa, N/A com justificativa, dashboard,
  lacunas priorizadas, item proprio de catalogo, baseline v1/v2 e comparacao de baselines.
- Cenario E validado: criacao/listagem de atribuicao, claim, submit e assinatura autenticada via
  `POST /gap/assignments/{id}/sign`, congelando uma baseline versionada com selo SHA-256. O caminho
  de assinatura validado usa usuario autenticado com `sign_form`; fluxo publico de OTP externo nao
  foi expandido nesta correcao.
- Cenario F coberto pela suite automatizada de isolamento.
- Suite automatizada executada: `.\\.venv\\Scripts\\pytest.exe wtnapp/test/test_gap_assessment.py
  wtnapp/test/test_gap_metrics.py wtnapp/test/test_gap_catalog.py wtnapp/test/test_gap_baseline.py
  wtnapp/test/test_gap_assignment.py wtnapp/test/test_tenant_isolation_gap.py`.
- Resultado: `41 passed`.
