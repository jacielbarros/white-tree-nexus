"""Feature 014 — Repositório transversal de evidências (US1/US2/US3).

Cobre upload+vínculo polimórfico, repositório/filtros, versionamento, cadeia de custódia e
acesso por classificação. Reusa o storage cifrado (Fernet) da Feature 008.
"""

import json
import uuid

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.asset_item_model import AssetItem
from wtnapp.models.audit_log_model import AuditLog
from wtnapp.models.evidence_model import Evidence, EvidenceEvent, EvidenceVersion
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
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


def _asset(db, org, user, *, code="ATV-9001", name="Servidor X"):
    asset = AssetItem(
        tenant_id=org.id, code=code, item_type="system", name=name,
        scope_status="in_scope", created_by=user.id,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def _upload(client, headers, target_type, target_id, *, filename="policy.pdf", content=b"policy evidence", classification="uso_interno", title=None):
    data = {"classification": classification, "target_type": target_type, "target_id": str(target_id)}
    if title:
        data["title"] = title
    return client.post("/evidence", headers=headers, data=data, files={"file": (filename, content, "application/pdf")})


# ───────────────────────────── US1 — anexar evidência ─────────────────────────────

def test_upload_to_gap_item_creates_version_hash_event_audit(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-up")
    item = seed["item"]
    item.status = GapStatus.not_meet
    db.commit()
    headers = org_headers(seed["admin"].email, seed["org"].id)

    resp = _upload(client, headers, "gap_item", item.id)
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["hash_algorithm"] == "sha256"
    assert payload["content_hash"] == "388911fba5f7bf053a680a5cabefe6fe1d023bf28eb74d0dccd99bfc21cc21d2"
    assert payload["can_download"] is True
    assert [(l["target_type"], l["target_id"]) for l in payload["links"]] == [("gap_item", str(item.id))]
    assert "storage_key" not in json.dumps(payload)

    evidence = db.get(Evidence, uuid.UUID(payload["id"]))
    version = db.get(EvidenceVersion, uuid.UUID(payload["current_version_id"]))
    assert evidence.tenant_id == seed["org"].id and version.version_number == 1
    assert b"policy evidence" not in (tmp_path / version.storage_key).read_bytes()  # cifrado em repouso

    types = {e.event_type for e in db.query(EvidenceEvent).filter_by(evidence_id=evidence.id)}
    assert {"uploaded", "linked"} <= types
    audit = db.query(AuditLog).filter_by(operation="UPLOAD_EVIDENCE", entity_id=str(evidence.id)).one()
    assert "storage_key" not in json.dumps(audit.details)
    # FR-010: anexar não altera o status do artefato-alvo
    assert db.get(GapAssessmentItem, item.id).status == GapStatus.not_meet


def test_upload_is_polymorphic_across_artifact_types(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-poly")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    asset = _asset(db, seed["org"], seed["admin"])

    r_gap = _upload(client, headers, "gap_item", seed["item"].id)
    r_asset = _upload(client, headers, "asset", asset.id, filename="ev2.pdf")
    assert r_gap.status_code == 201 and r_asset.status_code == 201, (r_gap.text, r_asset.text)
    assert r_asset.json()["links"][0]["target_type"] == "asset"


def test_upload_rejects_unknown_target(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-badtarget")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    resp = _upload(client, headers, "asset", uuid.uuid4())
    assert resp.status_code == 404, resp.text


def test_upload_rejects_invalid_files_and_classification(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path, max_bytes=8)
    seed = _seed_gap(db, gap_seed_factory, "ev-invalid")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    tid = seed["item"].id
    cases = [
        ("empty.pdf", b"", "uso_interno", 422),
        ("large.pdf", b"x" * 9, "uso_interno", 422),
        ("malware.exe", b"x", "uso_interno", 422),
        ("policy.pdf", b"x", "segredo", 422),
    ]
    for filename, content, classification, expected in cases:
        resp = _upload(client, headers, "gap_item", tid, filename=filename, content=content, classification=classification)
        assert resp.status_code == expected, (filename, resp.status_code, resp.text)
    assert db.query(Evidence).filter_by(tenant_id=seed["org"].id).count() == 0


def test_missing_encryption_key_is_fail_closed(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", "")
    seed = _seed_gap(db, gap_seed_factory, "ev-nokey")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    resp = _upload(client, headers, "gap_item", seed["item"].id)
    assert resp.status_code == 503, resp.text


def test_confidential_download_requires_manage(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-conf")
    admin_h = org_headers(seed["admin"].email, seed["org"].id)
    client_h = org_headers(seed["client"].email, seed["org"].id)
    up = _upload(client, admin_h, "gap_item", seed["item"].id, classification="confidencial")
    assert up.status_code == 201, up.text
    eid = up.json()["id"]
    # client tem apenas view_evidence → metadados sim, conteúdo não
    assert client.get(f"/evidence/{eid}", headers=client_h).json()["can_download"] is False
    assert client.get(f"/evidence/{eid}/download", headers=client_h).status_code == 403
    assert client.get(f"/evidence/{eid}/download", headers=admin_h).status_code == 200


# ───────────────────────────── US2 — repositório central + vínculos ─────────────────────────────

def test_repository_search_filters_and_extra_link(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-search")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    asset = _asset(db, seed["org"], seed["admin"])
    eid = _upload(client, headers, "gap_item", seed["item"].id, title="Politica de Acesso", classification="confidencial").json()["id"]
    _upload(client, headers, "asset", asset.id, title="Outro")

    # filtro por classificação
    r = client.get("/evidence", headers=headers, params={"classification": "confidencial"})
    assert {e["id"] for e in r.json()} == {eid}
    # filtro por texto
    r = client.get("/evidence", headers=headers, params={"q": "Politica"})
    assert [e["title"] for e in r.json()] == ["Politica de Acesso"]
    # filtro por alvo
    r = client.get("/evidence", headers=headers, params={"target_type": "asset"})
    assert all(any(l["target_type"] == "asset" for l in e["links"]) for e in r.json())

    # vincular a 2º artefato (1..N)
    link = client.post(f"/evidence/{eid}/links", headers=headers, json={"target_type": "asset", "target_id": str(asset.id)})
    assert link.status_code == 201, link.text
    detail = client.get(f"/evidence/{eid}", headers=headers).json()
    assert {l["target_type"] for l in detail["links"]} == {"gap_item", "asset"}
    # vínculo duplicado → 409
    assert client.post(f"/evidence/{eid}/links", headers=headers, json={"target_type": "asset", "target_id": str(asset.id)}).status_code == 409


# ───────────────────────────── US3 — versionamento + custódia ─────────────────────────────

def test_replace_keeps_history_and_versions_are_immutable(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-replace")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    eid = _upload(client, headers, "gap_item", seed["item"].id).json()["id"]
    v1 = db.query(EvidenceVersion).filter_by(evidence_id=uuid.UUID(eid), version_number=1).one()

    rep = client.post(f"/evidence/{eid}/versions", headers=headers, data={"classification": "uso_interno"}, files={"file": ("v2.pdf", b"second version", "application/pdf")})
    assert rep.status_code == 201, rep.text
    assert rep.json()["content_hash"] != v1.content_hash

    hist = client.get(f"/evidence/{eid}/history", headers=headers)
    assert hist.status_code == 200
    numbers = [v["version_number"] for v in hist.json()["versions"]]
    assert numbers == [2, 1]
    assert sum(1 for v in hist.json()["versions"] if v["is_current"]) == 1

    # imutabilidade: trigger append-only bloqueia UPDATE na versão antiga
    import pytest
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        db.query(EvidenceVersion).filter_by(id=v1.id).update({"size_bytes": 1})
        db.commit()
    db.rollback()


def test_inactivate_hides_from_default_search_but_keeps_history(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed_gap(db, gap_seed_factory, "ev-inact")
    headers = org_headers(seed["admin"].email, seed["org"].id)
    eid = _upload(client, headers, "gap_item", seed["item"].id).json()["id"]

    assert client.request("DELETE", f"/evidence/{eid}", headers=headers, json={"reason": "anexada por engano"}).status_code == 204
    assert eid not in {e["id"] for e in client.get("/evidence", headers=headers).json()}
    # filtro status=inactive (manage) revela
    r = client.get("/evidence", headers=headers, params={"status": "inactive"})
    assert eid in {e["id"] for e in r.json()}
    # histórico preserva e o registro não é apagado
    assert client.get(f"/evidence/{eid}/history", headers=headers).status_code == 200
    assert db.get(Evidence, uuid.UUID(eid)) is not None
