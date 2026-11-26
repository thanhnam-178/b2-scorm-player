from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    r = TestClient(app).get("/api/v1/health")
    assert r.json() == {"status": "ok"}

def test_trang_demo():
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert Path("src/scorm_service/static/demo.html").exists()