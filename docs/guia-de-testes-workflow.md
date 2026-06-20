# Guia de Testes — Motor de Workflow de Preenchimento (Feature 003)

Roteiro de validação manual (E2E) pela interface (`http://localhost:4200`). Cobre o fluxo completo:
**Template → Atribuição → Preenchimento → Assinatura eletrônica avançada (Lei 14.063/2020) →
versão imutável**, com trilha append-only/linha do tempo, devolução/cancelamento, política de
assinatura dupla, respondente externo via link tokenizado + OTP, e o consumo pelo Diagnóstico
(Cláusula 4) como primeiro consumidor.

> **Como ler este guia.** O **fluxo de membro** (Cenários 1–2, 4, 6) roda 100% no navegador, sem
> e-mail. O **fluxo externo (token + OTP)** (Cenário 3) **exige e-mail**: o link tokenizado só existe
> na mensagem e o OTP é **fail-closed** (sem entrega de e-mail, a assinatura é bloqueada com `503`).
> Veja o passo 0.3 para subir um *catcher* SMTP local.

---

## 0. Pré-requisitos

### 0.1 Serviços e dados base
1. Serviços no ar (`.\scripts\start.ps1`): backend em `:8000`, frontend em `:4200`, PostgreSQL em
   `:5432` (banco `wtndatabase`).
2. Super Admin criado (`.\.venv\Scripts\python.exe scripts\seed_super_admin.py`) e login feito.
3. Uma **organização** criada em **Organizações** e **selecionada** no seletor do topo
   (header `X-Org-Context`). Sem organização selecionada, as telas não carregam.

### 0.2 Usuários para um teste realista de papéis
Em **Usuários**, convide (ou crie) ao menos:
- um **Admin da organização** (`org_admin`) — atribui, assina, devolve, cancela, define política;
- um **Consultor** (`consultant`) — atribui, preenche, assina;
- um **Cliente** (`client`) — preenche e assina o que lhe é atribuído.

> O Super Admin tem **bypass de permissão** e consegue tudo — bom para um *smoke test* rápido, mas
> use os papéis acima para validar o RBAC de verdade (`assign_form`, `fill_form`, `sign_form`,
> `view_form`).

### 0.3 E-mail local (necessário para o Cenário 3 — externo/OTP)
O envio é **best-effort**. Sem `SMTP_HOST` configurado, **nada é enviado e o token/OTP não aparecem
em lugar nenhum** — então o fluxo externo não é testável. Para testar localmente, suba um *catcher*
SMTP (ex.: **MailHog** ou **smtp4dev**) e aponte o `.env` para ele:

```
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=            # vazio → sem STARTTLS/login (modo catcher)
EMAIL_FROM=no-reply@wtn.local
```

Com isso, o link de atribuição e o código OTP chegam na **UI web do catcher**
(MailHog: `http://localhost:8025`). Reinicie o backend após editar o `.env`.

> Alternativa de produção: AWS SES — `SMTP_PASSWORD` deve ser a *senha SMTP derivada* do SES (não o
> Access Key ID `AKIA...`), porta 587 com STARTTLS, remetente verificado. Ver o guia do Módulo 1.

---

## 1. Autoria do template (Templates)

Abra **Templates** no menu do topo.

1. Clique **Novo template**.
2. **Título:** `Diagnóstico de Contexto` · **Tipo:** `Diagnóstico`.
3. **Adicionar campo** algumas vezes e preencha (a *chave* é gerada automaticamente a partir do
   rótulo ao sair do campo):

| Rótulo                              | Tipo     | Obrigatório |
|-------------------------------------|----------|-------------|
| Razão social                        | Texto    |             |
| Setor de atuação                    | Texto    |             |
| Nº de colaboradores                 | Número   |             |
| A organização trata dados pessoais? | Sim/Não  | ✓ (marque)  |
| Observações                         | Texto longo |          |

4. **Salvar.** O template aparece na lista com a tag de status e a contagem de campos.
5. **Edição:** clique **Editar**, altere algo, **Salvar** novamente.
6. **Arquivar:** o botão **Arquivar** muda o status para *Arquivado* (some das listas de atribuição).

