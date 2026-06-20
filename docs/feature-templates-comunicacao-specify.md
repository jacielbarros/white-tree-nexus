# Feature (futura) — Central de Templates de Comunicação

> **Status:** mapeamento (pré-`/speckit.specify`). Documento de design + **prompt de specify pronto**
> ao final. A construção segue pelo fluxo Spec Kit (specify → clarify → plan → tasks → implement).
> Numeração sugerida: **005** (após 004 Gap Analysis), mas pode ser priorizada antes se desejado.

## Motivação

Hoje toda comunicação por e-mail é **hardcoded** em
[`wtnapp/services/notification_service.py`](../wtnapp/services/notification_service.py): convite,
redefinição de senha, atribuição de formulário, lembrete e OTP de assinatura têm assunto e corpo
fixos, em português, iguais para todas as organizações. Isso traz três limitações:

1. **Sem personalização por organização** — cada cliente (tenant) gostaria de ajustar tom, marca e
   texto das mensagens que seus membros/externos recebem.
2. **Sem internacionalização** — corpo fixo em PT; não há PT/EN nem por-org nem por-destinatário.
3. **Mensagens inadequadas a alguns contextos** — exemplo concreto: o convite diz *"use o token para
   aceitar e definir sua senha"* mesmo quando o convidado **já tem conta** (ex.: um Super Admin ou um
   Consultor multi-org). Para esse caso o texto deveria ser *"você foi adicionado à organização X"* —
   sem pedir criação de senha. (Ver também o gap funcional no §"Relação com o fluxo de convite".)

## Escopo da feature

Uma **Central de Templates de Comunicação**: catálogo de mensagens parametrizáveis, com **padrões da
plataforma** (mantidos pelo Super Admin) que cada **organização pode sobrescrever** (mantidos pelo
Admin da org), resolvidos com **placeholders seguros** no momento do envio. Cobre e-mail (canal
inicial), com arquitetura aberta a outros canais no futuro.

### Tipos de template (catálogo inicial)
Cada *tipo* corresponde a um evento de comunicação já existente ou previsto:

| Chave do tipo            | Disparado em                              | Placeholders típicos                              |
|--------------------------|-------------------------------------------|--------------------------------------------------|
| `invite_new_user`        | Convite a e-mail **sem conta**            | `org_name`, `role`, `accept_link`, `expires_at`  |
| `invite_existing_user`   | Convite a e-mail **com conta**            | `org_name`, `role`, `app_link`                   |
| `password_reset`         | "Esqueci a senha"                         | `reset_link`, `expires_at`                       |
| `form_assignment_member` | Atribuição a membro (workflow 003)        | `assignment_title`, `app_link`, `deadline`, `instructions` |
| `form_assignment_external`| Atribuição a externo via token (003)     | `assignment_title`, `respond_link`, `deadline`   |
| `form_reminder`          | Lembrete de formulário pendente (003)     | `assignment_title`, `link`                        |
| `signature_otp`          | OTP de assinatura avançada (003)          | `assignment_title`, `otp_code`, `ttl_minutes`    |
| `signature_request`      | Pedido de assinatura de documento         | `document_title`, `sign_link`, `deadline`        |
| `document_approved`      | Documento controlado aprovado/emitido     | `document_title`, `version`, `app_link`          |

> O catálogo é **extensível**: novos módulos (Riscos, Auditoria…) registram seus tipos. Cada tipo
> declara seus placeholders válidos (allowlist) — o editor só oferece/aceita esses.

### Conteúdo do template
- **Assunto** + **corpo** (texto; HTML opcional numa 2ª iteração).
- **Locale** (`pt-BR`, `en-US`) — seleção por org e/ou por preferência do destinatário (decisão de
  clarify).
- **Placeholders** via sintaxe simples (ex.: `{{org_name}}`), validados contra a allowlist do tipo.
- **Pré-visualização** com dados de exemplo + **envio de teste** para um e-mail do operador.

> **Observação técnica (links nos e-mails).** Hoje os links das mensagens transacionais estão
> **hardcoded** para `http://localhost:4200` em `notification_service.py` (link de aceite de convite
> e link `/respond/{token}` do workflow). Esta feature deve resolver os placeholders de link
> (`accept_link`, `respond_link`, `app_link`, `reset_link`, …) a partir de uma **URL base
> configurável** (ex.: `APP_BASE_URL` por ambiente, com possibilidade de domínio próprio por
> organização no futuro) — nunca `localhost` fixo no código.

