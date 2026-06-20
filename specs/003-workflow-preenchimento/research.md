# Phase 0 — Research: Motor de Workflow de Preenchimento

Todas as ambiguidades de alto impacto foram resolvidas no `/speckit.clarify` (Session 2026-06-20).
Abaixo, as decisões técnicas consolidadas.

## R1 — Motor genérico vs. específico do diagnóstico

- **Decisão**: motor **genérico** com discriminador `kind` (diagnostic | gap_analysis | generic). O
  Diagnóstico é o 1º consumidor; o Gap Analysis (feature 004) reusa o mesmo motor.
- **Rationale**: o fluxo (atribuir/preencher/assinar/congelar) se repete em várias fases; um motor
  único evita reescrever a máquina de estados e a assinatura por módulo (decisão travada com o usuário).
- **Alternativas**: implementar só no diagnóstico e generalizar depois (YAGNI) — rejeitada por gerar
  retrabalho no Gap Analysis, que já está no roadmap.

## R2 — Vínculo template ↔ atribuição (snapshot)

- **Decisão**: a **atribuição congela um snapshot** do schema de campos do template (clarify Q1);
  mantém também `template_id` (origem). As respostas são chaveadas pelos campos do snapshot.
- **Rationale**: garante integridade/rastreabilidade do que será assinado e evita que editar o template
  altere atribuições em andamento (alinha com Documento Controlado e assinatura avançada).
- **Alternativas**: referência viva (editar template afeta atribuições) — rejeitada por quebrar
  imutabilidade; snapshot + versionamento completo do template — adiado (não exigido no v1).

## R3 — Máquina de estados em service + eventos append-only

- **Decisão**: status enum em `FormAssignment`; transições válidas centralizadas em
  `form_workflow_service.py`. Cada transição grava um `FormAssignmentEvent` (append-only) **e**
  `AuditService.log_from_request`.
- **Rationale**: regra única e testável; o evento append-only alimenta a trilha/wizard (eventos, nunca
  conteúdo). Reusa o padrão de gatilho append-only de `audit_logs`/`document_versions`.
- **Alternativas**: derivar o wizard só da auditoria global — rejeitada (acopla UI ao audit log e
  mistura escopos); estados implícitos por timestamps — rejeitada (transições inválidas não barradas).

## R4 — Respondente externo por link tokenizado

- **Decisão**: reusar o padrão `invitations` — gerar token de alta entropia, persistir **apenas o
  hash (SHA-256)** em `respondent_token_hash`, com expiração; endpoint público resolve por token
  (comparação por hash) e expõe **somente** a atribuição correspondente. Sem conta.
- **Rationale**: já é a mecânica testada da fundação (R7 da 001 — só hash); menor superfície de risco.
  Rate limiting (slowapi) nos endpoints de token.
- **Alternativas**: exigir cadastro do cliente — rejeitada (atrito); token em claro — rejeitada (vaza
  credencial de acesso).

## R5 — Assinatura eletrônica avançada (Lei 14.063/2020)

- **Decisão**: ao assinar, **canonicalizar** as respostas (JSON estável: chaves ordenadas, UTF-8) →
  **SHA-256** = selo de integridade; gravar `FormSignature` (identidade, papel, carimbo de tempo UTC,
  hash, ip/ua) e **congelar versão imutável** via `controlled_document_service` (novo `DocType`
  `form_response` em `document_versions`). Para o **externo**, exigir **OTP por e-mail** no ato
  (clarify Q3): OTP gerado, enviado, e **verificado** (hash com TTL curto) antes de registrar a
  assinatura — **fail-closed** (sem OTP, sem assinatura). Verificação posterior recomputa o hash.
- **Rationale**: atende o nível *avançada* (vínculo único ao signatário + detecção de alteração) sem
  certificados; reusa o padrão de versão imutável e o serviço de e-mail.
- **Alternativas**: ICP-Brasil/qualificada (A1/A3) — fora de escopo (custo/integração); só posse do
  token para externo — rejeitada (vínculo fraco demais para "avançada").

## R6 — Política de assinatura configurável por organização

- **Decisão**: `FormSignaturePolicy` (1 por org): `require_assigner_countersignature` (default
  `false`). Padrão = assinatura única do preenchedor sela; se a org exigir, a **conclusão** (`concluído`)
  só ocorre após a contra-assinatura do atribuidor (clarify Q2). `FormSignature` registra o `signer_role`.
- **Rationale**: honra o "conforme a política da organização" mantendo o caminho simples como default;
  espelha o padrão de `classification_access_policy` (config por tenant no banco, não em `.env`).
- **Alternativas**: sempre única / sempre dupla — rejeitadas (não honram a configurabilidade pedida).

## R7 — Campos obrigatórios e validação de completude

- **Decisão**: cada campo do schema tem `required` (clarify Q4). O **envio** valida que todos os
  obrigatórios do snapshot estão preenchidos; a **assinatura** exige status `preenchido` (envio válido).
  Validação server-side em `form_workflow_service`.
- **Rationale**: padrão de questionário; evita assinar artefato de compliance incompleto.
- **Alternativas**: sem obrigatoriedade — rejeitada (qualidade do artefato); por-template — adiado.

## R8 — Diagnóstico como 1º consumidor (adaptador)

- **Decisão**: `diagnostic_intake.py` mapeia um assignment `kind=diagnostic` assinado/concluído para
  `diagnostics.sections` (formato `campos[]` já existente), tornando-o a fonte do diagnóstico vigente;
  o `suggestion_service` segue lendo `diagnostics.sections` (sem mudança).
- **Rationale**: reuso end-to-end sem reescrever o módulo 002; mantém as sugestões funcionando.
- **Alternativas**: o diagnóstico ler direto do assignment — rejeitada (acopla 002 ao motor; o
  adaptador mantém a fronteira limpa).

## R9 — E-mail (atribuição, lembrete, OTP)

- **Decisão**: estender `notification_service` com `send_form_assignment_email` (link p/ externo ou
  link no app p/ membro), `send_form_reminder_email`, `send_signature_otp_email`. Via `utils.email`
  (best-effort). O OTP de assinatura é gate de segurança (a assinatura externa só conclui com OTP
  verificado), mas a falha de envio **não** corrompe a atribuição — apenas impede a assinatura naquele
  momento.
- **Rationale**: reusa a infra de e-mail (SES) já configurada; mantém o princípio fail-soft de notificação.
- **Alternativas**: OTP por SMS — fora de escopo (novo canal/custo).

## R10 — Permissões e autorização (RBAC + ownership)

- **Decisão**: novas permissões `assign_form` (org_admin, consultant), `view_form` (papéis com acesso
  ao contexto), `fill_form`/`sign_form` (verificadas por **ownership**: o membro designado ou o portador
  do token), via `require_permission` + checagem de designação no router/service.
- **Rationale**: preencher/assinar não é puramente por papel — depende de ser o destinatário; combina
  RBAC com ownership da atribuição.
- **Alternativas**: só RBAC por papel — rejeitada (um Cliente poderia ver/preencher atribuições de outro).