> Atalho: cada template tem um link **Atribuir →** que já abre a tela de Formulários com o template
> pré-selecionado.

---

## 2. Cenário A — Atribuir a um membro, preencher e assinar (caminho feliz)

Abra **Formulários** (ou use o **Atribuir →** do template).

### 2.1 Atribuir (como Admin/Consultor)
1. **Nova atribuição** → selecione o **Template**.
2. Preenchedor: **Membro da org** → escolha o membro no **dropdown** (ex.: o Cliente).
3. (Opcional) defina **Prazo** e **Instruções**.
4. **Atribuir.** A atribuição entra na lista com status **Pendente** e abre o painel de detalhe.
   - Se o e-mail estiver configurado (0.3), chega a notificação "Formulário atribuído" ao membro.

### 2.2 Assumir e preencher (como o membro designado)
1. Faça login como o **membro** (ou troque de usuário). Em **Formulários**, abra a atribuição.
2. **Assumir e preencher** → status muda para **Em preenchimento** (registra quem assumiu e quando).
3. Preencha **parte** dos campos → **Salvar rascunho** → volte para Formulários e reabra:
   **os dados persistem** (retomável, sem perda).
4. **Teste negativo:** deixe o campo obrigatório ("trata dados pessoais?") como está e clique
   **Enviar** sem preencher os demais obrigatórios → toast de **erro (422)** apontando campo
   obrigatório.
5. Preencha o obrigatório e **Enviar** → status **Preenchido**.

### 2.3 Assinar (como signatário autorizado)
1. Na atribuição **Preenchido**, clique **Assinar**.
2. Com a política padrão (assinatura **única**), o status vai direto a **Concluído**.
3. No painel aparece o bloco **Assinaturas** com: nome do signatário, papel (Preenchedor),
   data e o **selo SHA-256** (12 primeiros caracteres).

### 2.4 Integridade e trilha
1. **Verificar integridade** → toast **"Integridade válida ✓"** com o hash.
2. A **Linha do tempo** lista todos os eventos em ordem: `assigned → claimed → saved → submitted →
   signed → completed` — **sem expor o conteúdo das respostas** (só quem/quando).

---

## 3. Cenário B — Preenchedor externo via link tokenizado + OTP

> Requer e-mail local configurado (0.3).

### 3.1 Atribuir a um e-mail externo
1. Em **Formulários** → **Nova atribuição** → Template selecionado.
2. Preenchedor: **Externo (e-mail)** → informe um e-mail (ex.: `externo@exemplo.com`).
3. **Atribuir.** No *catcher* SMTP, abra a mensagem "Formulário atribuído" e **copie o link**
   `http://localhost:4200/respond/<token>`.

> Segurança: no banco fica **apenas o hash** do token (`respondent_token_hash`); o token em claro só
> existe no e-mail.

### 3.2 Responder pelo link (sem login)
1. Abra o link `/respond/<token>` numa aba anônima (sem sessão).
2. **Começar** (assumir) → preencha os campos → **Enviar** (mesma validação de obrigatórios → 422).
3. Vai para a etapa **Assinar**: informe seu **nome** → **Enviar código de verificação**.
4. No *catcher* SMTP, abra "Código de assinatura" e copie o **OTP de 6 dígitos**.
5. Digite o OTP → **Confirmar assinatura** → tela **"✓ Formulário concluído"** com o selo SHA-256.

### 3.3 Testes negativos do externo
- **Token inválido:** abra `/respond/tokeninexistente` → "Link inválido ou expirado".
- **Token expirado** (> 7 dias) → o backend responde `410` (link expirado).
- **OTP errado:** digite um código incorreto → toast **"Falha na assinatura"** (`401`); peça
  **Reenviar código** e tente de novo.
- **OTP esgotado:** após 3 tentativas erradas, o código é invalidado — solicite um novo.

---

## 4. Cenário C — Devolução e cancelamento (como Admin/Consultor)

