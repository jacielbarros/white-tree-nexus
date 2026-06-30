# Quickstart — Evidências Transversais + Auditoria Interna (Feature 014 / 5a)

Roteiro de validação E2E (browser + Postgres real). Pré-requisitos: backend `:8000`, frontend
`:4200`, `.env` com `DATABASE_URL`, `FIELD_ENCRYPTION_KEY` (Fernet) e `EVIDENCE_STORAGE_DIR`. Login
como Admin da organização (tem `manage_evidence` + `manage_internal_audit` + `approve_audit_report`).

## 0. Migração (idempotente, resolve os 2 heads)
```bash
alembic upgrade head      # cria evidence_*/internal_audit_*; migra gap_evidence* → evidence*
pytest wtnapp/test/test_evidence_migration_008.py   # regressão da migração
```
Confirme: evidências antigas do Gap aparecem agora com `evidence_link(target_type=gap_item)` e os
endpoints `/gap/assessment/items/{id}/evidences` continuam respondendo igual.

## 1. Evidência transversal (P1)
1. Abra um **controle da SoA** → seção "Evidências anexadas" → **Anexar**: arquivo PDF,
   classificação `uso_interno`, confirmar. A evidência aparece com autor/data/tamanho/hash.
2. Repita em um **risco**, um **ativo** e um **item do Gap** (este último pela tela do Gap, contrato
   inalterado). Cada evidência fica no artefato correto.
3. Tente anexar arquivo vazio / extensão não permitida / acima de `EVIDENCE_MAX_FILE_BYTES` → recusa
   com mensagem clara, sem criar evidência.
4. Anexe uma evidência **confidencial**; como usuário só com `view_evidence`, o **download** é negado
   (403), metadados visíveis.

## 2. Repositório central (P2)
1. Abra **Repositório de Evidências** → veja todas as evidências do tenant com contagem de vínculos.
2. Filtre por classificação / tipo de artefato / autor / data / estado → resultado coerente.
3. Abra uma evidência → **Vincular** a um segundo artefato → confirme que agora ela aparece nos dois.
4. Filtro `status=inactive` só retorna resultados com `manage_evidence`.

## 3. Cadeia de custódia (P2)
1. **Substituir** uma evidência por nova versão (classificação obrigatória) → versão anterior fica no
   histórico (`manage_evidence`), versão corrente identificada, hash por versão.
2. **Inativar** uma evidência → some das listas padrão, permanece no histórico; arquivo não é apagado.
3. Verifique a trilha de custódia: `uploaded`/`replaced`/`inactivated`/`linked`/`downloaded` sem
   conteúdo/`storage_key` nos detalhes.

## 4. Auditoria interna (P3)
1. **Programa de auditoria** → criar (objetivo + período).
2. **Auditoria** → criar com escopo, critérios, **auditor interno** (membro), datas → nasce
   `planned`, código `AUD-####`.
3. **Checklist** → adicionar itens manuais (vinculados a controle/cláusula/risco) e usar **Importar do
   escopo (SoA/Gap)**.
4. **Iniciar** (→ `in_progress`); tentar concluir duas vezes → 2ª transição inválida (409).

## 5. Constatações (P3)
1. Registrar uma constatação de **cada tipo** (conforme / NC maior / NC menor / oportunidade /
   observação), com vínculo a controle/cláusula/risco.
2. Anexar evidência (do repositório) a uma constatação → `evidence_link(target_type=audit_finding)`.
3. Confirme: NC maior/menor ficam `promotable=true` com `nonconformity_ref` vazio; demais tipos não.
4. Concluir a auditoria (→ `completed`).

## 6. Relatório de auditoria (P4)
1. **Gerar relatório** → rascunho consolidando escopo/critérios/itens/constatações.
2. **Submeter à revisão**; tente aprovar com auditoria incompleta → **gate duro** bloqueia (409).
3. **Aprovar** (com e sem **assinatura** avançada/OTP) → versão imutável; **Exportar PDF** com rótulos,
   tipos de constatação, vínculos e evidências referenciadas.

## 7. Timeline + dashboards (P5)
1. Em um controle/risco/ativo → **Timeline**: evidências + constatações + eventos em ordem
   cronológica, só metadados.
2. **Dashboard do módulo**: evidências por status/classificação, auditorias por status, constatações
   por tipo.
3. **Dashboard de Conformidade**: card desta etapa reflete o readiness (auditoria concluída/relatório
   aprovado).

## 8. Isolamento de tenant (obrigatório)
1. Como usuário da Org A, tente `GET /evidence/{id}` de evidência da Org B → 404 genérico + audit.
2. Idem para auditoria/constatação/relatório/timeline da Org B → 404, sem revelar existência.
3. Consultor multi-org no contexto A nunca vê dados de B; consolidação/timeline nunca agregam B.
4. Rodar: `pytest wtnapp/test/test_tenant_isolation_evidence.py
   wtnapp/test/test_tenant_isolation_internal_audit.py`.

## Suítes de teste (planejadas)
- Backend: `test_evidence_repository.py`, `test_evidence_links.py`, `test_evidence_custody.py`,
  `test_evidence_migration_008.py`, `test_internal_audit_lifecycle.py`, `test_internal_audit_findings.py`,
  `test_internal_audit_report.py`, `test_traceability_timeline.py`, `test_audit_metrics.py`,
  `test_tenant_isolation_evidence.py`, `test_tenant_isolation_internal_audit.py`.
- Frontend: `evidence-panel.spec.ts`, `evidence-repository.spec.ts`, `internal-audit.spec.ts`,
  `internal-audit-detail.spec.ts`, `internal-audit-dashboard.spec.ts` + regressão do Gap.
