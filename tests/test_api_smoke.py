from fastapi.testclient import TestClient
import services.api.main as api

client = TestClient(api.app)

def test_health():
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json().get("status") == "ok"
