# Phase 0 Research: Anexos e Evidencias na Matriz do Gap Analysis

## Decision: storage local configuravel para o MVP

**Chosen**: armazenar o conteudo dos arquivos em filesystem local sob `EVIDENCE_STORAGE_DIR`, com
chaves opacas por tenant/evidencia/versao, cifragem em repouso via Fernet/`FIELD_ENCRYPTION_KEY`, e
persistir no banco apenas metadados, `storage_key`, tamanho, MIME, extensao e SHA-256.

**Rationale**: a spec exclui integracao com storage externo especifico. O AGENTS.md ja define
`FIELD_ENCRYPTION_KEY`, `EVIDENCE_STORAGE_DIR=./evidence_store/` e
`EVIDENCE_MAX_FILE_BYTES=20971520`, entao o plano fica compativel com a arquitetura existente e deixa
a troca futura por S3/object storage encapsulada em `utils/evidence_storage.py`.

**Alternatives considered**:
- Banco de dados como BLOB: simplifica transacao, mas aumenta carga no PostgreSQL, dificulta streaming
  e backup seletivo.
- S3/minio agora: mais proximo de producao, mas esta explicitamente fora do escopo inicial.
- Arquivos plaintext em disco: mais simples, mas incompatível com a constitution para evidencias que
  podem conter PII ou informacao confidencial.

## Decision: SHA-256 streaming como identificador de integridade

**Chosen**: calcular SHA-256 do conteudo original no upload e gravar `content_hash` +
`hash_algorithm="sha256"` em cada versao. O arquivo armazenado e cifrado; a verificacao futura deve
decifrar e recomputar o hash do conteudo original.

**Rationale**: ja existe uso de SHA-256 no produto para assinaturas/hash de token; atende ao criterio de
integridade sem depender de assinatura eletronica, que esta fora de escopo.

**Alternatives considered**:
- MD5/SHA-1: inadequados para integridade de compliance.
- Assinatura digital: robusta, mas fora de escopo.

## Decision: evidencia e versao separadas

**Chosen**: `GapEvidence` representa o registro logico vinculado ao item; `GapEvidenceVersion`
representa cada arquivo enviado/substituido; `GapEvidence.current_version_id` identifica a versao
corrente.

**Rationale**: a lista principal precisa mostrar apenas a versao corrente, enquanto historico e cadeia
de custodia precisam preservar versoes anteriores. Separar as entidades evita sobrescrever metadados
imutaveis do arquivo e prepara reuso futuro em SoA/auditoria.

**Alternatives considered**:
- Uma tabela unica com linhas duplicadas por versao: consulta corrente fica ambigua e aumenta risco de
  exibir historico para `view_gap`.
- Sobrescrever arquivo no mesmo registro: viola append-only/cadeia de custodia.

## Decision: evento de evidencia dedicado + audit log

**Chosen**: criar `GapEvidenceEvent` append-only para historico de dominio e tambem chamar
`AuditService.log_from_request()` nas acoes sensiveis definidas pela spec.

**Rationale**: audit log e trilha de cadeia de custodia tem finalidades diferentes. O audit log e
transversal e sem conteudo sensivel; o evento de evidencia sustenta a UI de historico para `manage_gap`.

**Alternatives considered**:
- Usar apenas audit log: evitaria uma tabela, mas dificultaria a tela de historico e misturaria
  auditoria operacional com historico de dominio.

## Decision: regra de classificacao explicita para conteudo

**Chosen**: metadados ativos/correntes do item ficam visiveis a `view_gap`; download/conteudo de
`publico` e `uso_interno` exige `view_gap`; download/conteudo de `confidencial` e `restrito` exige
`manage_gap`. Historico, versoes anteriores e evidencias inativadas exigem `manage_gap`.

**Rationale**: decisao direta das clarificacoes. O helper `classification_access_policy` pode ser usado
como restricao adicional futura, mas nunca para afrouxar a regra minima da spec.

**Alternatives considered**:
- Usar apenas politica por tenant: flexivel, mas insuficiente para garantir o comportamento MVP
  especificado.
- Exigir `manage_gap` para todo download: mais restritivo, mas piora a utilidade para auditores/leitores
  de evidencias publicas/internas.

## Decision: endpoints aninhados no item da avaliacao

**Chosen**: expor evidencias em `/gap/assessment/items/{item_id}/evidences`.

**Rationale**: a experiencia nasce no painel lateral de um item. O `item_id` ja e tenant-scoped via
`GapAssessmentItem`, e o path deixa claro que a evidencia pertence a um item especifico da matriz.

**Alternatives considered**:
- `/gap/evidences/{id}` global: util para futuro modulo de gestao de evidencias, mas menos contextual
  para o MVP da matriz.

## Decision: validacao fail-closed de upload

**Chosen**: recusar arquivo vazio, acima do limite, extensao/MIME nao permitido ou falha de storage sem
criar evidencia valida. Escrita usa arquivo temporario + rename/commit coordenado; falha remove artefato
temporario quando possivel.

**Rationale**: a matriz deve continuar funcionando, mas evidencias invalidas nao podem virar registros
auditaveis falsos.

**Alternatives considered**:
- Criar registro "pending" e reconciliar depois: aumenta estados e escopo sem necessidade no MVP.
