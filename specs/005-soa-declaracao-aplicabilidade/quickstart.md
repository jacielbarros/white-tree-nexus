# Quickstart — Statement of Applicability (SoA)

Roteiro E2E para validar a feature 005 (cenários A–F). Pré-requisitos: fundação (001), Diagnóstico
(002), Gap Analysis (004) implementados; uma organização com **Gap Analysis adotado e avaliado**
(pelo menos alguns controles do Anexo A com status). Backend `:8000`, frontend `:4200`, Postgres do
Docker (`wtndatabase`). Aplicar migrations: `alembic upgrade head`.

## Cenário A — Consolidar a SoA a partir do Gap Analysis (US1)

1. Autenticar como **Consultor/Admin** da org; selecionar a organização (X-Org-Context).
2. `POST /soa/consolidate`.
3. **Esperado**: `GET /soa` retorna ~93 itens (controles do Anexo A), com:
   - `applicable=false` + `exclusion_justification` nos controles que estavam **N/A** no Gap;
   - `implementation_status` mapeado (Atende→implemented, Parcial→in_progress, Não atende→
     not_started, Não avaliado→vazio);
   - `responsible`/`deadline` herdados do Gap quando existirem.
4. Rodar `POST /soa/consolidate` de novo ⇒ **idempotente** (não duplica itens).

## Cenário B — Editar controle e validações (US2)

1. `PUT /soa/items/{id}` marcando `applicable=true` **sem** `inclusion_reasons` ⇒ **422**.
2. `PUT` com `applicable=false` **sem** `exclusion_justification` ⇒ **422**.
3. `PUT` válido (aplicável + `inclusion_reasons=["risk_treatment","legal"]`, status, responsável,
   prazo, `risks_treated="R01, R02"`, `evidence_refs="POL-SI-001"`) ⇒ **200**; muda persiste e gera
   `SoaItemEvent`.

## Cenário C — Divergência e reconciliação (US5)

1. Editar na SoA o `implementation_status` de um controle para um valor diferente do Gap de origem.
2. `GET /soa` ⇒ o controle aparece com bloco `divergence` (`soa_value` ≠ `gap_value`);
   `GET /soa/divergences` lista-o.
3. `POST /soa/items/{id}/reconcile` (campo `implementation_status`) ⇒ aplica o valor vivo do Gap;
   a divergência some. (Reconciliação só por ação explícita.)
4. Confirmar que reconsolidar (`POST /soa/consolidate`) **não** apagou a edição manual antes do passo 3.

## Cenário D — Documento Controlado: revisar e aprovar (US3)

1. Tentar `POST /soa/approve` direto (em `draft`) ⇒ **409**.
2. Deixar um controle aplicável **sem** razão de inclusão; `POST /soa/submit-review` → `POST /soa/approve`
   ⇒ **422** com lista de `ref_code` incompletos.
3. Completar as pendências; `submit-review` → `approve` (como **Admin**) ⇒ **201** com a versão em
   vigor (`version_number=1`).
4. Como **Consultor**, `POST /soa/approve` ⇒ **403**.
5. (Opcional) aprovar com `sign=true` ⇒ dispara assinatura avançada (OTP do Motor 003); a versão fica
   marcada `signed=true`.
6. Verificar imutabilidade: a `DocumentVersion` emitida não pode ser alterada (gatilho append-only).

## Cenário E — Exportar PDF da versão (US4)

1. Editar a SoA depois da aprovação (rascunho diverge da versão).
2. `GET /soa/versions/{id}/export` da versão aprovada ⇒ PDF (`application/pdf`) com o conteúdo **da
   versão**, não do rascunho.
3. Conferir cabeçalho do Documento Controlado (identificador `SGSI-DOC-SOA`, versão, classificação,
   datas, aprovador) e a tabela dos controles.
4. A exportação gera registro de auditoria.

## Cenário F — Isolamento de tenant (obrigatório)

1. Como usuário da **Org B**, tentar `GET /soa`, `PUT /soa/items/{id}` ou
   `GET /soa/versions/{id}/export` de recursos da **Org A** ⇒ **404/403** (sem revelar existência) +
   audit log.
2. Consultor multi-org operando no contexto da Org A só vê a SoA da Org A.

## Frontend (telas)

- `/app/soa` — matriz dos 93 controles por tema; editar (dialog), consolidar, badges de divergência +
  reconciliar.
- `/app/soa-versions` — enviar p/ revisão, aprovar (+assinatura opcional), listar versões, exportar PDF.

## Checklist de saída

- [ ] `pytest wtnapp/test/test_soa*.py wtnapp/test/test_tenant_isolation_soa.py` verde.
- [ ] `npm test` (specs das telas `soa`/`soa-versions`) verde.
- [ ] `alembic upgrade head` idempotente no Postgres (tabelas já criadas pelo `create_all()`).
- [ ] Consolidação, edição, divergência, aprovação e exportação auditadas, sem PII/conteúdo sensível.
