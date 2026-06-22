"""Orientação de Avaliação por Item (Feature 007) — leitura, edição admin, trilha, propagação."""

import uuid

import pytest
from sqlalchemy import text

from wtnapp.settings import Role


def _super_admin(factory, login, email="root@platform.com"):
    user = factory.user(email, super_admin=True)
    return login(user.email)


# ── Leitura (US1) + Legenda (US3) ─────────────────────────────────────────────


def test_guidance_read_returns_items_and_legend(client, soa_seed, org_headers):
    s = soa_seed("gd")
    resp = client.get("/gap/guidance", headers=org_headers(s["admin"].email, s["org"].id))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    items = {i["ref_code"]: i for i in body["items"]}
    assert "A.8.24" in items
    assert items["A.8.24"]["referencia"] == "ISO/IEC 27001:2022 — A.8.24"
    assert items["A.8.24"]["objetivo"]  # objetivo já vem do seed
    assert len(items["A.8.24"]["como_avaliar"]) >= 1
    assert len(items["A.8.24"]["evidencias_esperadas"]) >= 1
    # cláusula tem referência de cláusula
    assert items["4"]["referencia"] == "ISO/IEC 27001:2022 — Cláusula 4"

    # Legenda global: 4 status + 4 prioridade (T026)
    assert len(body["legend"]["status"]) == 4
    assert len(body["legend"]["priority"]) == 4
    labels = {e["label"] for e in body["legend"]["status"]}
    assert {"Não atende", "Atende Parcialmente", "Atende Totalmente", "Não Aplicável"} == labels


def test_guidance_read_requires_view_gap(client, factory, org_headers):
    org = factory.org("gd-noperm", "GD NoPerm")
    guest = factory.user("guest@gd-noperm.com")
    factory.membership(guest, org, Role.guest_collaborator)  # sem view_gap
    resp = client.get("/gap/guidance", headers=org_headers(guest.email, org.id))
    assert resp.status_code == 403


# ── Edição admin (US2) ────────────────────────────────────────────────────────


def _seed_item_id(client, headers, ref_code):
    items = client.get("/gap/guidance", headers=headers).json()["items"]
    return next(i["seed_item_id"] for i in items if i["ref_code"] == ref_code)


def test_admin_edit_item_persists_with_trail_and_audit(client, soa_seed, factory, login, org_headers):
    s = soa_seed("gd-edit")
    ha = org_headers(s["admin"].email, s["org"].id)
    sid = _seed_item_id(client, ha, "A.8.24")
    sa_h = _super_admin(factory, login, "root-edit@platform.com")

    resp = client.put(f"/gap/guidance/items/{sid}", headers=sa_h, json={
        "objetivo": "Objetivo editado pelo admin",
        "como_avaliar": ["Pergunta nova A", "Pergunta nova B"],
    })
    assert resp.status_code == 200, resp.text
    assert resp.json()["objetivo"] == "Objetivo editado pelo admin"
    assert resp.json()["como_avaliar"] == ["Pergunta nova A", "Pergunta nova B"]

    # nova leitura reflete
    again = next(i for i in client.get("/gap/guidance", headers=ha).json()["items"] if i["seed_item_id"] == sid)
    assert again["objetivo"] == "Objetivo editado pelo admin"

    # trilha append-only registrou antes→depois
    events = client.get("/gap/guidance/events", headers=sa_h).json()
    fields = {e["field"] for e in events if e["target_id"] == sid}
    assert {"objetivo", "como_avaliar"} <= fields


def test_admin_edit_propagates_to_all_orgs(client, soa_seed, factory, login, org_headers):
    a = soa_seed("gd-pa")
    b = soa_seed("gd-pb")
    ha = org_headers(a["admin"].email, a["org"].id)
    sid = _seed_item_id(client, ha, "A.5.1")
    sa_h = _super_admin(factory, login, "root-prop@platform.com")

    client.put(f"/gap/guidance/items/{sid}", headers=sa_h, json={"nota": "Nota canônica X"})

    hb = org_headers(b["admin"].email, b["org"].id)
    item_b = next(i for i in client.get("/gap/guidance", headers=hb).json()["items"] if i["seed_item_id"] == sid)
    assert item_b["nota"] == "Nota canônica X"


def test_load_seed_does_not_overwrite_admin_edit(client, soa_seed, factory, login, org_headers, db):
    s = soa_seed("gd-noover")
    ha = org_headers(s["admin"].email, s["org"].id)
    sid = _seed_item_id(client, ha, "A.8.24")
    sa_h = _super_admin(factory, login, "root-noover@platform.com")
    client.put(f"/gap/guidance/items/{sid}", headers=sa_h, json={"objetivo": "Editado — não sobrescrever"})

    # roda o seed de novo (simula startup)
    from wtnapp.services.gap_seed_service import load_seed
    db.rollback()
    load_seed(db)
    db.commit()

    item = next(i for i in client.get("/gap/guidance", headers=ha).json()["items"] if i["seed_item_id"] == sid)
    assert item["objetivo"] == "Editado — não sobrescrever"


def test_legend_edit_by_admin(client, soa_seed, factory, login, org_headers):
    s = soa_seed("gd-leg")
    ha = org_headers(s["admin"].email, s["org"].id)
    legend = client.get("/gap/guidance", headers=ha).json()["legend"]
    entry_id = legend["status"][0]["id"]
    sa_h = _super_admin(factory, login, "root-leg@platform.com")

    resp = client.put(f"/gap/guidance/legend/{entry_id}", headers=sa_h, json={"definition": "Definição revisada"})
    assert resp.status_code == 200
    assert resp.json()["definition"] == "Definição revisada"


def test_guidance_event_is_append_only(client, soa_seed, factory, login, org_headers, db):
    s = soa_seed("gd-ao")
    ha = org_headers(s["admin"].email, s["org"].id)
    sid = _seed_item_id(client, ha, "A.6.3")
    sa_h = _super_admin(factory, login, "root-ao@platform.com")
    client.put(f"/gap/guidance/items/{sid}", headers=sa_h, json={"nota": "gera evento"})

    db.rollback()
    with pytest.raises(Exception):
        db.execute(text("UPDATE gap_guidance_event SET field = 'x'"))
        db.commit()
    db.rollback()
    with pytest.raises(Exception):
        db.execute(text("DELETE FROM gap_guidance_event"))
        db.commit()
    db.rollback()
