"""Comprobaciones del entorno WSGI, HTTPS y firmas entre workers."""
import pytest
from app import create_app

@pytest.fixture
def production(monkeypatch):
    monkeypatch.setenv("AGLUREP_ENV", "production")
    monkeypatch.setenv("AGLUREP_BEHIND_PROXY", "1")
    monkeypatch.setenv("AGLUREP_SECRET_KEY", "test-only-shared-production-key-0123456789")

@pytest.mark.parametrize("secret", [None, "", "short", " " * 32])
def test_production_requires_shared_secret(monkeypatch, secret):
    monkeypatch.setenv("AGLUREP_ENV", "production")
    if secret is None:
        monkeypatch.delenv("AGLUREP_SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("AGLUREP_SECRET_KEY", secret)
    with pytest.raises(RuntimeError, match="AGLUREP_SECRET_KEY"):
        create_app()

def test_local_boot_needs_no_environment(monkeypatch):
    for name in ("AGLUREP_ENV", "AGLUREP_BEHIND_PROXY", "AGLUREP_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    app = create_app()
    assert app.config["BEHIND_PROXY"] is False
    assert app.test_client().get("/health").get_json()["status"] == "ok"

def test_https_calculation_export_across_workers(production, payload):
    first, second = create_app().test_client(), create_app().test_client()
    base_url = "http://aglurep-test.onrender.com"
    headers = {"Origin": "https://aglurep-test.onrender.com", "X-Forwarded-Proto": "https"}
    assert first.get("/health", base_url=base_url).status_code == 200
    assert first.get("/", base_url=base_url).status_code == 200
    assert first.get("/static/app.js", base_url=base_url).status_code == 200
    response = first.post("/api/calculate", base_url=base_url, headers=headers, json=payload)
    assert response.status_code == 200
    snapshot = response.get_json()["snapshot"]
    exported = second.post("/api/export", base_url=base_url, headers=headers,
                           json={"snapshot": snapshot, "inputs": payload})
    assert exported.status_code == 200
    assert exported.mimetype == "text/csv"
    assert "attachment" in exported.headers["Content-Disposition"]

def test_proxy_does_not_allow_external_origin_or_host_override(production, payload):
    client = create_app().test_client()
    response = client.post("/api/calculate", base_url="http://aglurep-test.onrender.com", json=payload,
        headers={"Origin": "https://evil.example", "X-Forwarded-Proto": "https", "X-Forwarded-Host": "evil.example"})
    assert response.status_code == 422
    assert response.get_json()["errors"][0]["code"] == "invalid_origin"

def test_local_ignores_forwarded_proto_by_default(monkeypatch, payload):
    monkeypatch.delenv("AGLUREP_BEHIND_PROXY", raising=False)
    client = create_app().test_client()
    response = client.post("/api/calculate", json=payload,
        headers={"Origin": "https://localhost", "X-Forwarded-Proto": "https"})
    assert response.status_code == 422

def test_wsgi_entrypoint(production):
    import runpy
    app = runpy.run_module("wsgi")["app"]
    assert app.test_client().get("/health").status_code == 200
