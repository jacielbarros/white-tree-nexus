# Phase 1 — Data Model: Módulo de Gestão de Riscos

**Feature**: `012-risk-management` · **Date**: 2026-06-26 · **Input**: [research.md](research.md), [spec.md](spec.md)

Convenções: todas as tabelas de **domínio** carregam `tenant_id` (FK `organizations.id`) + RLS. As duas
tabelas-**semente** são **platform-level sem `tenant_id`** (read-only, sem RLS — exceção do Gap).
Tipos `Uuid(as_uuid=True)` PK `uuid4`; enums `SAEnum(..., native_enum=False)`; timestamps `timezone=True`.
Membros (dono/responsável) = FK `users.id` (referência a membro da org, no padrão do Ativos).

---

## 1. Catálogos-semente (plataforma — sem `tenant_id`)

### `threat_seed_item` — ameaça de referência (ISO 27005, PT-BR original)
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| code | String(20) | único; ex.: `AME-001` |
| name | String(300) | |
| description | Text | |
| category | SAEnum(ThreatCategory) | humana/ambiental/técnica/organizacional |
| origin | SAEnum(ThreatOrigin) \| null | deliberate/accidental/environmental |
| order | Integer | ordenação de exibição |

### `vulnerability_seed_item` — vulnerabilidade de referência
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| code | String(20) | único; ex.: `VUL-001` |
| name | String(300) | |
| description | Text | |
| category | SAEnum(VulnerabilityCategory) | técnica/física/organizacional/humana/processual |
| order | Integer | |

> Sem RLS; somente leitura para a org; editáveis só pelo Super Admin (`require_super_admin`).
> `load_seed()` é idempotente por `code`.

---

## 2. Metodologia de risco (1 por org)

### `risk_methodology`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | **único** (`uq_risk_methodology_tenant`) |
| is_configured | Boolean | `false` = ainda usando default; `true` = a org salvou |
| probability_scale | JSON | lista `[{order:1..5, label}]` |
| impact_scale | JSON | lista `[{order:1..5, label}]` |
| risk_levels | JSON | lista `[{key, label, severity, color, order}]` (ex.: baixo/medio/alto/critico) |
| risk_matrix | JSON | mapa `"{prob}x{impact}" → level_key` (25 células) |
| acceptance | JSON | mapa `level_key → accepted:bool` (critério de aceitação por nível) |
| cia_impact_map | JSON | mapa `CiaLevel → impact_order` (default baixa→2, media→3, alta→4, critica→5) |
| created_at / updated_at | DateTime | |

**Regras**: se não houver linha, `risk_methodology_service.get_or_default()` devolve o **default 5x5**
(in-code) e a avaliação prossegue (gate suave, FR-006). Validação ao salvar: 5 níveis em cada escala;
matriz cobre as 25 combinações; cada `level_key` da matriz existe em `risk_levels`; `acceptance` cobre
todos os níveis. Editar a matriz/critério dispara **recálculo em massa** dos riscos (FR-008).

---

## 3. Catálogo da organização (cópia editável)

### `org_threat`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| seed_item_id | UUID FK→threat_seed_item \| null | null para item próprio |
| code | String(20) | único por tenant (`uq_org_threat_tenant_code`) |
| name | String(300) | obrigatório |
| description | Text \| null | |
| category | SAEnum(ThreatCategory) | |
| origin | SAEnum(ThreatOrigin) \| null | |
| is_custom | Boolean | `true` = criado pela org |
| is_archived | Boolean | arquivamento lógico |
| archive_reason | String(500) \| null | obrigatório ao arquivar |
| created_by | UUID FK→users | |
| created_at / updated_at | DateTime | |

### `org_vulnerability`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| seed_item_id | UUID FK→vulnerability_seed_item \| null | |
| code | String(20) | único por tenant |
| name | String(300) | obrigatório |
| description | Text \| null | |
| category | SAEnum(VulnerabilityCategory) | |
| gap_catalog_item_id | UUID FK→gap_catalog_item \| null | referência a controle/gap **ausente** da org (FR-014) |
| is_custom / is_archived | Boolean | |
| archive_reason | String(500) \| null | |
| created_by | UUID FK→users | |
| created_at / updated_at | DateTime | |

### `asset_threat_link` / `asset_vulnerability_link` (vínculo a Ativos — Fase 1)
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| asset_item_id | UUID FK→asset_items | mesmo tenant |
| threat_id / vulnerability_id | UUID FK→org_threat / org_vulnerability | mesmo tenant |
| created_by | UUID FK→users | |
| created_at | DateTime | |

