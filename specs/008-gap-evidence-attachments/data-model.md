# Phase 1 Data Model: Anexos/Evidencias na Matriz do Gap Analysis

Todos os modelos abaixo sao **dados da organizacao** e carregam `tenant_id`.

## Enums e constantes

### `Classification` existente

Reusar `wtnapp.settings.Classification`:

- `publico`
- `uso_interno` (default do upload)
- `confidencial`
- `restrito`

### `GapEvidenceStatus`

Novo enum em `settings.py`:

- `active`: evidencia aparece na lista principal, com a versao corrente.
- `inactive`: evidencia removida logicamente; nao aparece para `view_gap`, mas fica no historico para
  `manage_gap`.

### `GapEvidenceEventType`

Novo enum em `settings.py` ou string validada no schema/model:

- `uploaded`
- `content_viewed`
- `downloaded`
- `replaced`
- `inactivated`
- `access_denied`

## `gap_evidence`

Registro logico de uma evidencia anexada a um item do Gap Analysis.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | Gerado no backend |
| `tenant_id` | UUID FK `organizations.id` | Obrigatorio; indexado; RLS |
| `assessment_item_id` | UUID FK `gap_assessment_item.id` | Obrigatorio; item deve pertencer ao mesmo tenant |
| `title` | String(255) | Nome visivel; default = filename original sanitizado |
| `description` | Text nullable | Descricao curta opcional |
| `classification` | Enum `Classification` | Classificação corrente da evidência; default `uso_interno` no upload inicial e atualizada quando uma nova versão vira corrente |
| `status` | Enum `GapEvidenceStatus` | `active` por default |
| `current_version_id` | UUID nullable | Id da versao corrente; preenchido apos criar a primeira versao |
| `created_by` | UUID FK/logical `users.id` | Usuario que criou |
| `created_at` | DateTime(tz) | Obrigatorio |
| `updated_at` | DateTime(tz) | Atualizado em nova versao/inativacao |
| `inactivated_by` | UUID nullable | Usuario que inativou |
| `inactivated_at` | DateTime(tz) nullable | Data da inativacao |
| `inactivation_reason` | String(300) nullable | Motivo sem conteudo sensivel |

Indices/restricoes:

- `ix_gap_evidence_tenant_id`
- `ix_gap_evidence_assessment_item_id`
- `ix_gap_evidence_status`
- `ix_gap_evidence_current_version_id`

## `gap_evidence_version`

Versao imutavel do arquivo de uma evidencia.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | Gerado no backend |
| `tenant_id` | UUID FK `organizations.id` | Obrigatorio; indexado; RLS |
| `evidence_id` | UUID FK `gap_evidence.id` | Obrigatorio |
| `version_number` | Integer | Comeca em 1; incrementa por evidencia |
| `classification` | Enum `Classification` | Classificação da versão no momento do upload/substituição; obrigatória |
| `original_filename` | String(255) | Nome original sanitizado para exibicao |
| `storage_key` | String(500) | Chave interna opaca; nunca expor em API/audit |
| `content_hash` | String(64) | SHA-256 hex |
| `hash_algorithm` | String(20) | `sha256` |
| `encrypted` | Boolean | `true` no MVP |
| `encryption_scheme` | String(40) | `fernet` quando cifrado |
| `size_bytes` | Integer | > 0 e <= `EVIDENCE_MAX_FILE_BYTES` |
| `mime_type` | String(120) nullable | Detectado/recebido do upload |
| `extension` | String(20) | Normalizada em lowercase |
| `uploaded_by` | UUID | Usuario que enviou a versao |
| `uploaded_at` | DateTime(tz) | Obrigatorio |

Indices/restricoes:

- unique `uq_gap_evidence_version_number` (`tenant_id`, `evidence_id`, `version_number`)
- `ix_gap_evidence_version_tenant_id`
- `ix_gap_evidence_version_evidence_id`
- `ix_gap_evidence_version_hash`

Imutabilidade:

- Versoes nao sao atualizadas/deletadas por operacoes comuns.
- Migration MUST criar trigger append-only em PostgreSQL/SQLite para bloquear UPDATE/DELETE em
  `gap_evidence_version`.

## `gap_evidence_event`

Historico de cadeia de custodia da evidencia.

