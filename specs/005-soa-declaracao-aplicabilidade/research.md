# Phase 0 — Research: Statement of Applicability (SoA)

Decisões técnicas que resolvem o Technical Context do [plan.md](plan.md). As 4 decisões de produto já
fixadas no `/speckit.clarify` estão na seção *Clarifications* da [spec.md](spec.md) e são insumo aqui.

---

## D1. Consolidação a partir da avaliação corrente do Gap Analysis

**Decision**: A SoA é gerada/atualizada por um serviço `soa_consolidation_service` que lê a
**avaliação corrente** (`gap_assessment` + `gap_assessment_item` join `gap_catalog_item` filtrando
`dimension == annex_a`) da mesma organização e materializa um `SoaItem` por controle do Anexo A.
A consolidação é **aditiva e idempotente**:
- Controle novo (sem `SoaItem`) ⇒ cria item pré-preenchido a partir do Gap.
- Controle já existente ⇒ **não sobrescreve** campos editados manualmente; a divergência é derivada
  na leitura (ver D2).
- Mapeamento de status (decisão do clarify): `meets→implemented`, `partial→in_progress`,
  `not_meet→not_started`, `not_applicable→not_applicable`, `not_filled→` (sem status). Aplicabilidade:
  `not_applicable ⇒ applicable=False`; qualquer outro ⇒ `applicable=True`.
- Herdados do Gap: aplicabilidade, `exclusion_justification`, status (mapeado), `responsible`,
  `deadline`. **Razões de inclusão** são exclusivas da SoA (preenchidas manualmente).

**Rationale**: a avaliação corrente já tem todos os campos de forma consultável; a SoA congela via seu
próprio versionamento (Documento Controlado), então não precisa ler baselines congeladas do Gap.
Aditivo/idempotente espelha o padrão consolidado da adoção de catálogo do Módulo 2.

**Alternatives considered**: consolidar de uma **baseline aprovada** do Gap (rejeitado no clarify —
mais auditável porém mais atrito e parsing de snapshot); **sobrescrever** na reconsolidação (rejeitado:
violaria FR-010, perderia edição manual).

---

## D2. Detecção de divergência por valor vivo (sem snapshot por campo)

**Decision**: A divergência é **computada na leitura**, comparando os campos consolidados do `SoaItem`
(aplicabilidade, `exclusion_justification`, status, `responsible`, `deadline`) com o **valor vivo
atual** do `gap_assessment_item` vinculado (aplicando o mapeamento de status do D1). Não há colunas de
snapshot por campo. A resposta da SoA inclui, por item, um bloco `divergence` listando os campos
divergentes com `{ soa_value, gap_value }`. A **reconciliação** (`POST /soa/items/{id}/reconcile`)
aplica o valor vivo do Gap ao campo — apenas por ação explícita do usuário (FR-011).

