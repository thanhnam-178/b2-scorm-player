
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service import api_attempts
from scorm_service.models import (
    Enrollment,
    PackageVersion,
    Person,
    Section,
    SectionPackage,
)


@pytest.fixture
def client():
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-session-secret",
    )
    app.include_router(api_attempts.router)

    @app.get("/test-login")
    def test_login(request: Request):
        request.session["authenticated"] = True
        request.session["person_code"] = "SV001"
        return {"message": "ok"}

    return TestClient(app)


@pytest.fixture
def mock_dependencies(monkeypatch):
    session = MagicMock()

    section = SimpleNamespace(section_code="LHP001")

    person = SimpleNamespace(
        person_code="SV001",
        person_type="student",
    )

    enrollment = SimpleNamespace(
        status="registered",
        role="student",
    )
    section_package = SimpleNamespace(
        section_code="LHP001",
        package_version_id=1,
    )
    package_version = SimpleNamespace(
        id=1,
        status="ready",
        scorm_version="1.2",
    )

    scos = [
        SimpleNamespace(
            id=10,
            position=0,
            href="content/sco1.html",
        ),
        SimpleNamespace(
            id=11,
            position=1,
            href="content/sco2.html",
        ),
    ]

    def fake_get(model, key):
        data = {
            Section: section,
            Person: person,
            Enrollment: enrollment,
            SectionPackage: section_package,
            PackageVersion: package_version,
        }
        return data.get(model)

    session.get.side_effect = fake_get
    session.scalar.return_value = None
    session.scalars.return_value.all.return_value = scos

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_attempts,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )

    def fake_flush():
        for call in session.add.call_args_list:
            obj = call.args[0]
            if obj.__class__.__name__ == "Attempt":
                obj.id = 100

    session.flush.side_effect = fake_flush

    return SimpleNamespace(
        session=session,
        scos=scos,
        section=section,
        enrollment=enrollment,
        section_package=section_package,
        package_version=package_version,
    )

@pytest.fixture
def teacher_dependencies(monkeypatch):
    session = MagicMock()

    section = SimpleNamespace(section_code="LHP001")
    person = SimpleNamespace(
        person_code="GV001",
        person_type="staff",
    )
    enrollment = SimpleNamespace(
        status="registered",
        role="teacher",
    )
    package_version = SimpleNamespace(
        id=1,
        package="INT1234",
        version="1.0",
        scorm_version="1.2",
        status="ready",
    )
    section_package = SimpleNamespace(
        section_code="LHP001",
        package_version_id=1,
    )

    def fake_get(model, key):
        data = {
            Section: section,
            Person: person,
            Enrollment: enrollment,
            PackageVersion: package_version,
            SectionPackage: section_package,
        }
        return data.get(model)

    session.get.side_effect = fake_get
    session.scalar.return_value = enrollment
    session.execute.return_value.scalars.return_value.all.return_value = [
        package_version
    ]

    class FakeSessionContext:
        def __enter__(self):
            return session

        def __exit__(self, exc_type, exc_value, traceback):
            return False

    monkeypatch.setattr(
        api_attempts,
        "phien_lam_viec",
        lambda: FakeSessionContext(),
    )

    return SimpleNamespace(
        session=session,
        section=section,
        person=person,
        enrollment=enrollment,
        package_version=package_version,
        section_package=section_package,
    )

