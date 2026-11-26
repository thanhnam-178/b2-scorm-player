
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service import api_packages
from scorm_service.importer import PackageRejected


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-session-secret-only-for-pytest",
    )
    @app.get("/test-login/{person_code}")
    def test_login(request: Request, person_code: str):
        request.session["authenticated"] = True
        request.session["person_code"] = person_code
        return {"authenticated": True}

    @app.get("/test-login-missing-code")
    def test_login_missing_code(request: Request):
        request.session["authenticated"] = True
        request.session.pop("person_code", None)
        return {"authenticated": True}

    app.include_router(api_packages.router)
    return TestClient(app)


@pytest.fixture
def mock_dependencies(monkeypatch):
    session = MagicMock()
    session.scalar.side_effect = [
        SimpleNamespace(role="teacher"),
        0,
    ]
    session.get.return_value = SimpleNamespace(person_type="staff")

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_packages,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )
    monkeypatch.setattr(api_packages, "next_version", lambda ten: 1)

    uploaded = []
    monkeypatch.setattr(
        api_packages,
        "upload_dir",
        lambda directory, prefix: uploaded.append((directory, prefix)),
    )

    imported = {
        "sha256": "a" * 64,
        "files": 2,
        "scorm_version": "1.2",
        "schemaversion": "1.2",
        "manifest_identifier": "INT1234-DEMO-12",
        "organization": {
            "identifier": "ORG1",
            "title": "Nhap mon lap trinh - goi mau",
        },
        "scos": [
            {
                "identifier": "RES1",
                "href": "index.html",
                "scorm_type": "sco",
                "files": ["index.html"],
                "item_identifier": "ITEM1",
                "title": "Bai mau",
            }
        ],
    }

    monkeypatch.setattr(
        api_packages,
        "import_package",
        lambda zip_path, dest_dir: imported,
    )

    def fake_flush():
        # Giả lập ID do PostgreSQL cấp sau flush.
        added = session.add.call_args.args[0]
        added.id = 123

    session.flush.side_effect = fake_flush

    return SimpleNamespace(
        session=session,
        uploaded=uploaded,
        imported=imported,
    )


def test_upload_goi_scorm_thanh_cong(client, mock_dependencies):
    client.get("/test-login/GV001")
    fixture = Path("tests/fixtures/INT1234-demo-scorm12.zip")

    with fixture.open("rb") as file:
        response = client.post(
            "/api/v1/packages",
            files={
                "file": (
                    "INT1234-demo-scorm12.zip",
                    file,
                    "application/zip",
                )
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert data["id"] == 123
    assert data["package"] == "INT1234-demo-scorm12"
    assert data["version"] == 1
    assert data["path"] == "INT1234-demo-scorm12/v1"
    assert data["scorm_version"] == "1.2"
    assert data["scos"][0]["identifier"] == "RES1"

    session = mock_dependencies.session
    session.add.assert_called_once()
    session.flush.assert_called_once()

    package_version = session.add.call_args.args[0]
    assert package_version.package == "INT1234-demo-scorm12"
    assert package_version.version == 1
    assert package_version.storage_prefix == "INT1234-demo-scorm12/v1"
    assert len(package_version.scos) == 1

    sco = package_version.scos[0]
    assert sco.identifier == "RES1"
    assert sco.title == "Bai mau"
    assert sco.href == "index.html"
    assert sco.position == 0
    assert sco.params == {
        "item_identifier": "ITEM1",
        "scorm_type": "sco",
        "files": ["index.html"],
    }

    assert len(mock_dependencies.uploaded) == 1
    uploaded_dir, uploaded_prefix = mock_dependencies.uploaded[0]
    assert uploaded_dir.name == "noi-dung"
    assert uploaded_prefix == "INT1234-demo-scorm12/v1"


def test_upload_goi_khong_hop_le_tra_400(client, monkeypatch):
    session = MagicMock()
    session.get.return_value = SimpleNamespace(person_type="staff")

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_packages,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )

    client.get("/test-login/GV001")
    def reject_package(zip_path, dest_dir):
        raise PackageRejected("Goi SCORM khong hop le")

    monkeypatch.setattr(api_packages, "import_package", reject_package)

    response = client.post(
        "/api/v1/packages",
        files={
            "file": (
                "goi-loi.zip",
                b"not-a-valid-package",
                "application/zip",
            )
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Goi SCORM khong hop le"


def test_upload_trung_phien_ban_tra_409(client, monkeypatch):
    session = MagicMock()
    session.scalar.side_effect = [
        SimpleNamespace(role="teacher"),
        0,
    ]
    session.get.return_value = SimpleNamespace(person_type="staff")

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_packages,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )

    client.get("/test-login/GV001")
    monkeypatch.setattr(api_packages, "next_version", lambda ten: 1)
    monkeypatch.setattr(
        api_packages,
        "import_package",
        lambda zip_path, dest_dir: {
            "sha256": "a" * 64,
            "files": 2,
            "scorm_version": "1.2",
            "schemaversion": "1.2",
            "manifest_identifier": "TEST",
            "organization": {},
            "scos": [
                {
                    "identifier": "RES1",
                    "href": "index.html",
                    "scorm_type": "sco",
                    "files": ["index.html"],
                    "item_identifier": "ITEM1",
                    "title": "Bai mau",
                }
            ],
        },
    )

    def raise_integrity_error():
        raise api_packages.IntegrityError(
            "INSERT",
            {},
            Exception("duplicate"),
        )

    session.flush.side_effect = raise_integrity_error

    upload_called = []
    monkeypatch.setattr(
        api_packages,
        "upload_dir",
        lambda directory, prefix: upload_called.append(prefix),
    )

    response = client.post(
        "/api/v1/packages",
        files={
            "file": (
                "goi-trung.zip",
                b"fake-zip",
                "application/zip",
            )
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Trung so phien ban, hay tai lai"
    assert upload_called == []


def test_upload_chua_dang_nhap_tra_401(client):
    response = client.post(
        "/api/v1/packages",
        files={
            "file": (
                "goi-test.zip",
                b"fake-zip",
                "application/zip",
            )
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Chua dang nhap"


def test_sinh_vien_upload_goi_scorm_bi_tu_choi(client, monkeypatch):
    session = MagicMock()
    session.get.return_value = SimpleNamespace(person_type="student")

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_packages,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )

    import_package_mock = MagicMock()
    monkeypatch.setattr(api_packages, "import_package", import_package_mock)

    client.get("/test-login/SV000002")

    response = client.post(
        "/api/v1/packages",
        files={
            "file": (
                "goi-test.zip",
                b"fake-zip",
                "application/zip",
            )
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Khong co quyen upload goi SCORM"
    import_package_mock.assert_not_called()


def test_upload_thieu_person_code_tra_401(client):
    client.get("/test-login-missing-code")

    response = client.post(
        "/api/v1/packages",
        files={
            "file": (
                "goi-test.zip",
                b"fake-zip",
                "application/zip",
            )
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Phien dang nhap khong hop le"
    )