> `UniqueConstraint(tenant_id, asset_item_id, threat_id)` (e análogo para vuln). Só une itens do mesmo
> tenant (app + RLS). Alimenta os placeholders "Ameaças/Vulnerabilidades vinculadas" do detalhe do ativo.

---

## 4. Registro de risco (Fase 2)

### `risk`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| code | String(20) | `RSK-####`, único por tenant, imutável |
| title | String(300) | **obrigatório** |
| description | Text | **obrigatório** |
| threat_id | UUID FK→org_threat | **obrigatório** (cenário) |
| vulnerability_id | UUID FK→org_vulnerability | **obrigatório** (cenário) |
| probability_level | Integer(1..5) \| null | null até avaliar |
| impact_level | Integer(1..5) \| null | derivado da CIA ou override |
| impact_derived_level | Integer(1..5) \| null | valor que a CIA sugeriria (p/ divergência) |
| impact_is_override | Boolean | `true` se ajustado manualmente |
| impact_override_reason | Text \| null | obrigatório quando override |
| inherent_level_key | String(20) \| null | calculado pela matriz |
| above_acceptance | Boolean \| null | derivado do critério |
| owner_user_id | UUID FK→users \| null | dono do risco (membro); obrigatório p/ avaliado |
| status | SAEnum(RiskStatus) | identified/assessed/in_treatment/accepted/closed |
| treatment_option | SAEnum(RiskTreatmentOption) \| null | mitigate/accept/transfer/avoid |
| residual_probability_level | Integer(1..5) \| null | re-pontuação |
| residual_impact_level | Integer(1..5) \| null | |
| residual_level_key | String(20) \| null | |
| residual_above_acceptance | Boolean \| null | |
| acceptance_reason | Text \| null | obrigatório quando aceito |
| accepted_owner_user_id | UUID FK→users \| null | dono a quem a aceitação é atribuída |
| accepted_by_user_id | UUID FK→users \| null | usuário que registrou a aceitação |
| accepted_at | DateTime \| null | |
| is_archived | Boolean | arquivamento lógico |
| archive_reason | String(500) \| null | |
| created_by / updated_by | UUID FK→users | |
| created_at / updated_at | DateTime | |

**Índices**: `tenant_id`, `code`, `status`, `owner_user_id`, `inherent_level_key`, `above_acceptance`.

### `risk_asset_link` (cenário com 0..n ativos)
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| risk_id | UUID FK→risk | |
| asset_item_id | UUID FK→asset_items | mesmo tenant |
| created_at | DateTime | `UniqueConstraint(risk_id, asset_item_id)` |

> Ativos **opcionais** (clarificação Q3). Sem ativos ⇒ impacto manual obrigatório.

---

## 5. Tratamento e controles (Fase 3)

### `risk_treatment_control` (controle selecionado · vínculo controle ← risco / insumo SoA)
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| risk_id | UUID FK→risk | |
| gap_catalog_item_id | UUID FK→gap_catalog_item \| null | controle A.5–A.8 do catálogo **da org** |
| custom_control_label | String(300) \| null | quando controle adicional/custom |
| responsible_user_id | UUID FK→users \| null | **obrigatório** quando mitigar |
| due_date | Date \| null | **obrigatório** quando mitigar |
| note | Text \| null | |
| created_by | UUID FK→users | |
| created_at | DateTime | |

> Exatamente um de `gap_catalog_item_id` **ou** `custom_control_label` é preenchido (CHECK na app).
> `gap_catalog_item_id` deve ser do mesmo tenant (não-descontinuado). É a base do **SoA-feed** (R7).

### `risk_plan` (Plano de Tratamento — Documento Controlado, 1 por org)
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | **único** |
| draft_status | SAEnum(DocStatus) | draft/in_review (in_force ⇒ via versão) |
| current_version_id | UUID \| null | ponteiro p/ `document_versions` (DocType.risk_treatment_plan) |
| created_at / updated_at | DateTime | |

> Versões imutáveis vivem em `document_versions` (tabela existente), `DocType.risk_treatment_plan` (novo).
> Aprovação reusa `controlled_document_service.approve_document` + assinatura avançada **opcional**
> (`signature_service`). `content_snapshot` = registro de riscos + tratamentos + residuais no momento.

---

## 6. Histórico append-only

