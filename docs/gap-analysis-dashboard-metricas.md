# Guia de metricas do Dashboard do Gap Analysis

Este documento define a regra de leitura dos indicadores exibidos em
`/app/gap-dashboard`.

O objetivo e evitar uma interpretacao equivocada: uma organizacao pode ter 100%
de aderencia entre os itens ja avaliados, mas ainda ter baixa cobertura da
matriz se a maior parte dos controles estiver como "Nao avaliado".

## Status considerados

| Status | Peso na aderencia | Entra como avaliado? | Observacao |
|---|---:|---:|---|
| Atende | 1.0 | Sim | Controle considerado aderente. |
| Parcialmente atende | 0.5 | Sim | Controle parcialmente aderente. |
| Nao atende | 0.0 | Sim | Controle avaliado sem aderencia. |
| N/A | Fora do denominador | Sim | Decisao registrada de nao aplicabilidade. |
| Nao avaliado | 0.0 no indicador conservador | Nao | Ausencia de avaliacao/evidencia. |

## Indicadores exibidos

### 1. Aderencia dos avaliados

Mede a qualidade dos controles ja avaliados e aplicaveis.

Formula:

```text
(Atende * 1.0 + Parcialmente * 0.5 + Nao atende * 0.0)
/ (Atende + Parcialmente + Nao atende)
```

Regras:

- `Nao avaliado` fica fora do denominador.
- `N/A` fica fora do denominador.
- Se nao houver nenhum item avaliado e aplicavel, exibir `-`.

Uso correto:

- Responde: "Dos itens que ja foram avaliados e aplicaveis, qual e o nivel de
  aderencia?"
- Nao responde: "A organizacao esta 100% conforme em toda a matriz?"

### 2. Completude da avaliacao

Mede quanto da matriz ja recebeu alguma decisao de avaliacao.

Formula:

```text
(Total de itens - Nao avaliado) / Total de itens
```

Regras:

- `N/A` conta como avaliado, porque houve uma decisao registrada.
- `Nao avaliado` nao conta como avaliado.

Uso correto:

- Responde: "Quanto da matriz ja foi preenchido?"
- Deve sempre ser analisado junto com a aderencia dos avaliados.

### 3. Conformidade consolidada

Indicador conservador para leitura executiva. Trata itens nao avaliados como
ausencia de comprovacao de aderencia.

Formula:

```text
(Atende * 1.0 + Parcialmente * 0.5)
/ (Total de itens - N/A)
```

Regras:

- `Nao atende` vale 0.
- `Nao avaliado` vale 0.
- `N/A` fica fora do denominador.
- Se todos os itens forem `N/A`, exibir `-`.

Uso correto:

- Responde: "Considerando a matriz como um todo e tratando itens nao avaliados
  como zero comprovacao, qual e a conformidade consolidada?"
- E o indicador mais prudente para comunicacao executiva quando a avaliacao
  ainda esta incompleta.

## Exemplos

### Exemplo A: DocBrasil

Distribuicao:

| Status | Quantidade |
|---|---:|
| Atende | 2 |
| Parcialmente atende | 0 |
| Nao atende | 0 |
| N/A | 0 |
| Nao avaliado | 99 |
| Total | 101 |

Calculos:

```text
Aderencia dos avaliados = 2 / 2 = 100%
Completude da avaliacao = 2 / 101 = 2%
Conformidade consolidada = 2 / 101 = 2%
```

Leitura correta:

> Os controles ja avaliados estao todos aderentes, mas a matriz ainda esta
> apenas 2% preenchida. Portanto, nao se deve interpretar o 100% como
> conformidade geral da organizacao.

### Exemplo B: SoA Demo

Distribuicao:

| Status | Quantidade |
|---|---:|
| Atende | 1 |
| Parcialmente atende | 1 |
| Nao atende | 1 |
| N/A | 1 |
| Nao avaliado | 96 |
| Total | 100 |

Calculos:

```text
Aderencia dos avaliados = (1 + 0.5 + 0) / 3 = 50%
Completude da avaliacao = 4 / 100 = 4%
Conformidade consolidada = (1 + 0.5) / 99 = 2%
```

Leitura correta:

> A aderencia dos itens avaliados e aplicaveis e 50%, mas a matriz ainda esta
> pouco preenchida. A conformidade consolidada fica em torno de 2%, pois os
> itens nao avaliados sao tratados como ausencia de comprovacao.

## Regras de nomenclatura na UI

Evitar o termo isolado "Aderencia geral" para esse dashboard quando ele se
referir apenas aos itens avaliados. Preferir:

- `Aderencia dos avaliados`
- `Completude da avaliacao`
- `Conformidade consolidada`

Texto recomendado no cabecalho:

```text
Aderencia dos controles avaliados - X de Y itens preenchidos
```

## Fonte tecnica atual

No backend, o campo `overall_adherence` de `GET /gap/assessment/dashboard`
corresponde a "aderencia dos avaliados".

No frontend, a tela `/app/gap-dashboard` deriva:

- `Completude da avaliacao` a partir da distribuicao por status.
- `Conformidade consolidada` a partir da mesma distribuicao, usando a formula
  conservadora descrita neste guia.

Se futuramente o backend passar a expor esses indicadores de forma nativa, os
nomes e formulas deste documento devem continuar como contrato de produto.
