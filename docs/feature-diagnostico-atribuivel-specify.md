# Feature mapeada (backlog) — Diagnóstico atribuível (questionário como workflow)

> **Status:** mapeada, **não** implementada. Quando decidir construir, rode o `/speckit.specify`
> abaixo (cria a feature com branch próprio) e siga o fluxo `clarify → plan → tasks → implement`.
>
> **Base já pronta:** o Módulo 1 (Feature 002) já tem o **diagnóstico-questionário** com um
> **form-builder** na tela (campos parametrizáveis por seção/rótulo/tipo/valor, salvos em
> `diagnostics.sections.campos[]`). Esta feature transforma esse questionário num **fluxo de
> atribuição**: alguém monta/atribui e um respondente preenche.

---

## Prompt para `/speckit.specify`

```
/speckit.specify Diagnóstico atribuível — transformar o diagnóstico-questionário da Cláusula 4
(Feature 002) num workflow de atribuição, sobre a fundação multi-tenant e o módulo de contexto
existentes.

Objetivo: permitir que um Consultor ou Admin da organização monte um questionário (a partir dos
campos parametrizáveis já existentes no diagnóstico) e o ATRIBUA a um respondente para preencher.
O respondente pode ser o papel "Cliente" da organização OU o próprio Consultor (auto-atribuição).
Ao concluir, as respostas consolidam no diagnóstico vigente da organização e seguem alimentando as
sugestões heurísticas da Visão Consolidada (sem aplicação automática — apenas via aceite).

Requisitos de comportamento (o QUÊ, agnóstico de stack):
- Um Consultor/Admin define o conjunto de campos (template) e cria uma ATRIBUIÇÃO do questionário a
  um respondente, com prazo opcional e instruções.
- Estados da atribuição: atribuída → em preenchimento → enviada (concluída); permitir salvar
  parcial e retomar sem perda; permitir reabertura/devolução para ajustes pelo atribuidor.
- O respondente vê apenas o(s) questionário(s) atribuído(s) a ele, preenche os valores dos campos e
  envia. Não pode alterar a estrutura do template (só responde).
- Notificação por e-mail na atribuição e em lembrete/prazo, REUSANDO a infraestrutura de e-mail
  existente (utils/email + notification_service) — best-effort/fail-soft, sem quebrar a operação.
- Consolidação: ao enviar, as respostas atualizam o diagnóstico vigente da organização (o mesmo
  artefato da Feature 002), preservando rastreabilidade de quem respondeu e quando.
- Multi-tenant: toda a atribuição e respostas são escopadas por organização (isolamento estrito,
  cross-tenant ⇒ 404 genérico + auditoria), reusando tenant_scope/RLS da fundação.
- RBAC: novas permissões para atribuir/gerir (assign_diagnostic) e para responder
  (respond_diagnostic). Atribuir: Consultor, Admin da organização. Responder: o respondente
  designado (Cliente ou o próprio Consultor).
- Auditoria: criar/editar template, atribuir, enviar resposta, reabrir e cada notificação geram
  audit log (sem PII/segredos).

Pontos a clarificar (deixar para o /speckit.clarify):
- Respondente externo SEM conta: permitir resposta via link tokenizado (reusando a mecânica de
  convite/aceite) ou exigir que o Cliente seja membro com login? (preferência inicial: link
  tokenizado para Cliente externo, login para Consultor).
- Quantos questionários/atribuições simultâneos por organização (um vigente vs. vários).
- O template é por-organização ou há um catálogo base reutilizável entre organizações.
- Versionamento do template/respostas (a atribuição enviada é imutável? vira documento controlado?).
- Prazo: efeito ao vencer (apenas sinalização vs. bloqueio).

Fora de escopo (evolução futura): lógica condicional entre perguntas (skip logic), múltiplos
idiomas, anexos por resposta, e analytics de preenchimento.
```

---

## Notas de contexto para o `/plan`

- **Reuso máximo:** o campo `diagnostics.sections` (JSON) já comporta o template (`campos[]`); a
  atribuição/respostas devem ser **novas entidades** escopadas por `tenant_id` (não inflar o
  diagnóstico). Reusar `helpers/tenant_scope`, `helpers/permissions`, `services/audit_service` e
  `utils/email`/`services/notification_service`.
- **Respondente externo (Cliente):** a fundação já tem a mecânica de **convite por token + aceite**
  (`invitations`) — é o caminho natural para um link de resposta sem exigir cadastro completo.
- **Não** introduzir AsyncSession; manter o padrão de routers + queries diretas; registrar o novo
  router em `main.py`; migration Alembic + `create_all` para as novas tabelas.
- **Frontend:** o form-builder do diagnóstico vira o **editor de template** (modo configuração) e
  ganha um **modo resposta** (somente valores) para o respondente; nova tela de "Atribuições".
