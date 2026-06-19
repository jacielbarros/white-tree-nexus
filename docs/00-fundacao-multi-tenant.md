# Prompt para `/speckit.specify` — Feature 0: Fundação multi-tenant

Cole o bloco abaixo no `/speckit.specify`. É **agnóstico de stack** de propósito —
a stack (FastAPI + Angular) vem do `/speckit.plan`, guiado pela constitution.

Esta deve ser a **primeira** feature: é a espinha de que todos os módulos dependem.

---

```
Plataforma SaaS multi-tenant de Gestão de SGSI e Compliance ISO/IEC 27001:2022,
para consultores, empresas e auditores conduzirem a jornada de implementação do SGSI.

Esta primeira feature estabelece a FUNDAÇÃO sobre a qual todos os módulos serão
construídos: gestão de organizações (tenants), autenticação, controle de acesso por
papéis (RBAC), isolamento de dados entre organizações e trilha de auditoria.
Nenhum módulo de negócio entra aqui — só a base.

Escopo desta feature:
- Cadastro e ciclo de vida de organizações (tenants): criar, ativar, suspender, reativar.
- Bootstrap da plataforma: criação do primeiro Super Admin da plataforma.
- Autenticação de usuários com sessão segura, expiração configurável, logout que
  encerra a sessão, e bloqueio após tentativas sucessivas de login malsucedidas.
- Fluxo de definição/redefinição de senha.
- Papéis: Super Admin da plataforma, Admin da organização, Consultor, Cliente,
  Gestor, Dono de processo, Dono de controle, Auditor interno, Colaborador convidado.
  Um Consultor pode atuar em múltiplas organizações; os demais papéis são por organização.
  Apenas o Super Admin da plataforma é cross-tenant.
- Convite de usuários para uma organização, com atribuição de papel, aceite e expiração
  do convite.
- Isolamento de tenant: dado de uma organização nunca é visível, listável ou alterável
  por usuário de outra organização.
- Trilha de auditoria de toda ação sensível (login, logout, falha de login, convite,
  mudança de papel, criação/alteração de organização ou usuário, tentativa de acesso
  cross-tenant).

Requisitos observáveis (critérios de aceitação):
- Um usuário só enxerga e opera dados da(s) organização(ões) à(s) qual(is) pertence.
- Toda tentativa de acesso a dado de outra organização é negada (404/403, sem revelar
  a existência do recurso) e registrada em auditoria.
- O Super Admin da plataforma pode operar entre organizações, mas todas as suas ações
  são auditadas — não há bypass de auditoria.
- Toda ação sensível gera registro de auditoria imutável (append-only), sem expor
  senhas, tokens, chaves ou PII.
- Mensagens de erro não vazam detalhes internos (tabela, stack, existência de recurso
  de outro tenant).
- Permissões são verificadas por papel; um usuário sem a permissão necessária é negado
  e o evento é auditado.

Fora de escopo desta feature (virão em specs próprias, nesta ordem de MVP):
Diagnóstico e Contexto da Organização, Gap Analysis, Statement of Applicability,
Plano de Ação, Gestão de Evidências. Depois: Riscos, Auditoria Interna, Revisão pela
Direção, IA, Dashboards avançados.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```

---

## Sequência sugerida de features (cada uma = um `/speckit.specify`)

Ver `docs/README.md` para a lista completa com os arquivos de prompt correspondentes.
Regra de ouro: **uma spec por feature** — não tente specar vários módulos num único
`specify`, senão o rastreamento requisito→implementação vira sopa.