**Rationale**: zero custo de armazenamento; "divergente" passa a significar "a SoA não reflete o Gap
atual", que é exatamente o que o usuário quer para manter sincronia. O vínculo `SoaItem →
gap_assessment_item_id` torna a comparação O(1) por item (~93 itens, volume trivial).

**Alternatives considered**: snapshot por campo na consolidação (rejeitado no clarify — mais tabelas/
colunas; "divergente" passaria a significar "editei desde a consolidação", menos útil).

---

## D3. SoA como Documento Controlado + assinatura opcional (reuso)

**Decision**: Reusar `controlled_document_service`:
- `submit_review(db, soa)` → `draft_status = in_review`.
- `approve_document(..., doc_type=DocType.soa, snapshot_factory=...)` → cria `DocumentVersion`
  imutável (gatilho append-only existente), aponta `soa.current_version_id`, volta `draft_status` a
  `draft`. Estende `DocType` com `soa`.
- `list_versions` / `is_superseded` reaproveitados para listar/qualificar versões.
- **Aprovação restrita** a `approve_soa` (Admin da organização). Aprovar sem revisão ⇒ 409 (já é o
  comportamento do serviço). Aprovar SoA **incompleta** ⇒ 422 (ver D5).
- **Assinatura avançada opcional** (decisão do clarify): após aprovar, o emissor pode assinar via
  `signature_service` (reusa `FormSignature`/OTP do Motor 003), selando a integridade da versão.
  Sem assinatura, a versão aprovada continua válida.

**Rationale**: o padrão de Documento Controlado já entrega versão imutável, cadeia elaborado/revisado/
aprovado, classificação, datas e `content_snapshot` — exatamente o que a SoA precisa. Espelha a
baseline do Gap (Módulo 2), inclusive a assinatura opcional.

**Alternatives considered**: tabela de versões própria da SoA (rejeitado: duplicaria `document_versions`
e seu gatilho append-only); assinatura obrigatória (rejeitado no clarify).

---

## D4. Geração de PDF a partir do snapshot da versão (reportlab)

**Decision**: `soa_export_service.render_pdf(version)` gera o PDF **a partir do `content_snapshot`** da
`DocumentVersion` selecionada (não do rascunho), usando **reportlab** (pure-Python, sem libs nativas —
seguro no Windows do projeto). Endpoint `GET /soa/versions/{id}/export` retorna `application/pdf`
(stream), exigindo `view_soa`, e **registra auditoria** (FR-017). O PDF traz cabeçalho do Documento
Controlado (identificador, versão, classificação, datas, aprovador) + tabela dos controles.

**Rationale**: gerar do snapshot imutável garante "corresponde exatamente à versão" (FR-015/SC-004) e
auditabilidade server-side. reportlab evita as dependências nativas do weasyprint (GTK), inviáveis no
ambiente Windows atual.

**Alternatives considered**: print-to-PDF no navegador (rejeitado: sem garantia de fidelidade ao
snapshot nem trilha server-side); weasyprint/wkhtmltopdf (rejeitado: deps nativas problemáticas no
Windows).

---

## D5. Validação de completude antes da aprovação

**Decision**: Na aprovação (`POST /soa/approve`), validar (SC-002): todo controle **aplicável** tem ≥1
**razão de inclusão tipada**; todo controle **não aplicável** tem `exclusion_justification`. Se houver
pendências, retornar **422** com a lista de `ref_code` incompletos (sem vazar conteúdo). Edição
individual (`PUT /soa/items/{id}`) também valida a regra do próprio item (aplicável⇒razão;
N/A⇒justificativa) com 422.

**Rationale**: a SoA aprovada é o artefato de auditoria; não pode ser emitida incompleta. Validar tanto
no item (cedo) quanto na aprovação (gate final) cobre edição parcial e garante o invariante na emissão.

**Alternatives considered**: validar só no item (rejeitado: permitiria aprovar com itens nunca tocados);
validar só na aprovação (rejeitado: feedback tardio ao usuário).

---

## D6. Razões de inclusão tipadas (multi-valor)

**Decision**: `SoaInclusionReason` enum: `risk_treatment | legal | contractual | best_practice`. Um
`SoaItem` aplicável pode ter **uma ou mais** razões — armazenadas como **JSON array** de valores do
enum (`inclusion_reasons`), mais um texto livre complementar (`inclusion_note`). Validação: aplicável ⇒
`len(inclusion_reasons) >= 1`.

**Rationale**: a norma admite múltiplas razões (ex.: risco + legal); JSON array é simples, sem tabela
de junção, coerente com o uso de JSON já presente no projeto (ex.: `fields_snapshot`/`answers` do 003).
Volume trivial (≤4 valores por item).

**Alternatives considered**: tabela de junção `soa_item_inclusion_reason` (rejeitado: over-engineering
para ≤4 enums); coluna única de uma razão (rejeitado: a norma permite múltiplas).

---

## Síntese de reuso (não reinventar)

| Necessidade | Reusa |
|---|---|
| Versão imutável + ciclo de vida + snapshot | `services/controlled_document_service.py` + `document_versions` (+ `DocType.soa`) |
| Assinatura avançada opcional na emissão | `services/signature_service.py` + `FormSignature`/OTP (Motor 003) |
| Origem dos dados (Anexo A avaliado) | `gap_assessment` + `gap_assessment_item` + `gap_catalog_item` (Módulo 2) |
| Isolamento | `helpers/tenant_scope.py` (`scoped_query`) + RLS |
| RBAC | `helpers/permissions.py` (+ `view_soa`, `manage_soa`, `approve_soa`) |
| Auditoria | `services/audit_service.py` |
| Acesso por classificação | `helpers/classification_access.py` (Módulo 1) |
| Rastreabilidade reversa | campo `soa_ref` **já existente** em `gap_assessment_item` |
