from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["data"]["status"] == "healthy"
    assert payload["data"]["services"]["api"] == "up"
    assert "meta" in payload
    assert payload["meta"]["source_type"] == "SYSTEM"
    assert payload["error"] is None
