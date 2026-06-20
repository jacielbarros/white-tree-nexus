# Feature 003 — Motor de Workflow de Preenchimento (atribuível + assinável)

> **Capacidade transversal** (como o [Documento Controlado SGSI](iso27001-documento-controlado.md)):
> não é um módulo de fase, e sim o **fluxo reutilizável** que envolve qualquer formulário
> preenchível — **Diagnóstico** (1º consumidor) e **Gap Analysis** (próximo), e futuras fases
> (revisão pela direção, auditoria interna). Roda sobre a fundação multi-tenant (001) e o módulo de
> contexto (002).
>
> **Sequência decidida:** Feature **003** = este motor + diagnóstico atribuível · Feature **004** =
> Gap Analysis já nasce usando o motor. (Quando construir, isto reordena Gap Analysis para a
> feature-branch 004; a identidade de módulo no roadmap não muda.)

## Decisões travadas

| Decisão | Escolha |
|---|---|
| Arquitetura | **Motor reutilizável** (template → atribuição → preenchimento → assinatura → snapshot) |
| Respondente | **Membro logado** (Cliente/Consultor — inclusive o próprio) **ou externo via link tokenizado** |
| Assinatura | **Avançada** (Lei 14.063/2020): identidade + carimbo de tempo + hash SHA-256 + trilha. **Sem ICP-Brasil** |
| Sequência | 003 = motor + diagnóstico · 004 = Gap Analysis consome o motor |

## Máquina de estados

`rascunho` (consultor monta) → `pendente` (atribuído; e-mail enviado) → `em_preenchimento`
(preenchedor **assume**) → `preenchido` (enviado) → `assinado` (congela snapshot imutável) →
`concluído`. Mais `devolvido` (consultor devolve p/ ajuste → volta a `em_preenchimento`) e
`cancelado`. **Cada transição** registra autor + carimbo de tempo (UTC). A visão **wizard/linha do
tempo** é a projeção dessa máquina + da trilha — não é estrutura nova.

## Reuso (não reinventar) — primitivos da fundação

| Necessidade | Reusar |
|---|---|
| Link tokenizado p/ externo (só o **hash**, expiração, status) | padrão `invitations` (`wtnapp/models/invitation_model.py`) |
| Snapshot imutável assinado | `services/controlled_document_service.py` + `document_versions` (append-only); estender `DocType` |
| Trilha imutável de **eventos** (nunca o conteúdo/PII) | `services/audit_service.py` |
| E-mail (atribuição + lembrete) | `services/notification_service.py` + `utils/email.py` |
| RBAC (atribuir / preencher / assinar) | `helpers/permissions.py` (+ `assign_form`, `fill_form`, `sign_form`, `view_form`) |
| Isolamento por tenant | `helpers/tenant_scope.py` + RLS |
| Autoria do template (campos) | **form-builder** já feito em `wtnadmin/src/app/pages/diagnostic/diagnostic.ts` |

**Assinatura avançada (14.063/2020):** ao assinar, canonicaliza as respostas (JSON estável) →
**SHA-256** → grava a assinatura (identidade, timestamp UTC, hash, ip/ua) **e** cria um
`document_version` imutável. Verificação recomputa o hash e compara (alteração posterior é
detectável). Nível *qualificada* (certificado ICP-Brasil A1/A3) fica como evolução futura.

**Entidades novas (a detalhar no `/speckit.plan`):** `FormTemplate` (kind + schema de campos),
`FormAssignment` (instância do workflow: respondente membro **ou** token, status, prazos, respostas,
content_hash, ponteiro da versão assinada), `FormAssignmentEvent` (trilha append-only → wizard),
`FormSignature` (assinatura avançada, append-only).

---

## Prompt para `/speckit.specify`

