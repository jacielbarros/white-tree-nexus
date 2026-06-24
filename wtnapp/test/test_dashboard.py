"""Dashboard de Conformidade (Feature 006) — agregação, KPIs, estados, RBAC e fail-open."""

from datetime import datetime, timedelta, timezone

from wtnapp.helpers.tenant_scope import OrgContext, Principal
from wtnapp.models.document_version_model import DocumentVersion
from wtnapp.models.scope_model import ScopeStatement
from wtnapp.services import dashboard_service
from wtnapp.services.dashboard_service import build_dashboard
from wtnapp.services.gap_metrics_service import compute_dashboard
from wtnapp.settings import Classification, DocStatus, DocType, GapPriority, GapStatus, Role


def _ctx(user, org, role) -> OrgContext:
    principal = Principal(user=user, jti="t", exp_ts=0, tenant_ids=[org.id], is_super_admin=False)
    return OrgContext(principal=principal, tenant_id=org.id, role=role, is_super_admin=False, membership=None)


# ── T010 — happy path + correção de agregação ────────────────────────────────


def test_dashboard_happy_path_and_kpis(client, soa_seed, org_headers, db):
    seed = soa_seed("dash")
    assessment = seed["assessment"]
    annex = seed["annex_items"]  # [0]=meets, [1]=partial, [2]=not_applicable
    annex[1].priority = GapPriority.critical  # 1 gap crítico (partial + priority critical)
    db.commit()

    body = client.get("/dashboard", headers=org_headers(seed["admin"].email, seed["org"].id)).json()
    by_id = {c["id"]: c for c in body["cards"]}

    # Cards reais + placeholders
    assert set(by_id) == {"context", "gap", "soa", "action_plan", "evidence"}
    assert by_id["action_plan"]["placeholder"] is True
    assert by_id["evidence"]["placeholder"] is True

    # Gap metrics ainda mostram aderencia entre avaliados; o KPI executivo do dashboard
    # considera controles nao avaliados como nao conformes para evitar falso 100%.
    metrics = compute_dashboard(db, seed["org"].id, assessment.id)
    assert metrics["overall_adherence"] == 0.75
    assert body["kpis"]["overall_adherence"] == 0.0163
    assert body["kpis"]["controls_evaluated"] == 3      # 3 controles do Anexo A avaliados
    assert body["kpis"]["controls_total"] == 93         # Anexo A (C2)
    assert body["kpis"]["critical_gaps"] == 1           # priority==critical, não not_meet (C1)
    assert body["kpis"]["modules_total"] == 3
    assert body["kpis"]["modules_approved"] == 0

    # Gap card: rascunho (sem versão aprovada), progresso = completude
    assert by_id["gap"]["status"] == "draft"
    assert by_id["gap"]["not_started"] is False
    assert by_id["gap"]["progress_pct"] == round(metrics["completeness"] * 100, 1)


def test_dashboard_compliance_penalizes_unassessed_controls(client, soa_seed, org_headers, db):
    """Dois controles Atende e o restante Nao avaliado nao podem virar 100% no dashboard executivo."""
    seed = soa_seed("dash-unassessed")
    annex = seed["annex_items"]
    annex[0].status = annex[1].status = GapStatus.meets
    annex[2].status = GapStatus.not_filled
    db.commit()

    body = client.get("/dashboard", headers=org_headers(seed["admin"].email, seed["org"].id)).json()

    assert compute_dashboard(db, seed["org"].id, seed["assessment"].id)["overall_adherence"] == 1.0
    assert body["kpis"]["overall_adherence"] == 0.0215


def test_critical_gaps_counts_priority_not_status(client, soa_seed, org_headers, db):
    """C1: critical_gaps conta priority==critical, NÃO a quantidade de not_meet."""
    seed = soa_seed("dash-crit")
    annex = seed["annex_items"]
    # annex[0] meets→não é gap; deixamos sem nenhum priority critical.
    db.commit()
    body = client.get("/dashboard", headers=org_headers(seed["admin"].email, seed["org"].id)).json()
    assert body["kpis"]["critical_gaps"] == 0


# ── T011 — estados, RBAC, gating, fail-open, revisão vencida ──────────────────


