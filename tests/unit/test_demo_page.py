
from unittest.mock import patch

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service.demo_page import router


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret",
    )
    app.include_router(router)
    return TestClient(app)


def test_demo_giang_vien_co_quyen(client):
    with patch(
        "scorm_service.demo_page.kiem_tra_quyen_upload"
    ) as mock_permission:
        response = client.get("/demo")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    mock_permission.assert_called_once()


@pytest.mark.parametrize(
    ("status_code", "detail"),
    [
        (401, "Chua dang nhap"),
        (403, "Khong co quyen upload goi SCORM"),
    ],
)
def test_demo_tu_choi_khi_khong_co_quyen(
    client,
    status_code,
    detail,
):
    with patch(
        "scorm_service.demo_page.kiem_tra_quyen_upload",
        side_effect=HTTPException(
            status_code=status_code,
            detail=detail,
        ),
    ):
        response = client.get("/demo")

    assert response.status_code == status_code
    assert response.json()["detail"] == detail
