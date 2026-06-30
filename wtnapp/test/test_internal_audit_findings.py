"""Feature 014 / US5 — Constatações com tipo, vínculo, evidência e promovibilidade."""

import uuid

from cryptography.fernet import Fernet

from wtnapp import settings
from wtnapp.models.gap_assessment_model import GapAssessment, GapAssessmentItem
from wtnapp.services.gap_seed_service import adopt_seed


def _configure_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "FIELD_ENCRYPTION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "EVIDENCE_STORAGE_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "EVIDENCE_MAX_FILE_BYTES", 256)
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_EXTENSIONS", {".pdf"})
    monkeypatch.setattr(settings, "EVIDENCE_ALLOWED_MIME_TYPES", set())


def _seed(db, gap_seed_factory, slug):
    seed = gap_seed_factory(slug)
    adopt_seed(db, seed["org"].id, "2022.1")
    db.commit()
    assessment = db.query(GapAssessment).filter_by(tenant_id=seed["org"].id).first()
    seed["item"] = db.query(GapAssessmentItem).filter_by(assessment_id=assessment.id).first()
    return seed


def _audit(client, headers, auditor_id):
    program_id = client.post("/internal-audit/programs", headers=headers, json={"name": "Prog"}).json()["id"]
    return client.post("/internal-audit/audits", headers=headers, json={
        "program_id": program_id, "title": "Aud", "scope": "s", "criteria": "c",
        "auditor_member_id": str(auditor_id),
    }).json()["id"]


def test_findings_types_and_promotable_flag(client, db, gap_seed, gap_seed_factory, org_headers):
    seed = _seed(db, gap_seed_factory, "ia-find")
    h = org_headers(seed["admin"].email, seed["org"].id)
    audit_id = _audit(client, h, seed["admin"].id)

    cases = {
        "conforme": False, "nc_maior": True, "nc_menor": True,
        "oportunidade_melhoria": False, "observacao": False,
    }
    for ftype, promotable in cases.items():
        resp = client.post(f"/internal-audit/audits/{audit_id}/findings", headers=h, json={
            "finding_type": ftype, "title": f"F {ftype}", "description": "achado",
            "target_type": "gap_item", "target_id": str(seed["item"].id),
        })
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["promotable"] is promotable
        assert body["nonconformity_ref"] is None  # reservado p/ 5b, vazio aqui


def test_attach_evidence_to_finding_and_lifecycle(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed(db, gap_seed_factory, "ia-find-ev")
    h = org_headers(seed["admin"].email, seed["org"].id)
    audit_id = _audit(client, h, seed["admin"].id)

    finding = client.post(f"/internal-audit/audits/{audit_id}/findings", headers=h, json={
        "finding_type": "nc_menor", "title": "NC", "description": "desvio",
    }).json()
    fid = finding["id"]

    # anexa evidência via repositório transversal (target_type=audit_finding)
    up = client.post("/evidence", headers=h, data={"classification": "uso_interno", "target_type": "audit_finding", "target_id": fid}, files={"file": ("e.pdf", b"prova", "application/pdf")})
    assert up.status_code == 201, up.text

    listed = client.get(f"/internal-audit/audits/{audit_id}/findings", headers=h).json()
    target = next(f for f in listed if f["id"] == fid)
    assert [l["target_type"] for l in target["evidence_links"]] == ["audit_finding"]

    # editar: muda tipo para observação → deixa de ser promovível
    upd = client.put(f"/internal-audit/findings/{fid}", headers=h, json={"finding_type": "observacao", "title": "NC", "description": "desvio"})
    assert upd.status_code == 200 and upd.json()["promotable"] is False

    # remoção lógica → some da lista ativa
    assert client.delete(f"/internal-audit/findings/{fid}", headers=h).status_code == 204
    assert fid not in {f["id"] for f in client.get(f"/internal-audit/audits/{audit_id}/findings", headers=h).json()}
