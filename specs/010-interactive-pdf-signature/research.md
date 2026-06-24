# Research: Preview Interativo e Posicionamento Visual de Assinatura em PDF

## Decision: usar visualizacao PDF controlada no frontend

**Decision**: Adicionar uma dependencia frontend baseada em PDF.js (`pdfjs-dist`) e criar um
componente compartilhado de visualizacao/posicionamento.

**Rationale**: O viewer nativo do navegador nao oferece controle consistente de pagina, zoom, overlay
de selo e conversao de coordenadas. PDF.js permite renderizar paginas em canvas, aplicar overlay
controlado, testar estados de carregamento/erro e manter experiencia consistente nas telas de
Contexto, Gap Analysis e SoA.

**Alternatives considered**:

- Iframe/navegador nativo: simples, mas pouco controlavel para overlay e testes.
- Biblioteca Angular pronta de PDF viewer: pode acelerar UI, mas aumenta acoplamento; avaliar na
implementacao se agrega sem contrariar a necessidade de coordenadas canonicas.

## Decision: coordenadas canonicas em pontos PDF, origem inferior esquerda

**Decision**: Persistir `x`, `y`, `width`, `height`, `page_width` e `page_height` em pontos PDF, com
origem inferior esquerda. O frontend converte coordenadas visuais do canvas para esse sistema ao
confirmar a posicao.

**Rationale**: ReportLab e o PDF final operam naturalmente em pontos PDF com origem inferior
esquerda. Persistir esse formato reduz ambiguidades no backend e melhora a preparacao para
assinatura digital futura.

**Alternatives considered**:

- Percentuais normalizados: bons para UI responsiva, mas exigem conversao extra no backend e podem
  perder precisao em paginas com rotacao/dimensoes diferentes.
- Persistir ambos: aumenta redundancia e risco de divergencia sem beneficio imediato para MVP.

## Decision: posicao confirmada e append-only no preview

**Decision**: Cada confirmacao de posicao cria uma nova revisao append-only vinculada ao preview. A
posicao ativa e a revisao confirmada mais recente e valida. Ao assinar, a posicao e copiada para um
snapshot imutavel vinculado ao documento assinado.

**Rationale**: O usuario pode ajustar a posicao antes de assinar sem perder trilha de auditoria. O
documento assinado preserva exatamente a posicao usada, mesmo se o preview ou template mudar depois.

**Alternatives considered**:

- Enviar coordenadas apenas no payload de assinatura: menor schema, mas pior auditoria e maior risco
  de divergencia entre visualizado e assinado.
- Usar apenas posicao padrao: nao entrega o valor principal da feature.

## Decision: areas bloqueadas definidas por politica/template e validadas no backend

**Decision**: A politica de assinatura visual pode definir areas bloqueadas/reservadas por tipo
documental ou versao de template. O backend valida se o retangulo do selo intersecta areas bloqueadas
antes de confirmar posicao e novamente antes de assinar.

**Rationale**: Mantem liberdade de posicionamento sem permitir que o selo cubra conteudo sensivel ou
regioes reservadas. Revalidar antes de assinar evita manipulacao no cliente.

**Alternatives considered**:

- Posicao livre em qualquer lugar: simples, mas pode gerar PDFs ruins ou cobrir conteudo.
- Apenas ancoras predefinidas: seguro, mas sacrifica a flexibilidade pedida pelo usuario.

## Decision: preparar metodos de assinatura sem implementar PAdES

**Decision**: Introduzir metadados `signature_method` e `signature_provider` com valor MVP
`internal_electronic_signature`; reservar valores futuros `pades`, `icp_brasil` e
`external_certificate_provider`.

**Rationale**: Evita confundir selo visual interno com assinatura digital criptografica e permite que
documentos antigos mantenham metodo original quando provedores futuros forem adicionados.

**Alternatives considered**:

- Usar apenas `level` existente em `DocumentSignature`: insuficiente para diferenciar provider e
  evolucao PAdES/ICP-Brasil.
- Implementar PAdES agora: fora do escopo e adiciona risco de certificacao/infra antes da UX base.

## Decision: inline preview tem evento auditavel proprio

**Decision**: Criar operacao/evento especifico para abertura de preview inline, separado do download
preliminar.

**Rationale**: Visualizar conteudo sensivel em tela e uma acao relevante para auditoria. Separar do
download evita mascarar comportamento e facilita dashboards/trilhas futuras.

**Alternatives considered**:

- Reutilizar evento de download: simples, mas semanticamente incorreto.
- Nao auditar visualizacao inline: viola rastreabilidade para documentos confidenciais.
