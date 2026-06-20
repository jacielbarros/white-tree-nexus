# Quickstart — Feature 003 (Motor de Workflow de Preenchimento)

Validação E2E do fluxo atribuir → preencher → assinar → congelar, e do consumo pelo Diagnóstico.
Pré-requisitos: features 001/002 implementadas; um Super Admin/Consultor/Cliente na organização
(ver `scripts/seed_super_admin.py` e a tela de Usuários). Backend `:8000`, frontend `:4200`.

## Cenário A — Atribuir a um membro, preencher, assinar (caminho feliz)

1. **Autoria do template**: `POST /form-templates` `{"kind":"diagnostic","title":"...","schema":[{"label":"Trata dados pessoais?","type":"boolean","required":true}]}`. Ou via futura UI em *Templates*.
2. **Atribuir**: `POST /form-assignments` `{"template_id":"<id>","respondent_user_id":"<cliente_id>","deadline_at":"..."}`. Confira: status `pending`, evento `assigned`, e-mail disparado (log do backend se SMTP estiver no-op).
3. **Assumir**: `POST /form-assignments/{id}/claim` (headers do Cliente) → status `in_progress`, evento `claimed` (com quem/quando).
4. **Preencher com retomada**: `PUT /form-assignments/{id}/answers` parcialmente, repita com dados diferentes → sem perda. `POST /form-assignments/{id}/submit` sem o campo obrigatório → `422`. Preencha e envie → `submitted`.
5. **Assinar**: `POST /form-assignments/{id}/sign` (headers do signatário) → `signed` (política única ⇒ `completed`). Resposta tem `content_hash` (SHA-256, 64 chars), `level=advanced`, `signed_at`.
6. **Verificar integridade**: `GET /form-assignments/{id}/verify` → `{"valid":true,"content_hash":"..."}`. (Tentar UPDATE na versão é bloqueado pelo gatilho append-only.)
7. **Wizard/trilha**: `GET /form-assignments/{id}/events` → lista ordenada de eventos (assigned → claimed → saved → submitted → signed → completed), sem expor as respostas.

## Cenário B — Preenchedor externo via link tokenizado

1. **Atribuir a e-mail externo**: `POST /form-assignments` `{"template_id":"<id>","respondent_email":"externo@exemplo.com"}`. Token gerado (só hash persistido) enviado por e-mail.
2. **Responder pelo link**: `GET /forms/respond/{token}` retorna **apenas** essa atribuição. `POST /forms/respond/{token}/claim` → `in_progress`. `PUT /forms/respond/{token}/answers`. `POST /forms/respond/{token}/submit` → `submitted`.
3. **Assinar com OTP**: `POST /forms/respond/{token}/otp` envia OTP por e-mail (fail-closed — se falhar, 503). `POST /forms/respond/{token}/sign` `{"otp":"123456","signer_name":"Nome"}` → assinatura com `otp_verified=true`. OTP errado/expirado ⇒ `401`.
4. **Isolamento**: token não acessa outra atribuição; token inválido ⇒ `404`; token expirado ⇒ `410`.

## Cenário C — Devolução e cancelamento

1. Com uma atribuição `submitted`, como Consultor: `POST /form-assignments/{id}/return` `{"reason":"Ajuste o campo X"}` → volta a `in_progress`, evento `returned`, preenchedor notificado. Reenvie com `PUT .../answers` + `POST .../submit`.
2. **Cancele** uma atribuição não concluída: `POST /form-assignments/{id}/cancel` → `cancelled`, registrado na trilha. Tentar cancelar de novo ⇒ `409`.

## Cenário D — Contra-assinatura (política dupla)

1. `PUT /form-signature-policy` `{"require_assigner_countersignature":true}` (headers do Admin).
2. Após o preenchedor assinar → `signed` (1 assinatura, papel `filler`). `GET /form-assignments/{id}/signatures` → 1 entrada. O **atribuidor** chama `POST /form-assignments/{id}/sign` → `completed` (2 assinaturas, papéis `filler` + `assigner`).
3. Reverter: `PUT /form-signature-policy` `{"require_assigner_countersignature":false}`.

## Cenário E — Consumo pelo Diagnóstico (1º consumidor)

1. Conclua (assine ou deixe chegar a `completed`) uma atribuição `kind=diagnostic` com respostas. O serviço `diagnostic_intake.apply_diagnostic_intake()` é chamado automaticamente na transição `completed`.
2. Verifique: `GET /context/diagnostic` → `sections["form_intake"]` contém as respostas + `assignment_id` + `completed_at`. O `status` do diagnóstico passa a `completed`.
3. `GET /context/overview` → sugestões heurísticas geradas a partir do diagnóstico (ex.: aviso de ANPD/Titulares quando `dados_pessoais=true`); só persistem após aceite explícito.

## Cenário F — Isolamento de tenant (obrigatório)

1. Crie 2 organizações com dados próprios. Autentique como membro da Org A com `X-Org-Context: <org_a_id>`.
2. Tente `GET /form-templates/<template_org_b_id>` → `404`. `GET /form-assignments/<assignment_org_b_id>` → `404`. `POST /forms/respond/<token_org_b>` → `404`.
3. Confirme no audit log que tentativas cross-tenant são registradas (`operation=READ`, `details.blocked=true`).
4. Coberto pelos testes automatizados em `wtnapp/test/test_tenant_isolation_forms.py`.
