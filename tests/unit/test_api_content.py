
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service import api_content, api_runtime_session


@pytest.fixture
def mock_session(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False

    attempt = SimpleNamespace(
        id=1,
        person_code="SV001",
        section_code="SEC001",
        package_version_id=10,
        status="in_progress",
    )
    enrollment = SimpleNamespace(
        status="registered",
        role="student",
    )
    person = SimpleNamespace(
        person_code="SV001",
        person_type="student",
    )
    sco = SimpleNamespace(
        id=100,
        package_version_id=10,
        href="content/index.html",
        params={
            "files": [
                "content/index.html",
                "content/style.css",
            ],
        },
    )
    package_version = SimpleNamespace(
        id=10,
        status="ready",
        scorm_version="1.2",
        storage_prefix="INT1234/v1",
    )
    state = SimpleNamespace(
        cmi_data={"cmi.core.lesson_status": "incomplete"},
        runtime_initialized=False,
        runtime_terminated=False,
    )

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    session.get.side_effect = fake_get
    session.scalar.return_value = state

    monkeypatch.setattr(
        api_content,
        "phien_lam_viec",
        lambda: session,
    )

    return session


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret",
    )

    @app.post("/test-login")
    def test_login(request: Request, data: dict):
        request.session["authenticated"] = True
        request.session["person_code"] = data["person_code"]
        return {"authenticated": True}

    app.include_router(api_content.router)

    return TestClient(app)


def dang_nhap(client, person_code="SV001"):
    client.post(
        "/test-login",
        json={"person_code": person_code},
    )


class FakeBody:
    def iter_chunks(self, chunk_size):
        yield b"<html>SCORM content</html>"


def test_phan_phoi_noi_dung_thanh_cong(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client)

    obj = {
        "Body": FakeBody(),
        "ContentType": "text/html; charset=utf-8",
    }

    get_object = MagicMock(return_value=obj)
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/index.html"
    )

    assert response.status_code == 200
    assert response.content == b"<html>SCORM content</html>"
    assert response.headers["content-type"] == "text/html; charset=utf-8"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["cache-control"] == "private, no-store"

    get_object.assert_called_once_with(
        "INT1234/v1/content/index.html"
    )


def test_phan_phoi_noi_dung_chua_dang_nhap_tra_401(
    client,
    monkeypatch,
):
    get_object = MagicMock()
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/index.html"
    )

    assert response.status_code == 401
    get_object.assert_not_called()


def test_phan_phoi_attempt_cua_nguoi_khac_tra_403(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client, person_code="SV002")

    get_object = MagicMock()
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/index.html"
    )

    assert response.status_code == 403
    get_object.assert_not_called()


@pytest.mark.parametrize(
    "path",
    [
        "../secret.txt",
        "content/../secret.txt",
        "/etc/passwd",
        r"content\secret.txt",
        "C:/secret.txt",
        "content//index.html",
        "content/./index.html",
        "",
        "https://example.com/file.html",
        "content/%00file.html",
    ],
)
def test_duong_dan_khong_hop_le_bi_chan(path):
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        api_content.chuan_hoa_duong_dan(path)

    assert exc_info.value.status_code == 400


def test_duong_dan_hop_le_duoc_chuan_hoa():
    assert (
        api_content.chuan_hoa_duong_dan("content/lesson/index.html")
        == "content/lesson/index.html"
    )


def test_khong_tim_thay_tep_minio_tra_404(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client)

    get_object = MagicMock(
        side_effect=ClientError(
            {
                "Error": {
                    "Code": "NoSuchKey",
                    "Message": "Not found",
                },
            },
            "GetObject",
        )
    )
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/style.css"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Khong tim thay tep SCORM"


def test_sco_khong_co_href_tra_404(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client)

    mock_session.get.side_effect = lambda model, key: (
        SimpleNamespace(
            id=100,
            package_version_id=10,
            href=None,
        )
        if model is api_runtime_session.Sco
        else {
            api_runtime_session.Attempt: SimpleNamespace(
                id=1,
                person_code="SV001",
                section_code="SEC001",
                package_version_id=10,
                status="in_progress",
            ),
            api_runtime_session.Enrollment: SimpleNamespace(
                status="registered",
                role="student",
            ),
            api_runtime_session.Person: SimpleNamespace(
                person_code="SV001",
                person_type="student",
            ),
            api_runtime_session.PackageVersion: SimpleNamespace(
                id=10,
                status="ready",
                scorm_version="1.2",
                storage_prefix="INT1234/v1",
            ),
        }.get(model)
    )

    get_object = MagicMock()
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/index.html"
    )

    assert response.status_code == 404
    get_object.assert_not_called()


def test_khong_duoc_doc_tep_ngoai_resource_cua_sco(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client)

    get_object = MagicMock()
    monkeypatch.setattr(
        api_content.storage,
        "get_object",
        get_object,
    )

    response = client.get(
        "/api/v1/content/attempts/1/scos/100/content/secret.html"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Tep khong thuoc tai nguyen cua SCO"
    )
    get_object.assert_not_called()