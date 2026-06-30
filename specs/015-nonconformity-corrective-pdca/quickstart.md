# Quickstart — NC/Ações Corretivas + Análise Crítica + PDCA (Feature 015 / 5b)

Roteiro E2E (browser + Postgres real). Pré-requisitos: backend `:8000`, frontend `:4200`, `.env` com
`DATABASE_URL`/`FIELD_ENCRYPTION_KEY`. A **Feature 5a deve estar aplicada** (auditoria + evidências).
Login como Admin da organização (tem `manage_nonconformity` + `manage_management_review` +
`approve_management_review`).

## 0. Migração
```bash
alembic upgrade head     # cria nonconformity_*/management_review/improvement_* (down_revision=b8c9d0e1f016)
pytest wtnapp/test/test_nonconformity.py wtnapp/test/test_nc_promotion.py
```

## 1. NC + promoção da 5a (US1)
1. Em **Auditoria Interna** (5a), abra uma auditoria com uma constatação **NC menor/maior** e use
   **Promover a NC** → confirme que abre a NC criada (origem `audit_finding`, severidade mapeada) e que
   a constatação passa a referenciar a NC.
2. Promova a **mesma** constatação de novo → o sistema abre a NC existente (idempotente, sem duplicar).
3. **Nova NC** manual: origem, descrição, severidade, vínculo a um controle da SoA; registre a **causa
   raiz**. A NC nasce `aberta`.

## 2. Ação corretiva + verificação de eficácia (US2)
1. Na NC, **adicione ação corretiva** (descrição, responsável = membro, prazo). Crie uma com prazo no
   passado → aparece como **prazo vencido**.
2. Transite a NC `iniciar` → `enviar p/ verificação`. Tente **encerrar** sem verificação → bloqueado
   (gate).
3. Registre **verificação de eficácia = eficaz**; conclua as ações; **encerre** a NC → permitido.
4. Verifique a trilha (append-only): `promoted`/`action_added`/`verified`/`closed`.

## 3. Evidências nas NCs/ações (US4, via 5a)
1. Na NC e numa ação corretiva, **anexe evidência** (painel reutilizado da 5a; `target_type=
   nonconformity` / `corrective_action`). Confirme metadados/integridade/classificação herdados.

## 4. Lista e dashboard (US3/US7)
1. **Lista de NCs**: filtre por status/severidade/responsável/prazo vencido.
2. **Dashboard do módulo**: NCs por status/severidade, ações vencidas, melhorias por status.

## 5. Análise crítica pela direção (US5)
1. **Nova análise crítica** (reunião): preencha entradas (ações anteriores, mudanças, desempenho,
   auditoria, riscos, NCs) e saídas/decisões.
2. **Submeter** → tentar aprovar incompleta → gate bloqueia (409).
3. **Aprovar** (com e sem **assinatura**) → versão imutável; **Exportar PDF**.
4. Crie uma **segunda** análise crítica (data diferente) → confirme que a coleção lista as duas atas.

## 6. Melhorias + visão PDCA (US6)
1. Registre **melhorias** de origens distintas (auditoria, NC, análise crítica, sugestão), referenciando
   um controle/risco (read-only).
2. Abra a **visão de ciclo PDCA** (em um controle/risco) → confirme o loop fechado
   constatação→NC→ação→melhoria→artefato, **somente leitura**, sem alterar os módulos consumidos.
3. **Dashboard de Conformidade**: o card desta etapa reflete o fechamento do PDCA.

## 7. Isolamento de tenant (obrigatório)
1. Como usuário da Org A, `GET /nonconformities/{id}` / análise crítica / melhoria da Org B → 404 + audit.
2. Promover uma constatação da Org B no contexto A → 404 (alvo não existe no tenant).
3. PDCA/dashboard nunca agregam dados de B.
4. Rodar: `pytest wtnapp/test/test_tenant_isolation_nonconformity.py`.

## Suítes de teste (planejadas)
- Backend: `test_nonconformity.py`, `test_nc_promotion.py`, `test_corrective_action.py`,
  `test_nc_verification_gate.py`, `test_management_review.py`, `test_improvement_pdca.py`,
  `test_nc_metrics.py`, `test_tenant_isolation_nonconformity.py`,
  `test_tenant_isolation_management_review.py`.
- Frontend: `nonconformities.spec.ts`, `nonconformity-detail.spec.ts`, `management-reviews.spec.ts`,
  `management-review-detail.spec.ts`, `improvements.spec.ts`, `nonconformity-dashboard.spec.ts`.
