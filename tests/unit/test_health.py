from fastapi.testclient import TestClient
from app.main import app

def test_health() -> None:
    r = TestClient(app).get("/api/v1/health")
    assert r.json() == {"status": "ok"}