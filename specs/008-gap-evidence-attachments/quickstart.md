# Quickstart: Anexos/Evidencias na Matriz do Gap Analysis (Feature 008)

Guia de implementacao e validacao. Esta feature vem depois da Feature 007; a UI deve manter separadas
"Evidencias esperadas" (orientacao textual) e "Evidencias anexadas" (arquivos reais do tenant).

## Pre-requisitos

- Feature 004 Gap Analysis implementada (`gap_assessment_item` tenant-scoped).
- Feature 007 Gap Guidance implementada (`evidencias_esperadas` no painel).
- Backend e frontend funcionando:

```bash
uvicorn wtnapp.main:app --reload
cd wtnadmin
npm start
```

## Configuracao

Adicionar `python-multipart` ao `requirements.txt` se ainda estiver ausente; FastAPI exige essa
dependencia para processar `multipart/form-data`.

Confirmar `FIELD_ENCRYPTION_KEY` com uma chave Fernet valida (urlsafe-base64 de 32 bytes). Upload de
evidencia deve falhar de forma fail-closed se a chave estiver ausente/invalida.

Adicionar/confirmar defaults em `wtnapp/settings.py`:

```text
EVIDENCE_STORAGE_DIR=./evidence_store/
EVIDENCE_MAX_FILE_BYTES=20971520
EVIDENCE_ALLOWED_EXTENSIONS=.pdf,.png,.jpg,.jpeg,.webp,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.zip,.7z
```

## Backend: ordem sugerida

1. **Settings/enums**: adicionar `GapEvidenceStatus`, `GapEvidenceEventType` e configuracoes de
   storage/limite/tipos permitidos.
2. **Storage util**: criar `wtnapp/utils/evidence_storage.py` com:
   - validacao de arquivo vazio/tamanho/extensao;
   - hash SHA-256 do conteudo original;
   - cifragem Fernet antes de persistir em disco e decifragem no download;
   - escrita em arquivo temporario e rename final do conteudo cifrado;
   - leitura/download por `storage_key` sem expor path;
   - nenhuma exposicao de path interno.
3. **Modelos**: criar `wtnapp/models/gap_evidence_model.py` com `GapEvidence`,
   `GapEvidenceVersion`, `GapEvidenceEvent` e triggers append-only para versoes/eventos.
4. **Migration**: criar Alembic revision para as 3 tabelas, indices, RLS PostgreSQL e triggers
   SQLite/PostgreSQL.
5. **Schemas**: criar `wtnapp/schemas/gap_evidence_schema.py`.
6. **Router**: criar `wtnapp/routers/gap_evidence.py`:
   - `GET /gap/assessment/items/{item_id}/evidences`
   - `POST /gap/assessment/items/{item_id}/evidences`
   - `GET /gap/assessment/items/{item_id}/evidences/{evidence_id}/download`
   - `POST /gap/assessment/items/{item_id}/evidences/{evidence_id}/versions`
   - `DELETE /gap/assessment/items/{item_id}/evidences/{evidence_id}`
   - `GET /gap/assessment/items/{item_id}/evidences/{evidence_id}/history`
7. **Main/model registry**: registrar router em `wtnapp/main.py` e modelos em `wtnapp/models/__init__.py`.

## Backend: testes obrigatorios

Criar `wtnapp/test/test_gap_evidence.py`:

- upload valido cria evidencia, versao 1, hash SHA-256, evento e audit;
- listagem com `view_gap` mostra metadados ativos/correntes e nao gera audit de conteudo;
- multiplas evidencias no mesmo item aparecem individualmente;
- arquivo vazio, grande demais e extensao invalida sao recusados sem criar evidencia valida;
- existencia de evidencia nao altera status/prioridade do item;
- download de `publico`/`uso_interno` funciona com `view_gap`;
- download de `confidencial`/`restrito` exige `manage_gap`;
- substituicao exige classificação obrigatória, cria nova versao e lista principal mostra apenas a corrente;
- inativacao oculta da lista principal e preserva historico;
- historico/inativas exigem `manage_gap`;
- audit log nao contem conteudo, storage_key ou path interno.
- arquivo em disco esta cifrado e o hash registrado corresponde ao conteudo decifrado/original.

Criar `wtnapp/test/test_tenant_isolation_gap_evidence.py`:

- usuario do tenant B nao lista, baixa, substitui, inativa nem infere evidencia do tenant A;
- tentativa cross-tenant retorna resposta generica e gera audit;
- Super Admin precisa de contexto explicito e opera apenas um tenant por vez.

Comandos:

