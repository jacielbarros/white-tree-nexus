# Phase 0 — Research: Diagnóstico e Contexto da Organização

**Feature**: `002-diagnostico-contexto` · **Date**: 2026-06-19

Decisões que resolvem os pontos técnicos do plano. Formato: **Decisão · Justificativa ·
Alternativas**. Reutiliza tudo da fundação 001 (auth, `tenant_scope`, RBAC, auditoria, RLS).

---

## R1. Modelo de "Documento Controlado" — dados de trabalho relacionais + snapshot de versão

**Decisão**: Cada artefato (Análise de Contexto, Mapa de Partes Interessadas, Declaração de Escopo)
tem **dados de trabalho relacionais** (questões, partes, requisitos, itens de escopo) que
representam o **rascunho corrente** editável. Ao **aprovar/emitir**, o sistema congela uma
**versão imutável** em `document_versions` contendo um **snapshot serializado (JSON)** do conteúdo
+ os metadados do padrão "Documento Controlado SGSI" (status, classificação, datas, cadeia de
aprovação, natureza da alteração). O histórico de versões é **append-only**.

**Justificativa**: combina edição relacional ergonômica (consultar/editar questões e partes
individualmente) com imutabilidade de auditoria (a versão aprovada é um snapshot fiel e congelado).
Evita a complexidade de versionar cada linha-filha relacionalmente.

**Alternativas**: (a) versionar todas as tabelas-filhas (event-sourcing/temporal) — rejeitado por
complexidade desproporcional ao MVP; (b) guardar tudo só como JSON sem tabelas relacionais —
rejeitado por perder consulta/validação relacional (ex.: derivação da estratégia por parte).

## R2. "Exatamente uma versão em vigor + rascunho paralelo" (clarify Q1)

**Decisão**: O artefato tem um ponteiro para a **versão em vigor** (última aprovada) e um estado de
**rascunho corrente** (os dados relacionais de trabalho, status rascunho/em revisão). Revisar um
artefato "em vigor" mexe no rascunho corrente; aprovar cria nova versão, atualiza o ponteiro "em
vigor" e marca a versão anterior como **obsoleta/substituída**. Invariante: no máximo **uma** versão
com status "em vigor" por artefato a qualquer instante.

**Justificativa**: cumpre exatamente a decisão de clarify; o SGSI nunca fica sem documento vigente
durante uma revisão; o auditor sempre vê uma versão corrente.

**Alternativas**: voltar o artefato a "em revisão" sem versão vigente (rejeitado — deixa o SGSI sem
documento em vigor); edição que sobrepõe a vigente (rejeitado — perde o "1 vigente estável").

## R3. Cardinalidade: um conjunto por organização (clarify Q4)

**Decisão**: Um `diagnostic` + uma `context_analysis` + um `stakeholder_map` + um `scope_statement`
por organização (unicidade por `tenant_id`). Artefatos pendem diretamente da Organização — sem
entidade intermediária de "escopo/SGSI".

**Justificativa**: caso típico (um SGSI por organização); modelo mais simples. Múltiplos
escopos/unidades podem ser adicionados depois introduzindo uma entidade de agrupamento sem quebrar
o contrato.

**Alternativas**: entidade "SGSI/escopo" com múltiplos conjuntos (adiado — over-engineering p/ MVP).

## R4. Classificação da informação e política de acesso (clarify Q3)

**Decisão**: Cada artefato/versão tem `classificacao` (Público/Uso Interno/Confidencial/Restrito) —
**rótulo de governança**. O acesso é, por padrão, controlado **apenas pelo RBAC**
(`view_context`/`manage_context`/`approve_context_document`). Cada organização **pode** configurar
uma `classification_access_policy` (mapeamento nível→papéis) que, quando presente, **restringe
adicionalmente** a visibilidade por nível. Sem política ⇒ sem restrição extra.

**Justificativa**: ship simples (RBAC-default, um eixo testável) com extensibilidade por org. A
checagem de política, quando existe, é aplicada no `tenant_scope`/dependency de leitura, mantendo o
ponto único de autorização.

**Alternativas**: restrição por classificação obrigatória com mapa fixo papel→nível (rejeitado —
rígido demais p/ MVP); classificação puramente decorativa (rejeitado — o clarify pediu
configurabilidade).

## R5. Diagnóstico-questionário incremental

**Decisão**: `diagnostic` com seções estruturadas (campo JSON por seção: Identificação, Estrutura,
Negócio, Tecnologia, Dados, Cadeia de suprimento, Requisitos) e estado rascunho/concluído.
Auto-save de rascunho; os campos são reutilizados como entradas das análises (pré-preenchimento das
sugestões). O diagnóstico **não** é um documento controlado versionado — é insumo de trabalho.

**Justificativa**: questionário evolui de forma flexível (JSON por seção) e o foco de versionamento
fica nos três artefatos formais (que o auditor exige). Simplicidade + alinhamento à norma.

**Alternativas**: diagnóstico como documento controlado (rejeitado — não é exigido como artefato
versionado; aumentaria escopo).

## R6. Motor de sugestões heurísticas (sem IA)

**Decisão**: `suggestion_service` aplica **regras determinísticas** sobre o diagnóstico (ex.: trata
dados pessoais ⇒ sugerir ANPD/titulares como partes interessadas + requisitos LGPD; usa nuvem ⇒
sugerir provedor como parte interessada e requisitos contratuais). Saída sempre **indicativa**;
nada é persistido em artefato sem o usuário **aceitar explicitamente**.

**Justificativa**: entrega valor sem IA (módulo posterior e opt-in). Regras locais são testáveis,
determinísticas e auditáveis. Falha do motor degrada graciosamente (artefatos seguem editáveis).

**Alternativas**: IA agora (rejeitado — é módulo 10, opt-in por organização); sem sugestões
(rejeitado — o prompt pede o auxílio heurístico).

## R7. Rastreabilidade entre artefatos por referência de versão (FR-009/FR-010)

**Decisão**: A Declaração de Escopo referencia a **versão específica** (não só o artefato) da
Análise de Contexto e do Mapa que a fundamentaram. Quando essas versões deixam de ser "em vigor"
(nova versão aprovada), a referência é **sinalizada como potencialmente desatualizada** (flag
derivada da comparação ponteiro-em-vigor vs. versão referenciada) — sem quebra silenciosa.

**Justificativa**: rastreabilidade verificável e auditável; o auditor consegue ver exatamente quais
versões fundamentaram o escopo. Sinalização (não bloqueio) preserva a usabilidade.

**Alternativas**: referenciar só o artefato (rejeitado — perde a rastreabilidade de versão);
bloquear obsolescência enquanto referenciado (rejeitado — rígido demais).

## R8. RBAC — novas permissões

**Decisão**: adicionar à matriz de `helpers/permissions.py`:
- `view_context` — ver diagnóstico/artefatos (todos os papéis membros por padrão).
- `manage_context` — criar/editar diagnóstico e artefatos (Consultor, Dono de processo, Gestor,
  Admin da organização).
- `approve_context_document` — aprovar/emitir/obsoletar artefatos (**apenas Admin da organização**;
  Super Admin cross-tenant, auditado).

**Justificativa**: cumpre o clarify Q2; reusa o factory `require_permission` e o escopo central.

**Alternativas**: papel de "direção" dedicado (adiado — a fundação não tem; Admin da organização
cobre).

**Status**: NEEDS CLARIFICATION resolvidos. Pronto para Phase 1.
