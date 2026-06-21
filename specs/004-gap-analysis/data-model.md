# Data Model — Gap Analysis (Feature 004)

Convenções: toda tabela **por-org** carrega `tenant_id` (FK `organizations`) + RLS; PKs UUID; tempos
em UTC. Tabelas **compartilhadas** (seed) não têm `tenant_id`. Append-only via gatilho onde indicado.

## Enums (em `settings.py`)

- **GapStatus**: `not_filled` (default) | `meets` (Atende totalmente) | `partial` (Atende
  parcialmente) | `not_meet` (Não atende) | `not_applicable` (Não aplicável).
- **GapPriority**: `critical` | `high` | `medium` | `low`.
- **GapDimension**: `clause` (Cláusulas 4–10) | `annex_a` (Controles do Anexo A).
- **GapTheme** (só Anexo A): `organizational` (A.5) | `people` (A.6) | `physical` (A.7) |
  `technological` (A.8).
- **GapAssignmentScope**: `whole` | `theme` (com `scope_theme` = GapTheme).
- **DocType** (estender): `+ gap_baseline`.
- Reuso: `AssignmentStatus`, `AssignmentEventType`, `SignerRole` (do 003); `DocStatus`,
  `Classification` (do Módulo 1).

## Tabelas compartilhadas (plataforma — sem `tenant_id`, somente leitura)

### GapSeedVersion — `gap_seed_version`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| version | String(20) | ex.: "2022.1" (único) |
| description | String(300) | |
| created_at | datetime | |

### GapSeedItem — `gap_seed_item`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| seed_version_id | UUID FK gap_seed_version | |
| dimension | GapDimension | clause \| annex_a |
| ref_code | String(20) | ex.: "6.1.2" ou "A.5.1" |
| name | String(300) | nome do requisito/controle |
| theme | GapTheme \| null | só p/ annex_a |
| objective | Text | texto/objetivo conforme a norma |
| order | int | ordenação de exibição |

Índice único: `(seed_version_id, ref_code)`. **Sem RLS** (referência compartilhada).

## Tabelas por organização (com `tenant_id` + RLS)

### GapCatalogItem — `gap_catalog_item`
Cópia editável do catálogo na organização (materializada na adoção do seed).
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK organizations | |
| seed_item_id | UUID FK gap_seed_item \| null | origem; null se item próprio |
| dimension | GapDimension | |
| ref_code | String(20) | |
| name | String(300) | editável |
| theme | GapTheme \| null | |
| objective | Text | editável |
| order | int | |
| is_custom | bool | item próprio da org |
| is_discontinued | bool | removido em versão posterior do seed (mantido) |
| group_label | String(120) \| null | agrupamento opcional |

Índice único: `(tenant_id, ref_code)`. Aplicabilidade do item é derivada da avaliação
(`status = not_applicable`), não duplicada aqui.

### GapAssessment — `gap_assessment`
Artefato único por organização (1 vigente + baselines). Reusa o padrão de Documento Controlado.
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK organizations | índice único em `tenant_id` (1 por org) |
| seed_version_id | UUID FK gap_seed_version | versão do seed adotada |
| draft_status | DocStatus | draft \| in_review (p/ aprovação de baseline) |
| current_version_id | UUID FK document_versions \| null | baseline vigente |
| created_at / updated_at | datetime | |

### GapAssessmentItem — `gap_assessment_item`
Avaliação de um `gap_catalog_item`.
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK organizations | |
| assessment_id | UUID FK gap_assessment | |
| catalog_item_id | UUID FK gap_catalog_item | |
| status | GapStatus | default not_filled |
| findings | Text \| null | constatações |
| actions | Text \| null | ações de adequação |
| priority | GapPriority \| null | |
| responsible | String(200) \| null | |
| deadline | date \| null | |
| evidence_ref | Text \| null | referência textual (Módulo de Evidências fará o vínculo real) |
| notes | Text \| null | observações |
| exclusion_justification | Text \| null | **obrigatória** quando status=not_applicable |
| maturity_level | int \| null | opcional |
| effort_estimate | String(60) \| null | opcional |
| soa_ref | String(60) \| null | chave de rastreabilidade p/ SoA (Módulo 3) |
| updated_by | UUID \| null | |
| updated_at | datetime | |

