# Quickstart — Diagnóstico e Contexto (Cláusula 4)

**Feature**: `002-diagnostico-contexto`. Como exercitar o módulo sobre a fundação 001. Sem novas
variáveis de `.env`. Assume backend (`uvicorn wtnapp.main:app`) e, opcionalmente, o frontend
(`wtnadmin`) rodando, com uma organização e um Admin da organização já criados (via bootstrap +
convite da fundação).

## Fluxo end-to-end (API)

```bash
# (pré) login de um Admin da organização → TOKEN; ORG = id da organização
H='-H "Authorization: Bearer $TOKEN" -H "X-Org-Context: $ORG" -H "Content-Type: application/json"'

# 1) Diagnóstico incremental (salvar rascunho)
curl -X PUT localhost:8000/context/diagnostic ... -d '{"status":"draft","sections":{"dados":{"dados_pessoais":true}}}'

# 2) Análise de Contexto (4.1): adicionar questões PESTEL/SWOT + impacto
curl -X POST localhost:8000/context/analysis/issues ... \
  -d '{"origin":"external","framework":"pestel","category":"Legal","description":"LGPD aplicável","impact":"alto"}'
curl -X POST localhost:8000/context/analysis/issues ... \
  -d '{"origin":"internal","framework":"swot","category":"Fraqueza","description":"Baixa maturidade documental","impact":"medio"}'
# enviar para revisão e aprovar (emite versão em vigor)
curl -X POST localhost:8000/context/analysis/submit-review ...
curl -X POST localhost:8000/context/analysis/approve ... \
  -d '{"classification":"uso_interno","next_review_at":"2027-06-19T00:00:00Z","change_nature":"Emissão inicial"}'
curl localhost:8000/context/analysis/versions ...   # histórico append-only

# 3) Partes Interessadas (4.2): Poder×Interesse → estratégia derivada
curl -X POST localhost:8000/context/stakeholders ... \
  -d '{"name":"Cliente enterprise","type":"external","power":"alto","interest":"alto"}'   # → strategy: manage_closely
curl -X POST localhost:8000/context/stakeholders/approve ... -d '{}'

# 4) Declaração de Escopo (4.3): itens + referências de versão + aprovar
curl -X POST localhost:8000/context/scope/items ... \
  -d '{"kind":"inclusion","description":"Plataforma SaaS e processos de suporte","justification":"Receita principal"}'
curl -X PUT localhost:8000/context/scope ... \
  -d '{"interfaces_dependencies":"Provedor de nuvem (AWS sa-east-1)","context_version_ref":"<vid>","stakeholder_version_ref":"<vid>"}'
curl -X POST localhost:8000/context/scope/approve ... -d '{}'

# 5) Visão consolidada e sugestões
curl localhost:8000/context/overview ...
curl localhost:8000/context/suggestions ...        # ex.: dados_pessoais=true ⇒ ANPD/titulares + LGPD
curl -X POST localhost:8000/context/suggestions/accept ... -d '{"suggestion_id":"<id>"}'
```

## Verificações-chave (mapeiam aos Success Criteria)

- **SC-002**: `PUT /context/diagnostic` parcial e novo `GET` ⇒ dados preservados (rascunho).
- **SC-004**: criar parte com `power=alto`,`interest=alto` ⇒ `strategy=manage_closely`; variar para
  cobrir keep_satisfied/keep_informed/monitor.
- **SC-003**: após `approve`, a versão aparece em `/versions` e não pode ser editada/apagada
  (append-only); aprovar nova versão mantém **1** em vigor e marca a anterior obsoleta.
- **SC-005**: `scope` referencia versões específicas de contexto e partes; revisar a Análise de
  Contexto sinaliza a referência do escopo como potencialmente desatualizada.
- **SC-006**: um Consultor (sem `approve_context_document`) recebe **403** ao chamar `/approve`.
- **SC-007**: `GET /context/suggestions` não persiste nada; só `/suggestions/accept` cria item.
- **SC-001 / SC-ISO**: token do tenant A com `X-Org-Context` do tenant B (ou acesso por id) ⇒ **404**
  genérico + audit.

## Testes (Definition of Done)

```bash
pytest wtnapp/test/test_tenant_isolation.py     # OBRIGATÓRIO — estendido p/ artefatos da Cláusula 4
pytest wtnapp/test/test_context_analysis.py wtnapp/test/test_stakeholders.py \
       wtnapp/test/test_scope.py wtnapp/test/test_document_version.py
cd wtnadmin && npm test
```

Cobertura mínima: happy path de cada artefato; derivação Poder×Interesse (todas as combinações);
versionamento append-only + "1 em vigor + rascunho paralelo"; aprovação negada sem papel (403);
sugestões nunca auto-aplicadas; **isolamento de tenant** dedicado para diagnóstico, análise,
partes, escopo e versões.

## Registro de validacao E2E

Validado em 2026-06-22 contra backend local `http://localhost:8000` e DB real, com o run
`20260622214313`.

- Fluxo API validado: diagnostico incremental, analise PESTEL/SWOT, partes interessadas com
  estrategia derivada, escopo com referencias de versao, submit/approve dos tres artefatos,
  historico de versoes, overview consolidado e aceite explicito de sugestao.
- Suite automatizada executada: `.\\.venv\\Scripts\\pytest.exe wtnapp/test/test_tenant_isolation.py
  wtnapp/test/test_diagnostic.py wtnapp/test/test_context_analysis.py
  wtnapp/test/test_stakeholders.py wtnapp/test/test_scope.py
  wtnapp/test/test_document_version.py wtnapp/test/test_overview_suggestions.py`.
- Resultado: `21 passed`.