### `risk_events`
| Campo | Tipo | Notas |
|------|------|------|
| id | UUID PK | |
| tenant_id | UUID FK→organizations | +RLS |
| risk_id | UUID FK→risk \| null | null = evento de nível do plano |
| event_type | String(40) | RiskEventType (CREATE/UPDATE/PROBABILITY_CHANGE/IMPACT_CHANGE/LEVEL_CHANGE/OWNER_CHANGE/TREATMENT_DECISION/CONTROL_ADD/CONTROL_REMOVE/ACCEPTED/ARCHIVE/PLAN_SUBMITTED/PLAN_APPROVED) |
| field_name | String(60) \| null | |
| old_value / new_value | Text \| null | |
| reason | String(500) \| null | **obrigatório** nas mudanças relevantes |
| actor_id | UUID \| null | |
| occurred_at | DateTime | |
| details | JSON \| null | |

> Gatilhos append-only (SQLite `RAISE(ABORT)` + PG `RAISE EXCEPTION`), padrão `asset_item_events`.

---

## Relacionamentos (resumo)

```
organizations 1─* risk_methodology (1:1) / org_threat / org_vulnerability / risk / risk_plan / *_link / risk_events
threat_seed_item 1─* org_threat            vulnerability_seed_item 1─* org_vulnerability
asset_items 1─* asset_threat_link / asset_vulnerability_link / risk_asset_link / risk_treatment_control
org_threat 1─* risk            org_vulnerability 1─* risk (cenário: 1 ameaça + 1 vuln + 0..n ativos)
gap_catalog_item 1─* org_vulnerability(ref) / risk_treatment_control (controle A.5–A.8 da org)
risk 1─* risk_asset_link / risk_treatment_control / risk_events
risk_plan 1─* document_versions (DocType.risk_treatment_plan)  [tabela existente]
users 1─* risk(owner/created/updated/accepted) / *_link(created_by) / risk_treatment_control(responsible)
```

## Máquina de estados do risco (`status`)

```
identified ──(prob+impacto+dono)──▶ assessed ──(decisão de tratamento)──▶ in_treatment
   │                                    │                                      │
   └──────────────── archive ◀──────────┴──────── accept (justif.+dono) ──▶ accepted
                                                                              │
                                                          (residual ok / fim)─┴─▶ closed
```

- `identified`: cenário criado (título/descrição/ameaça/vuln). Sem prob/impacto/dono ainda.
- `assessed`: prob + impacto + dono presentes ⇒ nível e aceitação calculados (FR-043).
- `in_treatment`: opção de tratamento definida; mitigar exige ≥1 controle c/ responsável+prazo (FR-044).
- `accepted`: opção "aceitar" com justificativa + aceitação do dono (FR-045); residual registrado.
- `closed`: encerrado (residual tratado/aceito). `archived` é ortogonal (flag `is_archived`).

## Enums novos (em `settings.py`)

```python
class ThreatCategory(str, Enum): human, environmental, technical, organizational
class ThreatOrigin(str, Enum): deliberate, accidental, environmental
class VulnerabilityCategory(str, Enum): technical, physical, organizational, human, process
class RiskStatus(str, Enum): identified, assessed, in_treatment, accepted, closed
class RiskTreatmentOption(str, Enum): mitigate, accept, transfer, avoid
class RiskEventType(str, Enum): CREATE, UPDATE, PROBABILITY_CHANGE, IMPACT_CHANGE, LEVEL_CHANGE,
    OWNER_CHANGE, TREATMENT_DECISION, CONTROL_ADD, CONTROL_REMOVE, ACCEPTED, ARCHIVE,
    PLAN_SUBMITTED, PLAN_APPROVED
# DocType += risk_treatment_plan
# RISK_CODE_PREFIX = "RSK"; defaults da metodologia 5x5 (DEFAULT_RISK_METHODOLOGY)
```

## Validações (espelham FR-042..FR-046)

- `title`, `description`, `threat_id`, `vulnerability_id` obrigatórios (cenário).
- `assessed`+ exige `probability_level`, `impact_level`, `owner_user_id`.
- Sem ativos ⇒ `impact_level` manual obrigatório (não há CIA); `impact_is_override` não se aplica.
- Override de impacto exige `impact_override_reason`.
- `treatment_option == mitigate` exige ≥1 `risk_treatment_control` com `responsible_user_id` + `due_date`.
- `treatment_option == accept` exige `acceptance_reason` + `accepted_owner_user_id` (registrado por
  usuário `manage_risk`).
- Arquivar (risco/ameaça/vulnerabilidade) exige `archive_reason`; **sem exclusão física**.
- Mudanças relevantes (aceitação, mudança de nível, decisão de tratamento, aprovação) exigem `reason`
  e geram `risk_events`.
- Referências cross-tenant (ativo/ameaça/vuln/gap de outro tenant) ⇒ 404 genérico.