Índice único: `(assessment_id, catalog_item_id)`. **Regra**: `status=not_applicable` ⇒
`exclusion_justification` não nula (validado no service ⇒ 422).

### GapAssessmentItemEvent — `gap_assessment_item_event` (append-only)
Histórico de alterações de item (não guarda conteúdo sensível além do necessário).
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK organizations | |
| item_id | UUID FK gap_assessment_item | |
| field | String(40) | campo alterado (ex.: "status", "priority") |
| old_value / new_value | String(120) \| null | valores curtos (status/prioridade); textos longos ⇒ só marca "alterado" |
| actor_id | UUID \| null | |
| created_at | datetime | |

Gatilho **append-only** (bloqueia UPDATE/DELETE), como em `form_assignment_events`.

### GapAssignment — `gap_assignment` (US5 — reusa serviços do 003)
Condução atribuível da avaliação.
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK organizations | |
| assessment_id | UUID FK gap_assessment | |
| scope | GapAssignmentScope | whole \| theme |
| scope_theme | GapTheme \| null | quando scope=theme |
| status | AssignmentStatus | reusa a máquina do 003 |
| respondent_user_id | UUID \| null | membro |
| respondent_email | String(320) \| null | externo |
| respondent_token_hash | String(64) \| null | só hash (reusa mecânica do 003) |
| token_expires_at | datetime \| null | |
| deadline_at | datetime \| null | |
| instructions | Text \| null | |
| claimed_at / submitted_at / signed_at | datetime \| null | |

CHECK: exatamente um respondente (user **ou** email), como em `FormAssignment`. Trilha em
`form_assignment_event` (reuso) referenciando `gap_assignment.id`; assinatura em `FormSignature`
(reuso); OTP via `signature_service`.

### Baseline (reuso de `document_versions`)
Sem tabela nova: `controlled_document_service.approve_document(doc_type=DocType.gap_baseline,
snapshot_factory=...)`. O snapshot serializa: itens (ref_code, status, prioridade, campos), aderência
consolidada (geral/por dimensão/cláusula/tema), `seed_version`, completude. `current_version_id` do
`GapAssessment` aponta a baseline vigente; `is_superseded` deriva obsolescência por recência.

## Relacionamentos

```
organizations 1──* gap_catalog_item *──1 gap_seed_item *──1 gap_seed_version
organizations 1──1 gap_assessment 1──* gap_assessment_item 1──1 gap_catalog_item
gap_assessment_item 1──* gap_assessment_item_event   (append-only)
gap_assessment 1──* document_versions (DocType.gap_baseline)  [baselines]
organizations 1──* gap_assignment *──1 gap_assessment
gap_assignment 1──* form_assignment_event  / 1──* form_signatures   (reuso do 003)
```

## Transições de estado

- **Item**: `not_filled → {meets|partial|not_meet|not_applicable}` (livremente reavaliável;
  not_applicable exige justificativa). Cada transição grava evento append-only + audit.
- **Baseline (GapAssessment.draft_status)**: `draft → in_review` (enviar p/ aprovação) → aprovar
  (Admin) cria `DocumentVersion` e volta a `draft`. (Mesma mecânica do Módulo 1.)
- **GapAssignment**: `pending → in_progress → submitted → signed → completed` (+ `returned`,
  `cancelled`) — reusa `form_workflow`/máquina do 003. Assinatura no `submitted` congela a baseline.

## Regras de validação (resumo)

- `not_applicable` sem `exclusion_justification` ⇒ 422 (FR-007).
- Aderência considera só itens aplicáveis; pesos 1.0/0.5/0.0; denominador zero ⇒ "—" (FR-011).
- Lacunas = itens aplicáveis com `partial`/`not_meet`, ordenáveis por prioridade (FR-013).
- Adoção de nova `seed_version` é aditiva e preserva itens/avaliações (FR-002).
- Cross-tenant em qualquer recurso ⇒ 404/403 + audit (SEC-001).