```
Motor de Workflow de Preenchimento (atribuível e assinável) da plataforma SaaS multi-tenant de
Gestão de SGSI. É uma capacidade TRANSVERSAL e REUTILIZÁVEL: o mesmo fluxo envolve qualquer
formulário preenchível de fase — o Diagnóstico (Cláusula 4, já existente) é o primeiro consumidor e
o Gap Analysis será o próximo. Roda sobre a fundação multi-tenant e o módulo de contexto existentes;
todo dado pertence a uma organização e respeita o isolamento de tenant (acesso cross-tenant negado
com 404/403 sem revelar existência, e auditado).

== Template parametrizável ==
Um Consultor ou Admin da organização monta/edita um TEMPLATE de formulário (conjunto de campos por
seção, com rótulo e tipo — texto, sim/não, número, seleção). O template tem um "tipo" que indica a
qual fase ele serve (diagnóstico, gap analysis, genérico). Personalizar o template de uma
organização nunca afeta outra organização.

== Atribuição ==
O Consultor/Admin cria uma ATRIBUIÇÃO de um template a um PREENCHEDOR, com prazo opcional e
instruções. O preenchedor pode ser:
- um membro da organização (papel Cliente ou Consultor — inclusive o próprio que atribuiu), ou
- um respondente EXTERNO, convidado por LINK com token (sem exigir conta), reusando a mecânica de
  convite (apenas o hash do token é guardado; o link expira).
Ao atribuir, o preenchedor recebe NOTIFICAÇÃO POR E-MAIL (e lembrete) — entrega best-effort, sem
quebrar a operação.

== Ciclo de vida (máquina de estados) ==
rascunho (consultor monta) -> pendente (atribuído; e-mail enviado) -> em preenchimento (o
preenchedor ASSUME) -> preenchido (enviado) -> assinado -> concluído. Além de: devolvido (o
atribuidor devolve para ajustes, voltando a "em preenchimento") e cancelado. O preenchedor pode
salvar parcialmente e retomar sem perda. Cada transição registra QUEM e QUANDO (carimbo de tempo).

== Assinatura eletrônica avançada (Lei nº 14.063/2020) ==
Após o preenchimento, o formulário pode ser ASSINADO eletronicamente no nível "avançada": vincula a
identidade do signatário, registra carimbo de tempo, e gera um selo de integridade (hash do conteúdo
preenchido) que torna detectável qualquer alteração posterior. A assinatura congela uma VERSÃO
IMUTÁVEL do formulário preenchido (reusa o padrão de Documento Controlado SGSI). Não há integração
com certificado digital ICP-Brasil nesta feature (nível "qualificada" é evolução futura).

== Trilha e visão em wizard ==
Todo o histórico do fluxo é preservado de forma imutável (atribuição, notificações, assunção,
salvamentos, envio, devolução, assinatura, conclusão) — uma TRILHA append-only por atribuição que é
exibida como uma LINHA DO TEMPO / WIZARD dos passos. A trilha registra os EVENTOS (quem/quando), não
o conteúdo sensível das respostas.

== Papéis e permissões ==
- Atribuir/gerir/devolver/cancelar: Consultor e Admin da organização.
- Preencher e enviar: o preenchedor designado (membro) ou o portador do link tokenizado.
- Assinar: o preenchedor e/ou o atribuidor, conforme a política da organização.
- Visualizar: usuários da organização com permissão; respondente externo vê apenas o que lhe foi
  atribuído, pelo link.

== Consumo pelo Diagnóstico (1º consumidor) ==
O Diagnóstico de Contexto (Cláusula 4) passa a ser preenchido por este fluxo: o preenchimento
assinado torna-se a fonte do diagnóstico vigente da organização e segue alimentando as sugestões
heurísticas da visão consolidada (sem aplicação automática — só via aceite).

Requisitos observáveis (critérios de aceitação):
- Uma atribuição e suas respostas só são visíveis/editáveis por quem tem direito (atribuidor,
  preenchedor designado, ou portador do token); acesso cross-tenant é negado (404/403) e auditado.
- O preenchedor é notificado por e-mail ao ser atribuído; ao "assumir", o status muda para "em
  preenchimento" e fica registrado quem assumiu e quando.
- O preenchimento pode ser salvo parcialmente e retomado sem perda de dados.
- Ao assinar, gera-se um selo de integridade do conteúdo e uma versão imutável; recomputar o selo
  sobre o conteúdo assinado confere, e qualquer alteração posterior é detectável.
- A trilha do fluxo é completa e imutável e é apresentável como linha do tempo/wizard.
- Personalizar/atribuir na organização A nunca afeta a organização B.
- Toda transição sensível (atribuir, notificar, assumir, enviar, devolver, assinar, cancelar) gera
  registro de auditoria, sem PII/segredos.

Fora de escopo desta feature:
- Assinatura QUALIFICADA com certificado digital ICP-Brasil (A1/A3) — evolução futura.
- O conteúdo específico de fases além do diagnóstico (a matriz do Gap Analysis vem na feature 004,
  consumindo este motor).
- Upload de arquivos de evidência (Módulo de Evidências).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto. Reusar, no /plan, os primitivos existentes:
mecânica de convite (token), Documento Controlado/versões imutáveis, auditoria append-only, serviço
de e-mail, RBAC e isolamento de tenant.
```
