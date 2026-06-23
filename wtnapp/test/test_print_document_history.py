from wtnapp.models.context_analysis_model import ContextAnalysis
from wtnapp.test.print_document_helpers import configure_document_storage, headers_for, seed_context


def test_signed_history_marks_previous_version_obsolete(client, db, factory, org_headers, monkeypatch, tmp_path):
    configure_document_storage(monkeypatch, tmp_path)
    seed = seed_context(db, factory, "history-context")
    headers = headers_for(org_headers, seed["admin"], seed["org"])

    first_preview = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"}).json()
    first = client.post(
        f"/print-documents/previews/{first_preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": first_preview["snapshot_hash"]},
    ).json()

    analysis = db.query(ContextAnalysis).filter_by(tenant_id=seed["org"].id).first()
    analysis.methodology = "Metodo revisado."
    db.commit()

    second_preview = client.post("/print-documents/previews", headers=headers, json={"document_type": "context_report"}).json()
    second = client.post(
        f"/print-documents/previews/{second_preview['id']}/sign",
        headers=headers,
        json={"confirm_snapshot_hash": second_preview["snapshot_hash"]},
    ).json()

    history = client.get("/print-documents/signed?document_type=context_report", headers=headers)
    assert history.status_code == 200
    by_id = {row["id"]: row for row in history.json()}
    assert by_id[first["id"]]["status"] == "obsolete"
    assert by_id[second["id"]]["status"] == "signed"