### Hierarquia de resolução (qual template usar)
1. Override **ativo da organização** para o tipo+locale, se houver;
2. senão, **padrão da plataforma** para o tipo+locale;
3. senão, **fallback hardcoded** atual (garante que nada quebra se não houver template).

## Fora de escopo (desta feature)
- Canais além de e-mail (SMS, push, webhook) — arquitetura aberta, implementação futura.
- Editor visual rico (WYSIWYG/HTML drag-drop) — começa com texto + placeholders.
- Campanhas/marketing/disparo em massa — isto é **transacional** (1 evento → 1 mensagem).
- A correção do **fluxo de convite para usuário existente** em si (ver abaixo) — pode ser uma
  correção menor independente; esta feature só fornece o *texto* adequado a cada caso.

## Relação com o fluxo de convite (gap funcional correlato)

Mapeado mas **separável**: hoje [accept_invitation](../wtnapp/routers/invitations.py) reaproveita o
usuário por e-mail (não duplica), **porém exige e sobrescreve a senha** mesmo para quem já tem conta,
e não há caminho "aceitar já logado". Recomenda-se uma melhoria (pode ser PR pequeno, antes ou junto
desta feature):
- Se o e-mail do convite pertence a um usuário **já ativo**: aceitar **sem** exigir/alterar senha
  (confirmar vínculo apenas); idealmente um botão "Aceitar" para quem está logado.
- Selecionar `invite_new_user` vs `invite_existing_user` no envio conforme o e-mail já exista —
  exatamente o que esta feature de templates habilita no texto.

## Reuso de primitivos existentes (não reinventar)

| Necessidade                         | Reusar                                                              |
|-------------------------------------|--------------------------------------------------------------------|
| Envio de e-mail                     | [`utils/email.py`](../wtnapp/utils/email.py) + `notification_service` (passa a **renderizar template** antes de enviar) |
| Isolamento por organização          | `helpers/tenant_scope.py` + RLS                                    |
| Quem edita (org vs plataforma)      | RBAC `helpers/permissions.py` (novas perms: `manage_comm_templates`, `manage_platform_templates`) |
| Versão/aprovação (se desejado)      | Padrão **Documento Controlado** (`controlled_document_service`) — opcional p/ trilha de mudanças |
| Auditoria de alterações             | `services/audit_service.py` (append-only)                          |

## Considerações de segurança
- **Nunca** armazenar segredos no template: token/OTP/senha entram **só como placeholder**, resolvidos
  no envio; o conteúdo renderizado com segredo **não** é logado nem auditado (mantém a regra do 003).
- **Allowlist de placeholders** por tipo — impede injeção de variáveis arbitrárias / vazamento de
  dados de outro contexto.
- Sanitização do corpo (especialmente se HTML entrar depois) para evitar injeção.
- **Isolamento de tenant**: override de uma org nunca afeta outra; cross-tenant ⇒ 404 + audit.

## Critérios de aceitação observáveis
- Admin da org edita o texto do convite da **sua** organização; novos convites usam o texto editado;
  outra organização continua com o padrão.
- Super Admin edita o **padrão da plataforma**; orgs sem override passam a usar o novo padrão.
- Convidar um e-mail **já cadastrado** usa a mensagem `invite_existing_user` (sem "defina sua senha").
- Pré-visualização e **envio de teste** funcionam com placeholders resolvidos por dados de exemplo.
- Se uma org não tem override, cai no padrão da plataforma; se nem isso, no fallback atual (nada
  quebra).
- Token/OTP nunca aparecem em logs/auditoria; alteração de template é auditada (quem/quando).
- Org A não vê/edita templates da Org B.

## Decisões em aberto (para `/speckit.clarify`)
1. **Locale**: por organização, por destinatário, ou ambos com precedência?
2. **Versionamento**: templates como Documento Controlado (com aprovação) ou edição direta + auditoria?
3. **HTML**: já nesta feature ou só texto + placeholders, deixando HTML para depois?
4. **Editor de placeholders**: inserção guiada (lista clicável) — confirmar UX mínima.

---

## Prompt pronto para `/speckit.specify`

