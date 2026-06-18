# Prompt para `/speckit.specify` — Feature 1: Fundação multi-tenant

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

Escopo desta feature:
- Cadastro e ciclo de vida de organizações (tenants): criar, ativar, suspender.
- Autenticação de usuários com sessão segura e expiração configurável.
- Papéis: Super Admin da plataforma, Admin da organização, Consultor, Cliente,
  Gestor, Dono de processo, Dono de controle, Auditor interno, Colaborador convidado.
  Um consultor pode atuar em múltiplas organizações; demais papéis são por organização.
- Convite de usuários para uma organização, com atribuição de papel.
- Isolamento de tenant: dado de uma organização nunca é visível ou alterável por
  usuário de outra organização.
- Trilha de auditoria de toda ação sensível (login, mudança de papel, acesso a dado
  de organização, alteração de cadastro).

Requisitos observáveis (critérios de aceitação):
- Um usuário só enxerga e opera dados da(s) organização(ões) à(s) qual(is) pertence.
- Toda tentativa de acesso a dado de outra organização é negada (404/403) e registrada.
- Toda ação sensível gera registro de auditoria imutável, sem expor dados sensíveis.
- Mensagens de erro não vazam detalhes internos (tabela, stack, existência de recurso
  de outro tenant).

Fora de escopo desta feature (virão em specs próprias, nesta ordem de MVP):
Diagnóstico e Contexto da Organização, Gap Analysis, Statement of Applicability,
Plano de Ação, Gestão de Evidências. Depois: Riscos, Auditoria Interna, Revisão pela
Direção, IA, Dashboards avançados.

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```

---

## Sequência sugerida de features (cada uma = um `/speckit.specify`)

1. **Fundação multi-tenant** (este prompt)
2. Módulo 1 — Diagnóstico e Contexto da Organização
3. Módulo 2 — Gap Analysis ISO 27001:2022 (+ seed dos controles do Anexo A, editável)
4. Módulo 4 — Statement of Applicability (SoA)
5. Módulo 5 — Plano de Ação
6. Módulo 6 — Gestão de Evidências
7. Módulo 3 — Gestão de Riscos
8. Módulo 7 — Auditoria Interna
9. Módulo 8 — Revisão pela Direção
10. Módulo 9 — Dashboard Executivo
11. Módulo 10 — Recursos de IA (opt-in por organização)

> Não tente specar vários módulos num único `specify` — uma spec por feature mantém o
> rastreamento requisito→implementação limpo.