1. Tenha uma atribuição em **Preenchido** (repita 2.1–2.2 com outro membro/template).
2. No painel, **Devolver** → informe o **motivo** → **Confirmar devolução**. Status volta a
   **Em preenchimento**; evento `returned` (com a nota) entra na linha do tempo; o preenchedor é
   notificado (se e-mail ativo). O membro pode ajustar e reenviar.
3. **Lembrar** → dispara um e-mail de lembrete (toast "Lembrete enviado").
4. **Cancelar** uma atribuição não concluída → status **Cancelado** (registrado na trilha).
   - **Teste negativo:** **Cancelar** de novo a mesma → erro **409** (transição inválida).

---

## 5. Cenário D — Política de assinatura dupla (contra-assinatura)

1. Em **Formulários**, no topo, marque **"Exigir contra-assinatura do atribuidor"** (toast confirma).
2. Crie uma nova atribuição, preencha e **envie** (como o membro).
3. O **preenchedor** assina → status **Assinado** (1 assinatura, papel *Preenchedor*); **não**
   conclui ainda.
4. O **atribuidor** (Admin/Consultor) abre a mesma atribuição e clica **Assinar** → status
   **Concluído** (2 assinaturas: *Preenchedor* + *Atribuidor*).
5. Desligue o toggle para voltar à assinatura única.

---

## 6. Cenário E — Consumo pelo Diagnóstico (1º consumidor)

1. Garanta que existe um **template `kind=diagnostic`** (Cenário 1) com o campo "trata dados
   pessoais?".
2. Atribua, preencha (marque **Sim** em dados pessoais) e **conclua** (assine) — Cenários A ou B.
3. Abra **Diagnóstico** no menu:
   - A seção **"Diagnóstico vigente"** passa a mostrar a **fonte** (form_intake), a data de
     conclusão e as **respostas** do preenchimento assinado — com status **Concluído**.
   - Há um link **"Ver atribuição na linha do tempo →"**.
4. Abra **Visão** (Visão Consolidada): como o diagnóstico indica tratamento de dados pessoais,
   surgem as **sugestões heurísticas** (ANPD / Titulares) — que só persistem após **Aceitar**.

> A tela de **Diagnóstico** não tem mais o editor de campos inline: a autoria virou **Template** e o
> preenchimento vem pelo workflow. A tela agora lista os **templates de diagnóstico** e exibe o
> **vigente**.

---

## 7. Cenário F — Isolamento entre organizações (multi-tenant)

1. Crie uma **segunda organização** e cadastre nela um template/atribuição próprios.
2. Alterne no seletor do topo entre as duas organizações.
3. Confirme que **cada organização vê apenas os próprios** templates, atribuições, eventos e
   assinaturas — nada vaza. Acesso direto a um recurso de outra org responde **404** (sem revelar
   existência) e é auditado.
4. Um **token externo** da Org A só serve à atribuição da Org A.

---

## 8. Observações e limites

- **Rate limiting** nos endpoints públicos (token/OTP): `RATE_LIMIT_FORM_TOKEN` (20/min) e
  `RATE_LIMIT_FORM_OTP` (5/min). Em testes automatizados fica desligado (`RATE_LIMIT_ENABLED=false`).
- **Auditoria:** toda transição sensível (atribuir/assumir/salvar/enviar/devolver/cancelar/assinar/
  concluir) gera log — **sem** PII, token, OTP ou respostas.
- **Append-only:** versões assinadas e eventos da trilha **não podem ser editados/apagados**
  (gatilho no banco). Não há ação de UI para isso — é garantido no backend.
- **Cobertura automatizada** equivalente a este roteiro:
  - Backend: `wtnapp/test/test_form_assignment_lifecycle.py`, `test_form_respond_token.py`,
    `test_form_signature.py`, `test_tenant_isolation_forms.py`, `test_diagnostic_intake.py`
    (37 testes).
  - Frontend: `form-templates.spec.ts`, `form-assignments.spec.ts`, `form-respond.spec.ts`
    (32 testes).
- **Quickstart técnico** (chamadas de API equivalentes): `specs/003-workflow-preenchimento/quickstart.md`.
