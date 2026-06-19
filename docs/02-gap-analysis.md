# Prompt para `/speckit.specify` — Módulo 2: Gap Analysis ISO/IEC 27001:2022

Pré-requisitos: Fundação multi-tenant e Módulo 1 (Diagnóstico) especificados.
Esta feature introduz o **seed editável dos controles do Anexo A** — base para SoA.
Agnóstico de stack.

---

```
Módulo de Gap Analysis ISO/IEC 27001:2022 da plataforma SaaS multi-tenant de Gestão
de SGSI. Permite avaliar a aderência da organização aos controles do Anexo A
(ISO/IEC 27001:2022, 93 controles em 4 temas: Organizacional, Pessoas, Físico,
Tecnológico) e gerar lacunas e plano de remediação.

Esta feature roda sobre a fundação multi-tenant e o módulo de Diagnóstico já existentes.
Todo dado respeita o isolamento de tenant.

Escopo desta feature:
- Catálogo-base dos controles do Anexo A 2022 fornecido como dado inicial (seed) da
  plataforma: cada controle com identificador, título, tema e descrição. O catálogo-base
  é mantido pela plataforma, mas cada organização pode personalizar sua cópia (renomear,
  adicionar controles próprios, marcar controles como não aplicáveis) sem afetar outras
  organizações nem o catálogo-base.
- Matriz de gap analysis por organização: para cada controle, registrar:
  - Aplicável ou não aplicável.
  - Status de implementação: implementado, parcialmente implementado, não implementado.
  - Justificativa.
  - Evidências existentes e evidências pendentes (referência textual nesta fase; o
    vínculo com arquivos reais vem no módulo de Evidências).
  - Responsável.
  - Prazo.
  - Nível de maturidade.
  - Ações necessárias.
  - Observações.
- Geração automática de: lista de lacunas (controles aplicáveis não/parcialmente
  implementados), visão percentual de aderência (geral e por tema), e insumo para um
  plano de remediação.

Requisitos observáveis (critérios de aceitação):
- A matriz de uma organização só é visível/editável por usuários dela com permissão;
  acesso cross-tenant é negado e auditado.
- Personalizar o catálogo de uma organização nunca altera o de outra nem o seed-base.
- O percentual de aderência é calculado de forma consistente com os status registrados
  e considera apenas controles aplicáveis.
- Alterações em itens da matriz geram histórico e registro de auditoria.
- O seed dos 93 controles está completo e é versionável (atualização da norma não
  apaga avaliações já feitas).

Fora de escopo desta feature:
- Declaração de Aplicabilidade formal (módulo SoA, próximo).
- Upload e versionamento de arquivos de evidência (módulo de Evidências).
- Cálculo de risco (módulo de Riscos).

NÃO especificar tecnologia/stack nesta spec — decisões de implementação ficam para o
/speckit.plan, guiado pela constitution do projeto.
```