| Campo | Tipo | Regra |
|-------|------|-------|
| `id` | UUID PK | Gerado no backend |
| `tenant_id` | UUID FK `organizations.id` | Obrigatorio; indexado; RLS |
| `evidence_id` | UUID FK `gap_evidence.id` nullable | Nullable para tentativa negada antes de resolver recurso |
| `version_id` | UUID FK `gap_evidence_version.id` nullable | Presente quando evento envolve uma versao |
| `assessment_item_id` | UUID FK `gap_assessment_item.id` nullable | Ajuda auditoria contextual |
| `event_type` | String/Enum | `uploaded`, `downloaded`, `replaced`, etc. |
| `outcome` | String(20) | `success` ou `denied` |
| `actor_id` | UUID nullable | Usuario autenticado |
| `occurred_at` | DateTime(tz) | Obrigatorio |
| `details` | JSON | Sanitizado: sem conteudo, path, token, PII ou storage_key |

Indices:

- `ix_gap_evidence_event_tenant_id`
- `ix_gap_evidence_event_evidence_id`
- `ix_gap_evidence_event_item_id`
- `ix_gap_evidence_event_type`

Imutabilidade:

- Trigger append-only bloqueia UPDATE/DELETE.

## DTOs de API

### `GapEvidenceSummary`

Usado pela lista principal.

- `id`
- `assessment_item_id`
- `title`
- `description`
- `classification`
- `status`
- `current_version_id`
- `file_name`
- `mime_type`
- `extension`
- `size_bytes`
- `content_hash`
- `hash_algorithm`
- `uploaded_by`
- `uploaded_at`
- `created_at`
- `can_download`

Nao inclui `storage_key`.

### `GapEvidenceHistory`

Disponivel apenas para `manage_gap`.

- `evidence`: metadados do registro logico
- `versions`: lista de `GapEvidenceVersionSummary`
- `events`: lista de `GapEvidenceEventSummary`

### `GapEvidenceVersionSummary`

Usado no histórico disponível apenas para `manage_gap`.

- `id`
- `version_number`
- `classification`
- `file_name`
- `mime_type`
- `extension`
- `size_bytes`
- `content_hash`
- `hash_algorithm`
- `uploaded_by`
- `uploaded_at`
- `is_current`

### `GapEvidenceUploadRequest`

Multipart/form-data:

- `file`: obrigatorio
- `title`: opcional
- `description`: opcional
- `classification`: obrigatorio, default frontend `uso_interno`

### `GapEvidenceReplaceRequest`

Multipart/form-data:

- `file`: obrigatorio
- `description`: opcional
- `classification`: obrigatorio, default frontend = classificação corrente da evidência

## Relacionamentos

- `GapAssessmentItem (1) -> (N) GapEvidence`
- `GapEvidence (1) -> (N) GapEvidenceVersion`
- `GapEvidence (1) -> (N) GapEvidenceEvent`
- `GapEvidence.current_version_id -> GapEvidenceVersion.id`

## State transitions

```text
active + version 1
  | replace
  v
active + version N (current_version_id aponta para a nova versao)
  | inactivate
  v
inactive (lista principal oculta; historico visivel apenas para manage_gap)
```

Regras:

- Upload inicial cria `GapEvidence`, `GapEvidenceVersion(version_number=1)` e evento `uploaded`.
- Substituicao cria nova `GapEvidenceVersion(version_number=N+1)` com classificação obrigatória,
  atualiza `current_version_id` e a classificação corrente em `GapEvidence`, e cria evento `replaced`;
  a versao anterior permanece imutável.
- Inativacao muda `GapEvidence.status` para `inactive`, preenche `inactivated_*` e cria evento
  `inactivated`; nao apaga arquivo fisicamente.
- Download/conteudo cria evento/audit `downloaded` ou `content_viewed` apenas quando o conteudo e
  acessado, nao quando metadados sao listados.

## Validacoes

- O item selecionado deve existir em `scoped_query(db, GapAssessmentItem, ctx)`.
- O item e a evidencia devem pertencer ao mesmo `tenant_id`.
- Arquivo deve ter tamanho entre 1 e `EVIDENCE_MAX_FILE_BYTES`.
- Extensao/MIME deve estar na politica permitida.
- `FIELD_ENCRYPTION_KEY` deve estar configurada para permitir upload; se ausente/invalida, upload
  falha de forma clara e fail-closed.
- `classification` e obrigatoria no upload inicial e na substituição por nova versão.
- `title`, `description` e `inactivation_reason` devem ter limites e sanitizacao simples; nao gravar
  conteudo do arquivo nesses campos.
- Historico, versoes anteriores e inativas exigem `manage_gap`.
- Download de `confidencial`/`restrito` exige `manage_gap`; `publico`/`uso_interno` exige `view_gap`.
