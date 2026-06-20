# Guia de Testes — Módulo 1 (Diagnóstico e Contexto)

Roteiro de validação manual (E2E) pela interface (`http://localhost:4200`). Cobre a Cláusula 4 do
SGSI: Diagnóstico → Análise de Contexto (4.1) → Partes Interessadas (4.2) → Declaração de Escopo
(4.3) → Visão Consolidada + sugestões, incluindo o ciclo de vida de documento controlado
(rascunho → revisão → aprovação → versões).

> **Por que as telas parecem vazias?** O módulo é orientado a **entrada de dados**: nada é
> pré-preenchido. Em especial, as **sugestões** da Visão Consolidada só aparecem quando o
> **Diagnóstico** indica `dados.dados_pessoais = true`. Com `false` (o padrão), não há sugestões —
> por isso a Visão fica vazia.

---

## 0. Pré-requisitos

1. Serviços no ar (`.\scripts\start.ps1`): backend em `:8000`, frontend em `:4200`.
2. Super Admin criado (`.\.venv\Scripts\python.exe scripts\seed_super_admin.py`) e login feito.
3. Uma **organização** criada em **Organizações** (ex.: *DocBrasil*) e **selecionada** no seletor do
   topo (o header `X-Org-Context`). Sem organização selecionada, as telas do contexto não carregam.

> Dica: o usuário logado é o Super Admin, que tem **bypass de permissão** — então consegue executar
> todas as ações (inclusive **Aprovar**). Para um teste mais realista de papéis, crie em **Usuários**
> um **Admin da organização** (único que normalmente pode aprovar) e um **Consultor** (edita, mas não
> aprova) e repita o roteiro com cada um.

---

## 1. Diagnóstico (o que destrava as sugestões)

A tela **Diagnóstico** é um editor de JSON livre (MVP). Apague o conteúdo e cole **exatamente**:

```json
{
  "dados": {
    "dados_pessoais": true
  },
  "organizacao": {
    "setor": "Tecnologia / SaaS",
    "porte": "media",
    "num_colaboradores": 80
  },
  "ti": {
    "nuvem": true,
    "provedores_criticos": ["AWS", "Cloudflare"]
  },
  "regulacao": {
    "lgpd": true,
    "meta_iso27001": true
  }
}
```

Clique **Salvar rascunho** e depois **Concluir**.

- A única chave com comportamento heurístico hoje é **`dados.dados_pessoais`**. Com `true`, o sistema
  passa a sugerir 2 partes interessadas (**ANPD** e **Titulares de dados pessoais**) na Visão.
- O resto do JSON é texto livre (armazenado como está) — sirva-se para registrar o contexto real.
- **Teste rápido:** volte aqui, troque para `"dados_pessoais": false`, salve, abra a **Visão** → as
  sugestões somem. Volte para `true` → reaparecem.

---

## 2. Análise de Contexto (4.1)

Na tela **Contexto**:

1. **Resultados pretendidos:** `Proteger dados de clientes e garantir continuidade do SaaS, em
   conformidade com a LGPD e a ISO/IEC 27001.`
2. **Metodologia/fontes:** `Análise PESTEL (externo) e SWOT (interno), com base em entrevistas e no
   diagnóstico inicial.`
3. Clique **Salvar**.

### Questões (PESTEL/SWOT) — regra importante

O sistema **valida o par origem × framework**:
- **`external` ⇒ framework `pestel`**
- **`internal` ⇒ framework `swot`**

Combinação trocada (ex.: `external` + `swot`) é **rejeitada (422)** — é um teste negativo válido.

Adicione (botão **Adicionar**) algumas questões:

| Origem    | Framework | Categoria      | Descrição                                              | Impacto |
|-----------|-----------|----------------|--------------------------------------------------------|---------|
| external  | pestel    | Legal          | LGPD/ANPD exigem governança de privacidade             | alto    |
| external  | pestel    | Tecnológico    | Dependência de provedores de nuvem (AWS/Cloudflare)    | medio   |
| internal  | swot      | Forças         | Equipe de segurança dedicada                           | medio   |
| internal  | swot      | Fraquezas      | Inventário de ativos incompleto                        | alto    |

> **Teste negativo:** tente `external` + `swot` → deve recusar com mensagem "Questoes externas usam PESTEL".

---

## 3. Partes Interessadas (4.2)

Na tela **Partes**, cadastre partes interessadas com **Poder** e **Interesse** (alto/medio/baixo). A
**estratégia de engajamento (Mendelow)** é **derivada automaticamente**:

| Poder        | Interesse    | Estratégia derivada      |
|--------------|--------------|--------------------------|
| alto         | alto         | manage_closely (gerir de perto)  |
| alto         | medio/baixo  | keep_satisfied (manter satisfeito) |
| medio/baixo  | alto         | keep_informed (manter informado) |
| medio/baixo  | medio/baixo  | monitor (monitorar)      |

Sugestão de cadastro (confira a coluna **Estratégia** após adicionar):

| Nome                  | Tipo      | Poder | Interesse | Estratégia esperada |
|-----------------------|-----------|-------|-----------|---------------------|
| Alta Direção          | internal  | alto  | alto      | manage_closely      |
| ANPD                  | external  | alto  | medio     | keep_satisfied      |
| Clientes              | external  | medio | alto      | keep_informed       |
| Fornecedor de limpeza | external  | baixo | baixo     | monitor             |

