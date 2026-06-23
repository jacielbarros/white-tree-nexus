# Research: Documentos Imprimiveis, Pre-visualizaveis e Assinaveis

## Decision: Usar ReportLab como renderer PDF do MVP

**Rationale**: `reportlab>=4.0` ja esta em `requirements.txt`, e o servico atual de exportacao da
SoA (`soa_export_service.py`) ja segue esse padrao. ReportLab evita dependencias nativas de HTML/CSS,
funciona bem no ambiente Windows do projeto e permite gerar PDFs deterministas a partir de snapshots
imutaveis.

**Alternatives considered**:

- WeasyPrint: bom para HTML/CSS, mas traz dependencias nativas e maior risco operacional no Windows.
- wkhtmltopdf/pdfkit: depende de binario externo e instalacao fora do Python.
- Browser headless/Playwright para imprimir HTML: aumenta superficie operacional e acopla backend a
  runtime de navegador.

## Decision: Templates como secoes/variaveis controladas, nao HTML livre

**Rationale**: A clarificacao da spec permite templates proprios por Admin da organizacao, mas sem
editor visual avancado. Um schema controlado de secoes, tabelas, titulos, blocos de texto e variaveis
permitidas reduz risco de XSS, vazamento de dados por variavel arbitraria e inconsistencias visuais.
O renderer converte esse schema para ReportLab.

**Alternatives considered**:

- HTML/CSS versionado: flexivel, mas exigiria sanitizacao forte e renderer HTML confiavel.
- Templates hard-coded por tipo: mais simples, mas impediria customizacao controlada por organizacao.
- Editor visual avancado: fora do MVP e aumenta muito escopo.

## Decision: Preview cria snapshot temporario e PDF preliminar armazenado com TTL

**Rationale**: A resposta de clarificacao definiu que o preview gera snapshot temporario e so pode ser
assinado se artefato e template nao mudarem desde a geracao. O modelo `DocumentPreview` guarda
fingerprint do artefato, hash da versao do template, snapshot hash, PDF preliminar e `expires_at`.

**Alternatives considered**:

- Gerar preview sem persistir snapshot: dificulta provar que o documento assinado corresponde ao
  documento visualizado.
- Congelar versao final no preview: confundiria preview com assinatura e violaria a spec.
- Permitir assinatura de preview stale com aviso: rejeitado por risco de assinatura de conteudo
  diferente do revisado.

## Decision: Assinatura documental em entidade propria, mantendo FormSignature legado

**Rationale**: `FormSignature` e `signature_service.py` sao acoplados a `form_assignments`. A feature
precisa assinar Contexto, Gap, SoA e futuramente Gap Baseline/Form Response. Criar
`DocumentSignature` e `document_signature_service.py` reaproveita canonicalizacao/hash/audit, mas
evita quebrar fluxos de formulario existentes.

**Alternatives considered**:

- Reutilizar `FormSignature` com campos opcionais: introduziria FK nullable e semantica ambigua.
- Migrar imediatamente todo o motor de assinatura: maior risco e fora do MVP.
- Assinar apenas via `DocumentVersion.content_snapshot`: faltariam PDF final, template versionado e
  cadeia documental explicita.

## Decision: Storage local cifrado para PDFs finais e preliminares

**Rationale**: PDFs podem conter PII, dados confidenciais e referencias a evidencias. Como a Feature
008 ja estabeleceu storage local cifrado para evidencias, a feature 009 replica o padrao com
`DOCUMENT_STORAGE_DIR`, storage keys opacas, SHA-256 do plaintext e Fernet via `FIELD_ENCRYPTION_KEY`.
Falha de storage/cifragem e fail-closed para assinatura e download final.

**Alternatives considered**:

- Armazenar PDF em coluna bytea: simplifica transacao, mas cresce banco e dificulta evolucao para S3.
- Renderizar sempre on-demand: nao preserva exatamente o PDF assinado apos mudancas futuras.
- Armazenar sem cifragem local: rejeitado por sensibilidade dos documentos.

## Decision: Documentos assinados nao substituem `DocumentVersion`, mas podem referencia-lo

**Rationale**: O projeto ja usa `DocumentVersion` para versoes controladas de Contexto, Gap Baseline e
SoA. A feature de impressao/assinatura adiciona uma camada de documento PDF assinado (`SignedDocument`)
que referencia o artefato de origem e, quando existir, a `DocumentVersion` fonte. Assim preserva
compatibilidade e permite assinar o relatorio consolidado de Contexto, que agrega varios artefatos.

**Alternatives considered**:

- Expandir `DocumentVersion` para armazenar PDF e assinatura: exigiria misturar versoes logicas de
  artefatos com documentos imprimiveis, aumentando risco em fluxos existentes.
- Ignorar `DocumentVersion`: perderia rastreabilidade com documentos controlados ja aprovados.

## Decision: Permissao de assinatura mapeada ao modulo de origem

**Rationale**: A spec definiu que a assinatura segue a permissao de aprovacao existente:
`approve_context_document` para Contexto consolidado, `approve_gap_baseline` para Gap Analysis e
`approve_soa` para SoA. Preview e historico usam permissao de visualizacao do modulo. Templates
customizados exigem Admin da organizacao ou permissao dedicada `manage_print_templates`.

**Alternatives considered**:

- Criar `sign_print_document` generico: simples, mas criaria matriz paralela de aprovadores.
- Reusar apenas `manage_*`: daria a gestores de manutencao poder formal de assinatura.

## Decision: Verificacao por hash interno e identificador verificavel no MVP

**Rationale**: O MVP nao inclui PAdES/ICP-Brasil nem verificacao publica. Cada documento assinado
recebe identificador unico, SHA-256 do PDF final e hash canonico do snapshot assinado. A verificacao
recalcula o hash do arquivo armazenado e compara com os metadados imutaveis.

**Alternatives considered**:

- Assinatura digital embutida no PDF: fora do escopo.
- Verificacao publica anonima: exige desenho adicional de exposicao e privacidade.
- Somente hash em banco: insuficiente se o PDF final nao for preservado.

## Decision: Seeds idempotentes para templates padrao

**Rationale**: O MVP precisa funcionar sem configuracao inicial. A migration/seed deve criar ou
atualizar templates padrao de sistema para `context_report`, `gap_report` e `soa_report` de forma
idempotente, sem duplicar versoes em reexecucao.

**Alternatives considered**:

- Criar templates via startup: menos rastreavel que migration/seed idempotente.
- Exigir criacao manual por organizacao: viola criterio de sucesso de templates padrao.
