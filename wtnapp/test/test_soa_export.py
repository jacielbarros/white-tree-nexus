"""US4 — exportação em PDF correspondendo exatamente à versão selecionada."""

import uuid


def _approve(client, headers, complete_soa, tenant_id):
    client.post("/soa/consolidate", headers=headers)
    complete_soa(tenant_id)
    client.post("/soa/submit-review", headers=headers)
    return client.post("/soa/approve", headers=headers, json={}).json()


def test_export_returns_pdf(client, soa_seed, org_headers, complete_soa):
    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    version = _approve(client, h, complete_soa, s["org"].id)

    resp = client.get(f"/soa/versions/{version['id']}/export", headers=h)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_export_reflects_version_not_draft(client, soa_seed, org_headers, complete_soa, db):
    from wtnapp.models.document_version_model import DocumentVersion

    s = soa_seed()
    h = org_headers(s["admin"].email, s["org"].id)
    version = _approve(client, h, complete_soa, s["org"].id)

    # edita o rascunho APÓS aprovar
    item = next(i for i in client.get("/soa", headers=h).json()["items"] if i["applicable"])
    client.put(f"/soa/items/{item['id']}", headers=h, json={"observations": "alterado depois da emissao"})

    # o snapshot da versão permanece imutável (export gera a partir dele)
    db.rollback()
    ver = db.get(DocumentVersion, uuid.UUID(version["id"]))
    assert all(
        (it.get("observations") or "") != "alterado depois da emissao"
        for it in ver.content_snapshot["items"]
    )
    # e o export continua respondendo 200 PDF
    resp = client.get(f"/soa/versions/{version['id']}/export", headers=h)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"