---

## 4. Declaração de Escopo (4.3)

Na tela **Escopo**:

1. **Interfaces e dependências:** `Provedores de nuvem (AWS), gateway de e-mail (SES), integrações
   de pagamento e suporte ao cliente.`
2. **Salvar**.
3. Em **Itens**, adicione **inclusões** e **exclusões** — toda entrada exige **justificativa**:

| Tipo       | Descrição                                  | Justificativa                                   |
|------------|--------------------------------------------|-------------------------------------------------|
| inclusion  | Plataforma SaaS e suporte ao cliente       | Processo core; trata dados de clientes          |
| inclusion  | Infraestrutura em nuvem (AWS)              | Hospeda aplicação e dados                        |
| exclusion  | Rede do escritório físico                  | Sem dados de clientes; risco isolado/segregado  |

> **Referência de versão / obsolescência (avançado):** a Declaração de Escopo pode apontar para as
> **versões aprovadas** de Contexto e Partes. Quando uma nova versão desses artefatos é aprovada
> (passo 6), a referência antiga fica marcada como **desatualizada** (`*_ref_obsolete = true`). Hoje
> esse vínculo é definido via API (`PUT /context/scope` com `context_version_ref`); a sinalização
> aparece no JSON da **Visão**.

---

## 5. Visão Consolidada + Sugestões

Abra a tela **Visão**:

- O bloco superior mostra o **JSON consolidado** (Análise + Partes + Escopo). *(Se aparecer `{}`,
  recarregue com F5 — é o estado inicial antes da resposta.)*
- A tabela inferior lista as **sugestões heurísticas**. Como o Diagnóstico tem
  `dados_pessoais = true`, devem aparecer:
  - **stakeholder-anpd** — *Diagnóstico indica tratamento de dados pessoais.*
  - **stakeholder-titulares** — *Diagnóstico indica tratamento de dados pessoais.*
- Clique **Aceitar** em uma delas → ela é **persistida** como nova parte interessada (vá em **Partes**
  e confirme que "ANPD" / "Titulares de dados pessoais" foi criada, com o requisito LGPD associado).

> **Invariante:** sugestões **nunca** são aplicadas sozinhas — só persistem após **Aceitar** (FR-003).

---

## 6. Ciclo de vida do documento controlado (revisão → aprovação → versões)

Use a tela **Contexto** (mesma mecânica vale para Partes e Escopo):

1. **Enviar para revisão** → o rascunho passa para "em revisão".
2. **Aprovar** → emite a **versão 1 (em vigor)**. Se pedir classificação/natureza da mudança,
   preencha (ex.: *uso_interno* / *Emissão inicial*).
3. Edite algo (ex.: ajuste "Resultados pretendidos"), **Enviar para revisão** de novo e **Aprovar** →
   emite a **versão 2**. A versão 1 vira **superada** (histórico imutável; a "em vigor" é sempre a
   mais recente apontada pelo artefato).
4. Confira o **histórico de versões** na própria tela.

### Testes negativos do ciclo de vida

- **Aprovar sem enviar para revisão** → recusado (**409**: "Envie o artefato para revisao antes de aprovar").
- **Aprovar como Consultor** (se você criou esse usuário) → **403** (falta `approve_context_document`).
- **Append-only:** versões aprovadas **não podem ser editadas/apagadas** (protegido por gatilho no
  banco). Não há ação de UI para isso — é garantido no backend.

---

## 7. Isolamento entre organizações (multi-tenant)

1. Crie uma segunda organização (ex.: *Acme*) e cadastre dados diferentes nela.
2. Alterne no seletor do topo entre *DocBrasil* e *Acme*.
3. Confirme que **cada organização vê apenas os próprios** diagnóstico/contexto/partes/escopo —
   nada vaza entre elas.

---

## 8. E-mail (convites e redefinição de senha)

O envio é **best-effort** (se o SMTP falhar, a operação não quebra; o token vai para o log do
backend). Dispara em dois fluxos: **convite de usuário** (Usuários → convidar) e **redefinição de
senha** (tela "Esqueci a senha").

Para enviar de verdade via **AWS SES** (configurado no `.env`):

- **`SMTP_PASSWORD` deve ser a *senha SMTP do SES* (string longa derivada)**, gerada em
  *SES → SMTP settings → Create SMTP credentials* — **não** é o Access Key ID (`AKIA...`). Se o
  usuário e a senha estiverem com o mesmo valor `AKIA...`, a autenticação no SES vai **falhar**.
- O código usa **STARTTLS na porta 587** (ok para o `email-smtp.*.amazonaws.com`).
- O **remetente** (`EMAIL_FROM`) precisa ser uma **identidade verificada** no SES; em modo sandbox,
  o **destinatário** também precisa estar verificado.

Para validar sem disparar um convite real, você pode testar as credenciais por fora (ex.: `swaks`
ou um script SMTP simples) antes de usar pela UI.

---

## Observações

- O editor de Diagnóstico em JSON cru é intencional para o MVP — formulários guiados entram numa
  iteração futura.
- Padrão de documento controlado (versão/aprovação/classificação/retenção):
  `docs/iso27001-documento-controlado.md`.
- Cobertura automatizada equivalente a este roteiro vive em `wtnapp/test/` (diagnóstico, contexto,
  partes, escopo, versionamento/append-only, classificação, sugestões e isolamento de tenant).
