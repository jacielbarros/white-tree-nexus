from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _configure_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", 128)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf", ".txt"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def _seed_gap(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _headers(org_headers, user, org):
    return org_headers(user.email, org.id)


def _upload(client, item_id, headers):
    return client.post(
        f"/gap/assessment/items/{item_id}/evidences",
        headers=headers,
        data={"classification": "uso_interno"},
        files={"file": ("policy.pdf", b"tenant-a", "application/pdf")},
    )


def test_tenant_b_cannot_attach_list_download_replace_inactivate_or_view_history_for_tenant_a(
    client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path
):
    _configure_storage(monkeypatch, tmp_path)
    tenant_a = _seed_gap(db, gap_seed_factory, "gap-evidence-tenant-a")
    tenant_b = _seed_gap(db, gap_seed_factory, "gap-evidence-tenant-b")
    headers_a = _headers(org_headers, tenant_a["admin"], tenant_a["org"])
    headers_b = _headers(org_headers, tenant_b["admin"], tenant_b["org"])

    upload = _upload(client, tenant_a["item"].id, headers_a)
    assert upload.status_code == 201, upload.text
    evidence_id = upload.json()["id"]

    denied_upload = _upload(client, tenant_a["item"].id, headers_b)
    assert denied_upload.status_code == 404

    denied_list = client.get(f"/gap/assessment/items/{tenant_a['item'].id}/evidences", headers=headers_b)
    assert denied_list.status_code == 404

    denied_download = client.get(
        f"/gap/assessment/items/{tenant_a['item'].id}/evidences/{evidence_id}/download",
        headers=headers_b,
    )
    assert denied_download.status_code == 404

    denied_replace = client.post(
        f"/gap/assessment/items/{tenant_a['item'].id}/evidences/{evidence_id}/versions",
        headers=headers_b,
        data={"classification": "uso_interno"},
        files={"file": ("replacement.pdf", b"replacement", "application/pdf")},
    )
    assert denied_replace.status_code == 404

    denied_delete = client.request(
        "DELETE",
        f"/gap/assessment/items/{tenant_a['item'].id}/evidences/{evidence_id}",
        headers=headers_b,
        json={"reason": "cross tenant attempt"},
    )
    assert denied_delete.status_code == 404

    denied_history = client.get(
        f"/gap/assessment/items/{tenant_a['item'].id}/evidences/{evidence_id}/history",
        headers=headers_b,
    )
    assert denied_history.status_code == 404

    denied_audits = db.query(AuditLog).filter_by(
        tenant_id=tenant_b["org"].id,
        operation="EVIDENCE_ACCESS_DENIED",
        outcome="denied",
    ).all()
    assert denied_audits
    assert all(log.entity_id == str(tenant_a["item"].id) for log in denied_audits)