def test_tao_attempt_moi_thanh_cong(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["attempt_id"] == 100
    assert data["attempt_number"] == 1
    assert data["status"] == "in_progress"
    assert data["resumed"] is False

    assert len(data["sco_states"]) == 2
    assert data["sco_states"] == [
        {
            "sco_id": 10,
            "cmi_data": {
                "cmi.core.lesson_status": "not attempted",
            },
            "launch_url": (
                "/content/attempts/100/scos/10/content/sco1.html"
            ),
        },
        {
            "sco_id": 11,
            "cmi_data": {
                "cmi.core.lesson_status": "not attempted",
            },
            "launch_url": (
                "/content/attempts/100/scos/11/content/sco2.html"
            ),
        },
    ]

    session = mock_dependencies.session



    assert session.add.call_count == 3
    assert session.flush.call_count == 2

    attempt = session.add.call_args_list[0].args[0]

    assert attempt.section_code == "LHP001"
    assert attempt.person_code == "SV001"
    assert attempt.package_version_id == 1
    assert attempt.attempt_number == 1
    assert attempt.status == "in_progress"


def test_chua_dang_nhap_tra_401(client):
    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 401


def test_khong_co_quyen_dang_ky_lop_tra_403(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    mock_dependencies.session.get.side_effect = (
        lambda model, key: (
            None
            if model is Enrollment
            else {
                Section: mock_dependencies.section,
                SectionPackage: mock_dependencies.section_package,
                PackageVersion: mock_dependencies.package_version,
            }.get(model)
        )
    )

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 403



def test_tiep_tuc_attempt_dang_hoc(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    attempt_cu = SimpleNamespace(
        id=50,
        attempt_number=1,
        status="in_progress",
    )

    states_cu = [
        SimpleNamespace(
            sco_id=10,
            cmi_data={"cmi.core.lesson_status": "completed"},
        ),
        SimpleNamespace(
            sco_id=11,
            cmi_data={"cmi.core.lesson_status": "incomplete"},
        ),
    ]

    session = mock_dependencies.session
    session.scalar.return_value = attempt_cu

    ket_qua_scos = MagicMock()
    ket_qua_scos.all.return_value = mock_dependencies.scos

    ket_qua_states = MagicMock()
    ket_qua_states.all.return_value = states_cu

    session.scalars.side_effect = [
        ket_qua_scos,
        ket_qua_states,
    ]

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["attempt_id"] == 50
    assert data["attempt_number"] == 1
    assert data["status"] == "in_progress"
    assert data["resumed"] is True

    assert data["sco_states"] == [
        {
            "sco_id": 10,
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
            "launch_url": (
                "/content/attempts/50/scos/10/content/sco1.html"
            ),
        },
        {
            "sco_id": 11,
            "cmi_data": {
                "cmi.core.lesson_status": "incomplete",
            },
            "launch_url": (
                "/content/attempts/50/scos/11/content/sco2.html"
            ),
        },
    ]

    # Khong tao Attempt hoac CMI moi khi tiep tuc.
    session.add.assert_not_called()
    session.flush.assert_not_called()


@pytest.mark.parametrize(
    "trang_thai",
    ["completed", "passed", "failed"],
)
def test_hoc_lai_tao_attempt_moi(
    client,
    mock_dependencies,
    trang_thai,
):
    client.get("/test-login")

    attempt_cu = SimpleNamespace(
        id=50,
        attempt_number=1,
        status=trang_thai,
    )

    session = mock_dependencies.session
    session.scalar.return_value = attempt_cu

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["attempt_id"] == 100
    assert data["attempt_number"] == 2
    assert data["status"] == "in_progress"
    assert data["resumed"] is False

    assert len(data["sco_states"]) == 2

    # Mot Attempt moi va hai trang thai CMI moi.
    assert session.add.call_count == 3

    attempt_moi = session.add.call_args_list[0].args[0]

    assert attempt_moi.attempt_number == 2
    assert attempt_moi.status == "in_progress"



def test_khong_tim_thay_lop_hoc_phan_tra_404(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    mock_dependencies.session.get.side_effect = (
        lambda model, key: (
            None
            if model is Section
            else {
                Enrollment: mock_dependencies.enrollment,
                SectionPackage: mock_dependencies.section_package,
                PackageVersion: mock_dependencies.package_version,
            }.get(model)
        )
    )

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 404


def test_goi_chua_duoc_gan_vao_lop_tra_403(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    mock_dependencies.session.get.side_effect = (
        lambda model, key: (
            None
            if model is SectionPackage
            else {
                Section: mock_dependencies.section,
                Enrollment: mock_dependencies.enrollment,
                PackageVersion: mock_dependencies.package_version,
            }.get(model)
        )
    )

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 403


def test_goi_chua_san_sang_tra_409(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    mock_dependencies.package_version.status = "processing"

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 409


def test_goi_chua_co_sco_tra_409(
    client,
    mock_dependencies,
):
    client.get("/test-login")

    mock_dependencies.session.scalars.return_value.all.return_value = []

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 409


def test_gan_goi_thanh_cong(
    client,
    teacher_dependencies,
):
    get_ban_dau = teacher_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is SectionPackage:
            return None
        return get_ban_dau(model, key)

    teacher_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 200
    assert response.json() == {
        "message": "Gan goi SCORM thanh cong",
        "section_code": "LHP001",
        "package_version_id": 1,
    }

    teacher_dependencies.session.add.assert_called_once()


def test_gan_goi_da_ton_tai_khong_them_lai(
    client,
    teacher_dependencies,
):
    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 200
    teacher_dependencies.session.add.assert_not_called()


def test_gan_goi_khi_chua_dang_nhap_tra_401(
    client,
    teacher_dependencies,
):
    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Chua dang nhap"


def test_gan_goi_khi_khong_phai_giang_vien_tra_403(
    client,
    teacher_dependencies,
):
    teacher_dependencies.person.person_type = "student"

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Khong co quyen giang vien"


def test_gan_goi_khi_giang_vien_chua_duoc_phan_cong_tra_403(
    client,
    teacher_dependencies,
):
    teacher_dependencies.session.scalar.return_value = None

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Ban khong co quyen quan ly lop hoc phan nay"
    )


def test_gan_goi_khi_khong_tim_thay_lop_tra_404(
    client,
    teacher_dependencies,
):
    get_ban_dau = teacher_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is Section:
            return None
        return get_ban_dau(model, key)

    teacher_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Khong tim thay lop hoc phan"


def test_gan_goi_khi_khong_tim_thay_package_tra_404(
    client,
    teacher_dependencies,
):
    get_ban_dau = teacher_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is PackageVersion:
            return None
        return get_ban_dau(model, key)

    teacher_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Khong tim thay goi SCORM"


def test_gan_goi_khi_package_chua_san_sang_tra_409(
    client,
    teacher_dependencies,
):
    teacher_dependencies.package_version.status = "processing"

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Phien ban goi SCORM chua san sang"
    )

    teacher_dependencies.session.add.assert_not_called()


def test_lay_danh_sach_goi_thanh_cong(
    client,
    teacher_dependencies,
):
    client.get("/test-login")

    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 200
    assert response.json() == {
        "section_code": "LHP001",
        "total": 1,
        "packages": [
            {
                "id": 1,
                "package": "INT1234",
                "version": "1.0",
                "scorm_version": "1.2",
                "status": "ready",
            }
        ],
    }


def test_lay_danh_sach_goi_rong(
    client,
    teacher_dependencies,
):
    teacher_dependencies.session.execute.return_value.scalars.return_value.all.return_value = []

    client.get("/test-login")

    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 200
    assert response.json() == {
        "section_code": "LHP001",
        "total": 0,
        "packages": [],
    }


def test_lay_danh_sach_goi_khi_chua_dang_nhap_tra_401(
    client,
    teacher_dependencies,
):
    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Chua dang nhap"

def test_lay_danh_sach_goi_khi_khong_tim_thay_lop_tra_404(
    client,
    teacher_dependencies,
):
    get_ban_dau = teacher_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is Section:
            return None
        return get_ban_dau(model, key)

    teacher_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Khong tim thay lop hoc phan"


def test_lay_danh_sach_goi_khi_chua_dang_ky_lop_tra_403(
    client,
    teacher_dependencies,
):
    teacher_dependencies.session.scalar.return_value = None

    client.get("/test-login")

    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Ban khong co quyen xem goi SCORM cua lop nay"
    )


def test_lay_danh_sach_goi_khi_thieu_person_code_tra_401(
    client,
    teacher_dependencies,
):
    client.get("/test-login")

    def fake_login(request: Request):
        request.session["authenticated"] = True
        request.session.pop("person_code", None)
        return {"message": "ok"}

    client.app.add_api_route("/test-login-invalid", fake_login)

    client.get("/test-login-invalid")

    response = client.get(
        "/api/v1/sections/LHP001/packages"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Phien dang nhap khong hop le"


def test_go_bo_goi_thanh_cong(
    client,
    teacher_dependencies,
):
    client.get("/test-login")

    response = client.delete(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 200
    assert response.json()["message"] == (
        "Go goi SCORM khoi lop thanh cong"
    )
    teacher_dependencies.session.delete.assert_called_once_with(
        teacher_dependencies.section_package
    )


def test_go_bo_goi_chua_duoc_gan_tra_404(
    client,
    teacher_dependencies,
):
    teacher_dependencies.session.get.return_value = None

    get_ban_dau = teacher_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is SectionPackage:
            return None
        return get_ban_dau(model, key)

    teacher_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.delete(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Goi SCORM chua duoc gan vao lop"
    )


def test_go_bo_goi_khi_chua_dang_nhap_tra_401(
    client,
    teacher_dependencies,
):
    response = client.delete(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Chua dang nhap"


def test_go_bo_goi_khi_khong_phai_giang_vien_tra_403(
    client,
    teacher_dependencies,
):
    teacher_dependencies.person.person_type = "student"

    client.get("/test-login")

    response = client.delete(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Khong co quyen giang vien"
    )


def test_go_bo_goi_khi_giang_vien_chua_duoc_phan_cong_tra_403(
    client,
    teacher_dependencies,
):
    teacher_dependencies.session.scalar.return_value = None

    client.get("/test-login")

    response = client.delete(
        "/api/v1/sections/LHP001/packages/1"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Ban khong co quyen quan ly lop hoc phan nay"
    )


def test_tao_attempt_khi_goi_chua_duoc_gan_tra_403(
    client,
    mock_dependencies,
):
    get_ban_dau = mock_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is SectionPackage:
            return None
        return get_ban_dau(model, key)

    mock_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "Goi SCORM chua duoc gan vao lop hoc phan"
    )


def test_tao_attempt_khi_khong_tim_thay_goi_tra_404(
    client,
    mock_dependencies,
):
    get_ban_dau = mock_dependencies.session.get.side_effect

    def fake_get(model, key):
        if model is PackageVersion:
            return None
        return get_ban_dau(model, key)

    mock_dependencies.session.get.side_effect = fake_get

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Khong tim thay goi SCORM"


def test_tao_attempt_khi_attempt_cu_co_trang_thai_khong_hop_le(
    client,
    mock_dependencies,
):
    attempt_cu = SimpleNamespace(
        id=99,
        status="in_progress_invalid",
        attempt_number=1,
    )
    mock_dependencies.session.scalar.return_value = attempt_cu

    client.get("/test-login")

    response = client.post(
        "/api/v1/sections/LHP001/packages/1/attempts"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Trang thai Attempt khong hop le"
    )