```bash
pytest wtnapp/test/test_gap_evidence.py wtnapp/test/test_tenant_isolation_gap_evidence.py
alembic upgrade head
```

## Frontend: implementacao

Editar `wtnadmin/src/app/pages/gap-analysis/gap-analysis.ts`:

- Ao selecionar item, carregar `GET /gap/assessment/items/{item_id}/evidences`.
- No painel lateral, apos "Evidencias esperadas", exibir secao separada "Evidencias anexadas".
- Estado vazio: "Nenhuma evidencia anexada ainda."
- Para cada evidencia: titulo/nome, descricao curta quando houver, classificacao, tamanho, tipo,
  autor/data, hash curto e acao de download quando permitido.
- Se `canManage()`, exibir acao "Adicionar evidencia" com arquivo, descricao e classificacao
  obrigatoria default `uso_interno`.
- Para `manage_gap`, disponibilizar historico/substituir/inativar conforme UX compacta do painel; substituição deve pré-preencher a classificação atual e exigir confirmação antes do envio.
- Nao alterar automaticamente status do item apos upload.

Editar `wtnadmin/src/app/core/models.ts` com tipos `GapEvidenceSummary`, `GapEvidenceHistory` e
`Classification` se ainda nao estiver exportado de forma reutilizavel.

Testes em `gap-analysis.spec.ts`:

- renderiza "Evidencias esperadas" e "Evidencias anexadas" como secoes separadas;
- estado vazio aparece sem bloquear avaliacao;
- botao de upload aparece apenas com `manage_gap`;
- upload monta `FormData` com `file`, `description`, `classification`;
- substituicao/inativacao nao aparecem para usuario sem `manage_gap`; substituição envia `FormData` com `file`, `description` e `classification`.

Comandos:

```bash
cd wtnadmin
npm test
```

## Validacao manual

1. Login em `http://localhost:4200`.
2. Abrir `Gap Analysis - Matriz`.
3. Selecionar um item.
4. Confirmar que o painel mostra:
   - Orientacao de avaliacao;
   - Evidencias esperadas;
   - Evidencias anexadas.
5. Anexar um PDF pequeno com classificacao `Uso interno`.
6. Ver a evidencia aparecer na lista do item.
7. Baixar a evidencia e conferir audit no backend.
8. Substituir por nova versao confirmando a classificação e verificar que a lista principal mostra apenas a versao corrente.
9. Inativar e confirmar que some da lista principal, mas aparece no historico para `manage_gap`.

## Validacao executada em 2026-06-22

- Frontend: `npm.cmd test -- --watch=false` em `wtnadmin/` passou com 19 arquivos e 108 testes.
- Backend: `.\\.venv\\Scripts\\pytest.exe wtnapp/test/test_gap_evidence_storage.py wtnapp/test/test_gap_evidence_model.py wtnapp/test/test_gap_evidence_migration.py wtnapp/test/test_gap_evidence.py wtnapp/test/test_tenant_isolation_gap_evidence.py` passou com 16 testes.
- Dependencia instalada na venv local para validar upload multipart: `python-multipart==0.0.32`.
- Alembic: `.\\.venv\\Scripts\\alembic.exe upgrade head` passou aplicando `84c5c822d7b1 -> c1d2e3f4a509`; segunda execucao passou como no-op, validando idempotencia via Alembic. Catalogo PostgreSQL conferido: revision `c1d2e3f4a509`, default booleano `encrypted_default true`, RLS ligado/forcado nas tres tabelas e triggers append-only em `gap_evidence_version`/`gap_evidence_event`.
- Responsivo: Chrome headless/CDP em `localhost:4200` com payloads mockados de evidencias longas validou o painel lateral da matriz em desktop `1440x900`, tablet `1024x900`, emulacao mobile `390x844` e viewports CSS estreitos `768`, `390` e `320` px; nao houve overflow horizontal em metadados, hashes, botoes de evidencia, upload, selects ou textareas. Observacao: abaixo de aproximadamente `520px`, o shell/sidebar global gera overflow horizontal fora do escopo do painel de evidencias.

## Definition of Done

- [ ] Migration cria tabelas, indices, RLS e triggers append-only.
- [ ] Upload/download validam tenant, RBAC, classificacao e tamanho/tipo.
- [ ] Arquivos de evidencia sao cifrados em repouso via `FIELD_ENCRYPTION_KEY`.
- [ ] Audit log cobre acoes sensiveis sem dados sensiveis.
- [ ] Historico, versoes anteriores e inativas restritos a `manage_gap`.
- [ ] UI diferencia visualmente evidencias esperadas de anexadas.
- [ ] Testes backend e frontend passam, incluindo isolamento de tenant.
