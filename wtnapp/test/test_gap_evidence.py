import json
import uuid

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceVersion
from wtnapp.services.gap_seed_service import adopt_seed
from wtnapp.settings import GapStatus


def _configure_storage(monkeypatch, tmp_path, *, max_bytes=128):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", max_bytes)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf", ".png", ".txt", ".zip"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def _seed_gap(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    item = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    seed["assessment"] = assessment
    seed["item"] = item
    return seed


def _headers(org_headers, user, org):
    return org_headers(user.email, org.id)


def _upload(client, item_id, headers, *, filename="policy.pdf", content=b"policy evidence", classification="uso_interno"):
    return client.post(
        f"/gap/assessment/items/{item_id}/evidences",
        headers=headers,
        data={"classification": classification, "description": "Documento de evidencia"},
        files={"file": (filename, content, "application/pdf")},
    )


def test_upload_creates_evidence_version_hash_event_audit_and_keeps_item_status(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-upload")
    item = seed["item"]
    item.status = GapStatus.not_meet
    db.commit()

    resp = _upload(client, item.id, _headers(org_headers, seed["admin"], seed["org"]))

    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["assessment_item_id"] == str(item.id)
    assert payload["classification"] == "uso_interno"
    assert payload["file_name"] == "policy.pdf"
    assert payload["hash_algorithm"] == "sha256"
    assert payload["content_hash"] == "388911fba5f7bf053a680a5cabefe6fe1d023bf28eb74d0dccd99bfc21cc21d2"
    assert payload["can_download"] is True

    evidence = db.get(Evidence, uuid.UUID(payload["id"]))
    version = db.get(EvidenceVersion, uuid.UUID(payload["current_version_id"]))
    assert evidence.tenant_id == seed["org"].id
    assert version.version_number == 1
    assert version.storage_key not in json.dumps(payload)
    assert b"policy evidence" not in (tmp_path / version.storage_key).read_bytes()
    assert db.get(GapAssessmentItem, item.id).status == GapStatus.not_meet

    event = db.query(EvidenceEvent).filter_by(evidence_id=evidence.id, event_type="uploaded").one()
    assert event.details["classification"] == "uso_interno"
    audit = db.query(AuditLog).filter_by(operation="UPLOAD_EVIDENCE", entity_id=str(evidence.id)).one()
    assert "storage_key" not in json.dumps(audit.details)


def test_upload_rejects_invalid_files_classification_and_missing_key(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path, max_bytes=8)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-invalid")
    headers = _headers(org_headers, seed["admin"], seed["org"])
    item_id = seed["item"].id

    cases = [
        {"filename": "empty.pdf", "content": b"", "classification": "uso_interno", "status": 422},
        {"filename": "large.pdf", "content": b"x" * 9, "classification": "uso_interno", "status": 422},
        {"filename": "malware.exe", "content": b"x", "classification": "uso_interno", "status": 422},
        {"filename": "policy.pdf", "content": b"x", "classification": "segredo", "status": 422},
    ]
    for case in cases:
        resp = _upload(
            client,
            item_id,
            headers,
            filename=case["filename"],
            content=case["content"],
            classification=case["classification"],
        )
        assert resp.status_code == case["status"], resp.text

    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", "")
    resp = _upload(client, item_id, headers, content=b"x")
    assert resp.status_code == 503
    assert db.query(Evidence).filter_by(tenant_id=seed["org"].id).count() == 0


def test_view_gap_cannot_upload_and_manage_gap_can_upload(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-rbac")

    denied = _upload(client, seed["item"].id, _headers(org_headers, seed["client"], seed["org"]))
    assert denied.status_code == 403

    allowed = _upload(client, seed["item"].id, _headers(org_headers, seed["consultant"], seed["org"]))
    assert allowed.status_code == 201


def test_list_and_download_respect_classification_rules(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-download")
    admin_headers = _headers(org_headers, seed["admin"], seed["org"])
    view_headers = _headers(org_headers, seed["client"], seed["org"])
    item_id = seed["item"].id

    public_resp = _upload(client, item_id, admin_headers, filename="public.pdf", content=b"public", classification="publico")
    restricted_resp = _upload(
        client,
        item_id,
        admin_headers,
        filename="secret.pdf",
        content=b"secret",
        classification="restrito",
    )
    assert public_resp.status_code == 201
    assert restricted_resp.status_code == 201

    before_list_download_audits = db.query(AuditLog).filter_by(operation="DOWNLOAD_EVIDENCE").count()
    listed = client.get(f"/gap/assessment/items/{item_id}/evidences", headers=view_headers)
    assert listed.status_code == 200
    after_list_download_audits = db.query(AuditLog).filter_by(operation="DOWNLOAD_EVIDENCE").count()
    assert after_list_download_audits == before_list_download_audits
    by_name = {item["file_name"]: item for item in listed.json()}
    assert by_name["public.pdf"]["can_download"] is True
    assert by_name["secret.pdf"]["can_download"] is False

    public_download = client.get(
        f"/gap/assessment/items/{item_id}/evidences/{public_resp.json()['id']}/download",
        headers=view_headers,
    )
    assert public_download.status_code == 200
    assert public_download.content == b"public"

    restricted_download = client.get(
        f"/gap/assessment/items/{item_id}/evidences/{restricted_resp.json()['id']}/download",
        headers=view_headers,
    )
    assert restricted_download.status_code == 403

    admin_download = client.get(
        f"/gap/assessment/items/{item_id}/evidences/{restricted_resp.json()['id']}/download",
        headers=admin_headers,
    )
    assert admin_download.status_code == 200
    assert admin_download.content == b"secret"


def test_replace_inactivate_and_history_preserve_custody(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-history")
    admin_headers = _headers(org_headers, seed["admin"], seed["org"])
    view_headers = _headers(org_headers, seed["client"], seed["org"])
    item_id = seed["item"].id
    upload = _upload(client, item_id, admin_headers, filename="v1.pdf", content=b"v1", classification="uso_interno")
    evidence_id = upload.json()["id"]

    missing_classification = client.post(
        f"/gap/assessment/items/{item_id}/evidences/{evidence_id}/versions",
        headers=admin_headers,
        files={"file": ("v2.pdf", b"v2", "application/pdf")},
    )
    assert missing_classification.status_code == 422

    replace = client.post(
        f"/gap/assessment/items/{item_id}/evidences/{evidence_id}/versions",
        headers=admin_headers,
        data={"classification": "confidencial", "description": "Nova versao"},
        files={"file": ("v2.pdf", b"v2", "application/pdf")},
    )
    assert replace.status_code == 201, replace.text
    assert replace.json()["classification"] == "confidencial"

    history = client.get(f"/gap/assessment/items/{item_id}/evidences/{evidence_id}/history", headers=admin_headers)
    assert history.status_code == 200
    assert [version["version_number"] for version in history.json()["versions"]] == [2, 1]
    assert history.json()["versions"][0]["classification"] == "confidencial"

    forbidden_history = client.get(f"/gap/assessment/items/{item_id}/evidences/{evidence_id}/history", headers=view_headers)
    assert forbidden_history.status_code == 403

    removed = client.request(
        "DELETE",
        f"/gap/assessment/items/{item_id}/evidences/{evidence_id}",
        headers=admin_headers,
        json={"reason": "Substituida por pacote de auditoria."},
    )
    assert removed.status_code == 204

    listed = client.get(f"/gap/assessment/items/{item_id}/evidences", headers=view_headers)
    assert listed.status_code == 200
    assert listed.json() == []

    history_after_remove = client.get(
        f"/gap/assessment/items/{item_id}/evidences/{evidence_id}/history",
        headers=admin_headers,
    )
    assert history_after_remove.status_code == 200
    assert history_after_remove.json()["evidence"]["status"] == "inactive"
    event_types = {event["event_type"] for event in history_after_remove.json()["events"]}
    assert {"uploaded", "replaced", "inactivated"}.issubset(event_types)


def test_evidence_audit_details_do_not_expose_content_storage_key_or_paths(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "gap-evidence-audit")
    headers = _headers(org_headers, seed["admin"], seed["org"])
    upload = _upload(client, seed["item"].id, headers, content=b"very sensitive body")
    evidence_id = upload.json()["id"]
    client.get(f"/gap/assessment/items/{seed['item'].id}/evidences/{evidence_id}/download", headers=headers)

    serialized = json.dumps(
        [log.details for log in db.query(AuditLog).filter(AuditLog.entity_type == "gap_evidence").all()],
        default=str,
    )
    assert "very sensitive body" not in serialized
    assert "storage_key" not in serialized
    assert str(tmp_path) not in serialized
