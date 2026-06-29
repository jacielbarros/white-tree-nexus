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


def test_snapshot_carries_risk_kind_and_links(
    client, soa_seed, org_headers, complete_soa, link_risk_to_control, approve_risk_plan, db
):
    """Feature 013 — snapshot da versão carrega soa_kind, risk_links e origin por controle."""
    from wtnapp.models.document_version_model import DocumentVersion

    s = soa_seed()
    link_risk_to_control(s["org"], s["annex_items"][0].catalog_item_id, code="RSK-0030")
    approve_risk_plan(s["org"])
    h = org_headers(s["admin"].email, s["org"].id)
    version = _approve(client, h, complete_soa, s["org"].id)

    assert version["kind"] == "normative"
    db.rollback()
    ver = db.get(DocumentVersion, uuid.UUID(version["id"]))
    assert ver.content_snapshot["soa_kind"] == "normative"
    risk_item = next(it for it in ver.content_snapshot["items"] if it.get("risk_links"))
    assert risk_item["risk_links"][0]["risk_code"] == "RSK-0030"
    assert risk_item["origin"] in ("risk", "risk+manual")

    # PDF gerado a partir do snapshot enriquecido
    resp = client.get(f"/soa/versions/{version['id']}/export", headers=h)
    assert resp.status_code == 200 and resp.content[:4] == b"%PDF"


def test_render_pdf_fail_closed_on_bad_snapshot():
    """SEC-006 — falha de render não é silenciosa (levanta); não corrompe nada (read-only)."""
    import pytest

    from wtnapp.services import soa_export_service
    from wtnapp.settings import Classification, DocStatus

    class _BadVersion:
        identifier = "SOA-001"
        version_number = 1
        classification = Classification.uso_interno
        status = DocStatus.in_force
        change_nature = "Emissão"
        emitted_at = None
        next_review_at = None
        content_snapshot = {"items": [123]}  # elemento inválido quebra a montagem da tabela

    with pytest.raises(Exception):
        soa_export_service.render_pdf(_BadVersion())