def test_modules_not_started(client, gap_seed_factory, org_headers):
    s = gap_seed_factory("dash-empty")  # org sem contexto, sem gap adotado, sem SoA
    body = client.get("/dashboard", headers=org_headers(s["admin"].email, s["org"].id)).json()
    by_id = {c["id"]: c for c in body["cards"]}
    for mod in ("context", "gap", "soa"):
        assert by_id[mod]["status"] == "not_started"
        assert by_id[mod]["not_started"] is True
        assert by_id[mod]["progress_pct"] is None
        assert by_id[mod]["responsible"] is None
        assert by_id[mod]["deadline"] is None
    assert body["kpis"]["controls_total"] == 93
    assert body["kpis"]["controls_evaluated"] == 0
    assert body["adherence_trend"] is None


def test_rbac_denied_for_guest(client, soa_seed, org_headers, factory):
    s = soa_seed("dash-rbac")
    guest = factory.user("guest@dash-rbac.com", full_name="Guest")
    factory.membership(guest, s["org"], Role.guest_collaborator)
    resp = client.get("/dashboard", headers=org_headers(guest.email, s["org"].id))
    assert resp.status_code == 403


def test_card_gating_by_module_permission(db, soa_seed):
    """Guest (view_context, sem view_gap/view_soa) — só o card de Contexto entra (SEC-002)."""
    s = soa_seed("dash-gate")
    resp = build_dashboard(db, _ctx(s["admin"], s["org"], Role.guest_collaborator))
    ids = {c.id.value for c in resp.cards if not c.placeholder}
    assert ids == {"context"}


def test_fail_open_per_card(db, soa_seed, monkeypatch):
    s = soa_seed("dash-failopen")

    def _boom(*a, **k):
        raise RuntimeError("boom")

    monkeypatch.setattr(dashboard_service, "_gap_card", _boom)
    resp = build_dashboard(db, _ctx(s["admin"], s["org"], Role.org_admin))
    by_id = {c.id.value: c for c in resp.cards}
    assert by_id["gap"].status.value == "error"
    assert by_id["soa"].status.value != "error"
    assert by_id["context"].status.value != "error"


def test_context_review_overdue(db, soa_seed):
    s = soa_seed("dash-overdue")
    org = s["org"]
    scope = ScopeStatement(tenant_id=org.id)
    db.add(scope)
    db.flush()
    past = datetime.now(timezone.utc) - timedelta(days=10)
    version = DocumentVersion(
        tenant_id=org.id,
        document_type=DocType.scope_statement,
        document_id=scope.id,
        identifier="SGSI-DOC-SCOPE-STATEMENT",
        version_number=1,
        status=DocStatus.in_force,
        classification=Classification.uso_interno,
        next_review_at=past,
        change_nature="Emissao inicial",
        content_snapshot={},
    )
    db.add(version)
    db.flush()
    scope.current_version_id = version.id
    db.commit()

    resp = build_dashboard(db, _ctx(s["admin"], org, Role.org_admin))
    ctx_card = next(c for c in resp.cards if c.id.value == "context")
    assert ctx_card.status.value == "needs_review"
    assert ctx_card.overdue is True


# ── T018 — US2: conformidade ao longo do tempo (adherence_trend) ──────────────


def _baseline(org_id, assessment_id, number, adherence):
    return DocumentVersion(
        tenant_id=org_id,
        document_type=DocType.gap_baseline,
        document_id=assessment_id,
        identifier="SGSI-DOC-GAP-BASELINE",
        version_number=number,
        status=DocStatus.in_force,
        classification=Classification.uso_interno,
        change_nature="Emissao inicial",
        content_snapshot={"dashboard": {"overall_adherence": adherence}},
    )


def test_adherence_trend_from_baselines(db, soa_seed):
    s = soa_seed("dash-trend")
    org, assessment = s["org"], s["assessment"]
    db.add(_baseline(org.id, assessment.id, 1, 0.45))
    db.add(_baseline(org.id, assessment.id, 2, 0.62))
    db.commit()

    resp = build_dashboard(db, _ctx(s["admin"], org, Role.org_admin))
    assert resp.adherence_trend is not None
    assert [p.adherence for p in resp.adherence_trend] == [0.45, 0.62]
    assert [p.version for p in resp.adherence_trend] == [1, 2]


def test_adherence_trend_none_with_single_baseline(db, soa_seed):
    s = soa_seed("dash-trend1")
    db.add(_baseline(s["org"].id, s["assessment"].id, 1, 0.5))
    db.commit()
    resp = build_dashboard(db, _ctx(s["admin"], s["org"], Role.org_admin))
    assert resp.adherence_trend is None
