"""Polish T053 — headers de segurança aplicados a todas as respostas."""


def test_security_headers_present_on_responses(client):
    resp = client.get("/health")
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["referrer-policy"] == "no-referrer"
    # CSP_ENABLED é true por padrão; /health não é caminho de docs.
    assert "default-src 'self'" in resp.headers["content-security-policy"]
    # HSTS é opt-in (default false) — não deve aparecer fora de produção HTTPS.
    assert "strict-transport-security" not in resp.headers


def test_csp_exempt_on_docs(client):
    resp = client.get("/openapi.json")
    assert resp.status_code == 200
    assert "content-security-policy" not in resp.headers
