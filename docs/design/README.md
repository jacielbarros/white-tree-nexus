# Caixa de entrada do design (output do Claude Design)

Cole aqui o resultado do **Claude Design** (prompt em
[`../feature-ux-revamp.md`](../feature-ux-revamp.md) → seção "Prompt para o Claude Design").
Depois é só avisar: *"o design está em `docs/design/`"* — eu leio e implemento (tokens + shell +
dashboard primeiro), **traduzindo** o HTML/CSS para componentes Angular + tema PrimeNG.

## Onde colar cada coisa (em ordem de importância)

| Arquivo | Conteúdo | Vira o quê na implementação |
|---|---|---|
| `tokens.css` | **Design tokens** como CSS variables, **claro + escuro** (cores/superfícies/texto/borda, raio, espaçamento, tipografia) | camada de tokens em `wtnadmin/src/styles.scss` |
| `mapping.md` | **Guia**: tokens `--wtn-*` → variáveis do PrimeNG (`--p-*`) e preset Material | overrides do tema PrimeNG |
| `components.md` | **Specs de componentes** + estados (botão, input/select/textarea, card, tag/badge de status, tabela densa, dialog, toast, tabs, timeline/wizard, empty state, loading) | padrões reutilizados nas telas |
| `screens/*.html` | **Mockups HTML/CSS** das telas-chave, nos dois temas (ver lista abaixo) | referência de estrutura/espaçamento por página |
| `screenshots/*.png` | (opcional) capturas dos mockups | referência visual complementar |

### Telas sugeridas em `screens/`
- `shell.html` — sidebar agrupada + topbar (a nova navegação)
- `dashboard.html` — **home / tela-âncora** (cards por módulo)
- `login.html` — padrão das telas públicas (auth)
- `gap-matrix.html` — Matriz do Gap (grade por tema + dialog de edição)
- `soa.html` — Declaração de Aplicabilidade

## Dicas
- **Tokens são o item crítico** — sem eles a implementação não fica fiel. Se for colar só uma coisa,
  cole `tokens.css`.
- Mantenha **claro + escuro** nos tokens (o app suporta os dois).
- Não precisa ser código Angular — HTML/CSS de referência basta; eu adapto.
- Pode colar em pedaços; me avise o que já está disponível e eu começo pelos tokens + shell.
