"""T010, T031 — Isolamento de tenant para o motor de formularios (Feature 003).

Toda query de dominio DEVE ser filtrada por tenant_id. Acesso cross-tenant → 404/403.
"""

import pytest


def _h(login, email, org_id):
    h = login(email)
    h["X-Org-Context"] = str(org_id)
    return h


@pytest.fixture
def two_orgs(factory, form_seed):
    """Org A (form_seed) + org B com admin proprio."""
    org_b = factory.org("org-b", "Org B")
    admin_b = factory.user("admin@org-b.com", full_name="Admin B")
    factory.membership(admin_b, org_b)
    return {"org_a": form_seed["org"], "admin_a": form_seed["admin"],
            "org_b": org_b, "admin_b": admin_b}


def _create_template(client, headers, title="T"):
    r = client.post(
        "/form-templates",
        json={"kind": "generic", "title": title, "schema": []},
        headers=headers,
    )
    assert r.status_code == 201, r.text
    return r.json()


class TestTemplateIsolation:
    def test_template_not_visible_to_other_tenant(self, client, login, two_orgs, form_outbox):
        h_a = _h(login, two_orgs["admin_a"].email, two_orgs["org_a"].id)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)
        tpl_a = _create_template(client, h_a, "Template da Org A")

        # Org B nao vê o template da Org A
        r = client.get("/form-templates", headers=h_b)
        ids = [t["id"] for t in r.json()]
        assert tpl_a["id"] not in ids

    def test_cross_tenant_get_template_returns_404(self, client, login, two_orgs, form_outbox):
        h_a = _h(login, two_orgs["admin_a"].email, two_orgs["org_a"].id)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)
        tpl_a = _create_template(client, h_a)

        r = client.get(f"/form-templates/{tpl_a['id']}", headers=h_b)
        assert r.status_code == 404

    def test_cross_tenant_patch_template_returns_404(self, client, login, two_orgs, form_outbox):
        h_a = _h(login, two_orgs["admin_a"].email, two_orgs["org_a"].id)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)
        tpl_a = _create_template(client, h_a)

        r = client.patch(f"/form-templates/{tpl_a['id']}", json={"title": "HACK"}, headers=h_b)
        assert r.status_code == 404


class TestAssignmentIsolation:
    def _create_and_assign(self, client, login, two_orgs, form_seed, form_outbox):
        h_a = _h(login, two_orgs["admin_a"].email, two_orgs["org_a"].id)
        tpl = _create_template(client, h_a)
        a = client.post(
            "/form-assignments",
            json={
                "template_id": tpl["id"],
                "respondent_user_id": str(form_seed["client"].id),
            },
            headers=h_a,
        ).json()
        return a, h_a

    def test_assignment_not_visible_cross_tenant(self, client, login, two_orgs, form_seed, form_outbox):
        a, _ = self._create_and_assign(client, login, two_orgs, form_seed, form_outbox)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)

        r = client.get("/form-assignments", headers=h_b)
        ids = [x["id"] for x in r.json()]
        assert a["id"] not in ids

    def test_cross_tenant_get_assignment_returns_404(self, client, login, two_orgs, form_seed, form_outbox):
        a, _ = self._create_and_assign(client, login, two_orgs, form_seed, form_outbox)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)

        r = client.get(f"/form-assignments/{a['id']}", headers=h_b)
        assert r.status_code == 404

    def test_cross_tenant_cancel_returns_404(self, client, login, two_orgs, form_seed, form_outbox):
        a, _ = self._create_and_assign(client, login, two_orgs, form_seed, form_outbox)
        h_b = _h(login, two_orgs["admin_b"].email, two_orgs["org_b"].id)

        r = client.post(f"/form-assignments/{a['id']}/cancel", headers=h_b)
        assert r.status_code == 404

    def test_token_only_serves_its_assignment(self, client, login, two_orgs, form_outbox):
        """Token da org A nao revela dados da org B."""
        h_a = _h(login, two_orgs["admin_a"].email, two_orgs["org_a"].id)
        tpl = _create_template(client, h_a)
        client.post(
            "/form-assignments",
            json={"template_id": tpl["id"], "respondent_email": "extA@a.com"},
            headers=h_a,
        )
        token_a = form_outbox[-1]["token"]

        # Token da org A com contexto da org B ainda resolve apenas a atribuicao da org A
        r = client.get(f"/forms/respond/{token_a}")
        assert r.status_code == 200
        assert r.json()["respondent_email"] == "extA@a.com"
