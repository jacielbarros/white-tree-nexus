# Padrão transversal: "Documento Controlado SGSI" (ISO/IEC 27001:2022, cláusula 7.5)

**Definição canônica** do padrão de *informação documentada controlada* da plataforma. É
**transversal**: referenciado pelos prompts dos Módulos 1–4 e **realizado** como capacidade no
Módulo 5 (Gestão de Evidências / Informação Documentada). Candidato natural a virar uma **feature
de fundação própria** (Gestão de Informação Documentada) — conecta ao Princípio IV da constitution
(integridade e versionamento).

> **Por que existe:** todo artefato de um SGSI auditável (Análise de Contexto, Mapa de Partes
> Interessadas, Declaração de Escopo, SoA, políticas, procedimentos, registros/evidências) é
> "informação documentada" controlada pela cláusula 7.5. Os campos abaixo se repetem em todos —
> não devem ser reinventados por módulo.

## Campos obrigatórios de um documento controlado

- **Identificador estável** (padrão configurável por organização, ex.: `SGSI-DOC-002`, `POL-SI-001`,
  `PROC-DOC-001`), **título** e **tipo**: Documento (prescritivo — política/procedimento/manual) ou
  Registro (evidencial).
- **Versão** + **histórico de versões append-only**: para cada versão, data, autor, natureza da
  alteração e aprovador. Nunca editado/apagado; alteração relevante gera nova versão.
- **Status no ciclo de vida**: rascunho → em revisão → aprovado/em vigor → (revisão periódica) →
  obsoleto/substituído → retido → descartado. Cada transição é auditada.
- **Classificação da informação**: Público | Uso Interno | Confidencial | Restrito.
- **Datas**: emissão e **próxima análise crítica** (revisão periódica — no mínimo anual e/ou a
  cada mudança significativa).
- **Cadeia de aprovação rastreável**: elaborado por, revisado por, aprovado por (quem e quando);
  aprovar/publicar exige o papel autorizado.
- **Referências cruzadas** a outros documentos do SGSI (rastreabilidade entre artefatos).
- **Referências normativas** aplicáveis (cláusulas ISO 27001/27002, ISO 31000/27005, LGPD, etc.).
- **Retenção e descarte** (para registros/evidências): período de retenção (considerando
  obrigações legais, ex.: LGPD) e descarte seguro auditado — o registro do descarte é preservado
  de forma imutável mesmo quando o arquivo é removido.

## Invariantes (alinhadas à constitution)

- Todo documento controlado é **escopado por tenant** (isolamento; cross-tenant ⇒ 404/403 + audit).
- Histórico de versões e registro de descarte são **append-only** (nunca editar/apagar).
- Conteúdo confidencial **nunca** aparece em logs, auditoria, telemetria ou mensagens de erro.
- Acesso por **papel e por classificação** da informação.

## Como citar nos prompts de módulo

Cada prompt `/speckit.specify` deve permanecer **autossuficiente** ao ser colado. Portanto, inclua
no bloco do prompt uma versão **concisa** do padrão (os campos-chave acima) e aponte para esta
definição canônica. Bloco curto sugerido para colar dentro do prompt:

```
Os artefatos deste módulo são "documentos controlados" (ISO 27001 cl. 7.5): identificador estável,
versão + histórico append-only (data/autor/alteração/aprovador), status no ciclo de vida
(rascunho→em revisão→aprovado/em vigor→obsoleto→retido→descartado), classificação (Público/Uso
Interno/Confidencial/Restrito), datas de emissão e próxima análise crítica, cadeia
elaborado/revisado/aprovado, referências cruzadas e normativas. Definição canônica:
docs/iso27001-documento-controlado.md. A capacidade de versionamento/aprovação/classificação/
retenção é realizada pelo Módulo 5 (Gestão de Evidências / Informação Documentada).
```