```
Central de Templates de Comunicação da plataforma SaaS multi-tenant de Gestão de SGSI. Capacidade
TRANSVERSAL: parametrizar o conteúdo (assunto + corpo) de todas as mensagens transacionais que o
sistema envia — convite de usuário (para quem ainda não tem conta E para quem já tem), redefinição
de senha, atribuição de formulário (a membro e a externo via link), lembrete, OTP de assinatura,
pedido de assinatura de documento e notificação de documento aprovado — com extensibilidade para
novos tipos registrados por outros módulos. Roda sobre a fundação multi-tenant; todo template
pertence a uma organização ou é um padrão da plataforma, respeitando o isolamento de tenant
(cross-tenant negado com 404 e auditado).

== Padrões da plataforma x overrides por organização ==
Existe um conjunto de templates PADRÃO mantidos pelo Super Admin da plataforma. Cada organização pode
SOBRESCREVER um template específico para a própria org (sem afetar outras). Na hora de enviar, o
sistema resolve nesta ordem: override ativo da organização (para o tipo+idioma) -> padrão da
plataforma -> fallback embutido no código (garante que nenhuma comunicação quebra se não houver
template configurado).

== Conteúdo e placeholders ==
Cada template tem um TIPO (que indica o evento), um ASSUNTO e um CORPO (texto), e um IDIOMA
(ex.: pt-BR, en-US). O corpo usa PLACEHOLDERS no formato {{variavel}}. Cada tipo declara a lista
permitida de placeholders (allowlist) — ex.: convite usa {{org_name}}, {{role}}, {{accept_link}},
{{expires_at}}. O editor só oferece/aceita placeholders válidos para aquele tipo. O sistema oferece
PRÉ-VISUALIZAÇÃO com dados de exemplo e ENVIO DE TESTE para um e-mail informado pelo operador.

== Links nas mensagens (URL base configurável) ==
Placeholders de link (ex.: accept_link, respond_link, app_link, reset_link) NÃO podem ser construídos
com host fixo no código. Hoje as notificações geram links hardcoded para http://localhost:4200
(aceite de convite e /respond/{token} do workflow); esta feature deve resolvê-los a partir de uma URL
BASE CONFIGURÁVEL por ambiente (ex.: APP_BASE_URL), com possibilidade de domínio próprio por
organização no futuro. A pré-visualização e o envio de teste também usam essa base.

== Papéis e permissões ==
- Editar padrões da plataforma: Super Admin (nova permissão manage_platform_templates).
- Editar overrides da própria organização: Admin da organização (nova permissão
  manage_comm_templates).
- Visualizar: quem administra a organização.

== Segurança ==
Segredos (token de convite, OTP, senha) NUNCA são armazenados no template — entram apenas como
placeholder e são resolvidos no momento do envio; o conteúdo renderizado contendo segredo não é
logado nem auditado. A alteração de um template é auditada (quem/quando), sem expor o conteúdo
sensível. Placeholders fora da allowlist do tipo são rejeitados.

Requisitos observáveis (critérios de aceitação):
- Admin da org edita o texto de um tipo (ex.: convite) e os novos envios DAQUELA org passam a usar o
  texto editado; outra organização continua com o padrão.
- Super Admin edita o padrão da plataforma e organizações sem override passam a usar o novo padrão.
- Convidar um e-mail que JÁ tem conta usa a mensagem de "usuário existente" (sem pedir criação de
  senha); convidar um e-mail sem conta usa a mensagem de "novo usuário".
- Pré-visualização e envio de teste resolvem os placeholders com dados de exemplo.
- Sem override e sem padrão, o envio cai no fallback embutido e a operação não quebra.
- Token/OTP nunca aparecem em logs/auditoria; toda edição de template é auditada.
- Personalizar/editar template na organização A nunca afeta a organização B.

Fora de escopo desta feature:
- Canais além de e-mail (SMS, push, webhook) — arquitetura deve permitir, sem implementar agora.
- Editor visual rico (WYSIWYG) e corpo HTML — começar com texto + placeholders (HTML é evolução).
- Disparo em massa/campanhas de marketing — esta feature é transacional (1 evento -> 1 mensagem).
- A correção do fluxo de aceite de convite para usuário já existente (aceitar sem redefinir senha) é
  uma melhoria correlata, tratada à parte; esta feature apenas fornece o TEXTO adequado a cada caso.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o /speckit.plan,
guiado pela constitution. Reusar, no /plan, os primitivos existentes: serviço de e-mail
(utils/email.py + notification_service como renderizador), RBAC, isolamento de tenant + RLS,
auditoria append-only e, se fizer sentido, o padrão de Documento Controlado para versionar templates.
```
