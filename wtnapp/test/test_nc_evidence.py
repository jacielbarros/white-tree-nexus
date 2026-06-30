"""Feature 015 / US4 — Evidências em NC/ação via o repositório transversal da 5a (alvos novos)."""

from cryptography.fernet import Fernet

from wtnapp import settings
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
    return seed


def _upload(client, h, target_type, target_id):
    return client.post("/evidence", headers=h, data={"classification": "uso_interno", "target_type": target_type, "target_id": str(target_id)}, files={"file": ("e.pdf", b"prova", "application/pdf")})


def test_attach_evidence_to_nc_and_action(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    seed = _seed(db, gap_seed_factory, "nc-ev")
    h = org_headers(seed["admin"].email, seed["org"].id)
    nc_id = client.post("/nonconformities", headers=h, json={"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}).json()["id"]
    action_id = client.post(f"/nonconformities/{nc_id}/actions", headers=h, json={"description": "a", "responsible_member_id": str(seed["admin"].id)}).json()["id"]

    # alvos novos do vínculo polimórfico da 5a
    assert _upload(client, h, "nonconformity", nc_id).status_code == 201
    assert _upload(client, h, "corrective_action", action_id).status_code == 201

    # aparecem no repositório central filtrando por alvo
    by_nc = client.get("/evidence", headers=h, params={"target_type": "nonconformity"}).json()
    assert any(any(l["target_id"] == nc_id for l in e["links"]) for e in by_nc)


def test_cannot_attach_to_other_tenant_nc(client, db, gap_seed, gap_seed_factory, org_headers, monkeypatch, tmp_path):
    _configure_storage(monkeypatch, tmp_path)
    a = _seed(db, gap_seed_factory, "nc-ev-a")
    b = _seed(db, gap_seed_factory, "nc-ev-b")
    ha = org_headers(a["admin"].email, a["org"].id)
    hb = org_headers(b["admin"].email, b["org"].id)
    nc_a = client.post("/nonconformities", headers=ha, json={"origin": "incident", "title": "NC", "description": "d", "severity": "menor"}).json()["id"]

    # Org B anexando a NC da Org A → 404 (alvo não existe no tenant de B)
    assert _upload(client, hb, "nonconformity", nc_a).status_code == 404
