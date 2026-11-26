from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from scorm_service import api_runtime_session


@pytest.fixture
def mock_session(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.__exit__.return_value = False

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, state = du_lieu

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        if model is api_runtime_session.Enrollment:
            return enrollment
        return bang_du_lieu.get(model)

    session.get.side_effect = fake_get
    session.scalar.return_value = state
    session.scalars.return_value.all.return_value = [state]

    monkeypatch.setattr(
        api_runtime_session,
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

    app.include_router(api_runtime_session.router)

    return TestClient(app)

def dang_nhap(client, person_code="SV001"):
    client.post(
        "/test-login",
        json={"person_code": person_code},
    )


def tao_du_lieu_gia():
    attempt = SimpleNamespace(
        id=1,
        person_code="SV001",
        section_code="SEC001",
        package_version_id=10,
        status="in_progress",
        completed_at=None,
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
        href="index.html",
    )

    package_version = SimpleNamespace(
        id=10,
        status="ready",
        scorm_version="1.2",
    )

    state = SimpleNamespace(
        cmi_data={
            "cmi.core.lesson_status": "incomplete",
            "cmi.core.student_id": "SV001",
        },
        runtime_initialized=True,
        runtime_terminated=False,
    )

    return attempt, enrollment, person, sco, package_version, state

def test_initialize_runtime_thanh_cong(client, mock_session):
    dang_nhap(client)

    state = mock_session.scalar.return_value

    state.runtime_initialized = False
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 200
    assert response.json() == {
        "attempt_id": 1,
        "sco_id": 100,
        "scorm_version": "1.2",
        "cmi_data": {
            "cmi.core.lesson_status": "incomplete",
            "cmi.core.student_id": "SV001",
        },
        "initialized": True,
        "terminated": False,
    }

    assert state.runtime_initialized is True
    assert state.runtime_terminated is False

def test_initialize_lai_runtime_khong_mat_cmi(client, mock_session):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    cmi_cu = dict(state.cmi_data)

    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 200
    assert response.json()["cmi_data"] == cmi_cu
    assert response.json()["initialized"] is True
    assert response.json()["terminated"] is False

    assert state.cmi_data == cmi_cu

def test_initialize_lai_sau_terminate_giu_nguyen_cmi(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    cmi_cu = dict(state.cmi_data)

    state.runtime_initialized = True
    state.runtime_terminated = True

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 200
    assert response.json()["cmi_data"] == cmi_cu
    assert response.json()["initialized"] is True
    assert response.json()["terminated"] is False

    assert state.cmi_data == cmi_cu
    assert state.runtime_initialized is True
    assert state.runtime_terminated is False

def test_terminate_runtime_thanh_cong(client, mock_session):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate"
    )

    assert response.status_code == 200
    assert response.json() == {
        "attempt_id": 1,
        "sco_id": 100,
        "scorm_version": "1.2",
        "terminated": True,
        "attempt_status": "in_progress",
    }

    assert state.runtime_terminated is True

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    assert attempt.status == "in_progress"
    assert attempt.completed_at is None

def test_terminate_luu_cmi_cuoi_cung_va_dong_attempt(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["terminated"] is True
    assert response.json()["attempt_status"] == "completed"

    assert state.cmi_data["cmi.core.lesson_status"] == "completed"
    assert state.runtime_terminated is True

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    assert attempt.status == "completed"
    assert attempt.completed_at is not None
    assert attempt.score_raw == 80.0
    assert attempt.score_min == 0.0
    assert attempt.score_max == 100.0

def test_terminate_cmi_khong_hop_le_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "unknown",
            },
        },
    )

    assert response.status_code == 400
    assert state.cmi_data["cmi.core.lesson_status"] == "incomplete"
    assert state.runtime_terminated is False

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    assert attempt.status == "in_progress"
    assert attempt.completed_at is None

def test_terminate_lap_lai_khong_co_cmi_moi_thanh_cong(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = True

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate",
    )

    assert response.status_code == 200
    assert response.json()["terminated"] is True
    assert response.json()["attempt_status"] == "completed"
    assert state.runtime_terminated is True

def test_terminate_lap_lai_co_cmi_moi_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = True

    cmi_cu = dict(state.cmi_data)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 409
    assert state.cmi_data == cmi_cu
    assert state.runtime_terminated is True
    assert attempt.status == "completed"

def test_terminate_attempt_da_dong_nhung_sco_chua_terminate_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Attempt khong con trong trang thai hoc"
    )
    assert state.runtime_terminated is False
    assert attempt.status == "completed"

def test_terminate_runtime_chua_initialize_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = False
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate"
    )

    assert response.status_code == 409
    assert state.runtime_terminated is False

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    assert attempt.status == "in_progress"
    assert attempt.completed_at is None

def test_cap_nhat_cmi_sau_terminate_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = True

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 409
    assert state.cmi_data["cmi.core.lesson_status"] == "incomplete"

def test_doc_cmi_thanh_cong(client, mock_session):
    dang_nhap(client)

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 200
    assert response.json() == {
        "attempt_id": 1,
        "sco_id": 100,
        "scorm_version": "1.2",
        "cmi_data": {
            "cmi.core.lesson_status": "incomplete",
            "cmi.core.student_id": "SV001",
        },
    }



def test_chua_dang_nhap_tra_401(client, mock_session):
    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 401

def test_truy_cap_attempt_cua_nguoi_khac_tra_403(
    client,
    mock_session,
):
    dang_nhap(client, person_code="SV002")

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403

def test_attempt_da_ket_thuc_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    attempt.status = "completed"

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 409

def test_nguoi_hoc_khong_con_dang_ky_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    enrollment.status = "withdrawn"

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_giang_vien_khong_duoc_truy_cap_runtime(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    enrollment.role = "teacher"

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_sco_khong_thuoc_package_version_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    sco.package_version_id = 99

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 404


def test_package_version_chua_san_sang_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    package_version.status = "processing"

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 409

def test_khong_tim_thay_trang_thai_cmi_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.scalar.return_value = None

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 404

def test_khong_tim_thay_attempt_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = None
    mock_session.get.return_value = None

    response = client.get(
        "/api/v1/attempts/999/scos/100/cmi"
    )

    assert response.status_code == 404


def test_khong_tim_thay_enrollment_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    mock_session.get.side_effect = lambda model, key: (
        None
        if model is api_runtime_session.Enrollment
        else {
            api_runtime_session.Attempt: tao_du_lieu_gia()[0],
            api_runtime_session.Person: tao_du_lieu_gia()[2],
            api_runtime_session.Sco: tao_du_lieu_gia()[3],
            api_runtime_session.PackageVersion: tao_du_lieu_gia()[4],
        }.get(model)
    )

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_khong_tim_thay_person_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, _, sco, package_version, _ = du_lieu

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }
        if model is api_runtime_session.Person:
            return None
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_khong_tim_thay_sco_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, _, package_version, _ = du_lieu

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.PackageVersion: package_version,
        }
        if model is api_runtime_session.Sco:
            return None
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 404


def test_khong_tim_thay_package_version_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, _, _ = du_lieu

    def fake_get(model, key):
        bang_du_lieu = {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
        }
        if model is api_runtime_session.PackageVersion:
            return None
        return bang_du_lieu.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 409


def test_phien_dang_nhap_thieu_person_code_tra_401(client):
    client.post(
        "/test-login",
        json={"person_code": ""},
    )

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 401


def test_person_code_khong_khop_attempt_tra_403(
    client,
    mock_session,
):
    dang_nhap(client, person_code="SV002")

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_enrollment_da_bi_huy_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _ = du_lieu
    enrollment.status = "cancelled"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403

def test_person_khong_phai_student_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _ = du_lieu
    person.person_type = "staff"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_enrollment_role_khong_phai_student_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _ = du_lieu
    enrollment.role = "editingteacher"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/cmi"
    )

    assert response.status_code == 403


def test_cap_nhat_cmi_thanh_cong(client, mock_session):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "attempt_id": 1,
        "sco_id": 100,
        "scorm_version": "1.2",
        "cmi_data": {
            "cmi.core.lesson_status": "completed",
            "cmi.core.student_id": "SV001",
        },
    }
    attempt = mock_session.get(api_runtime_session.Attempt, 1)

    assert attempt.status == "in_progress"
    assert attempt.completed_at is None


def test_cap_nhat_cmi_trang_thai_khong_hop_le_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "unknown",
            },
        },
    )

    assert response.status_code == 400


def test_cap_nhat_cmi_gia_tri_khong_phai_chuoi_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": 123,
            },
        },
    )

    assert response.status_code == 400  


def test_cap_nhat_cmi_truong_khong_duoc_ho_tro_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.invalid_field": "value",
            },
        },
    )

    assert response.status_code == 400


def test_put_cmi_chua_dang_nhap_tra_401(client, mock_session):
    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 401


def test_put_cmi_attempt_cua_nguoi_khac_tra_403(
    client,
    mock_session,
):
    dang_nhap(client, person_code="SV002")

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 403


def test_put_cmi_attempt_da_ket_thuc_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.get.side_effect = None

    attempt, enrollment, person, sco, package_version, _state = (
        tao_du_lieu_gia()
    )
    attempt.status = "completed"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 409


def test_put_cmi_enrollment_da_bi_huy_tra_403(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _state = du_lieu
    enrollment.status = "cancelled"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 403


def test_put_cmi_sco_khong_thuoc_package_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _state = du_lieu
    sco.package_version_id = 99

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 404


def test_put_cmi_khong_tim_thay_state_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.scalar.return_value = None

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 404

def test_put_cmi_scorm_2004_thanh_cong(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _state = du_lieu
    package_version.scorm_version = "2004"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.completion_status": "completed",
                "cmi.success_status": "passed",
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["cmi_data"]["cmi.completion_status"] == "completed"
    assert response.json()["cmi_data"]["cmi.success_status"] == "passed"
    assert response.json()["cmi_data"]["cmi.core.student_id"] == "SV001"

def test_put_cmi_scorm_2004_completion_status_khong_hop_le_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _state = du_lieu
    package_version.scorm_version = "2004"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.completion_status": "passed",
            },
        },
    )

    assert response.status_code == 400


def test_put_cmi_scorm_2004_success_status_khong_hop_le_tra_400(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    attempt, enrollment, person, sco, package_version, _state = du_lieu
    package_version.scorm_version = "2004"

    def fake_get(model, key):
        return {
            api_runtime_session.Attempt: attempt,
            api_runtime_session.Enrollment: enrollment,
            api_runtime_session.Person: person,
            api_runtime_session.Sco: sco,
            api_runtime_session.PackageVersion: package_version,
        }.get(model)

    mock_session.get.side_effect = fake_get

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.success_status": "completed",
            },
        },
    )

    assert response.status_code == 400


def test_put_cmi_co_truong_khong_hop_le_khong_luu_mot_phan(
    client,
    mock_session,
):
    dang_nhap(client)

    du_lieu = tao_du_lieu_gia()
    _, _, _, _, _, state = du_lieu

    cmi_ban_dau = dict(state.cmi_data)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
                "cmi.core.invalid_field": "invalid",
            },
        },
    )

    assert response.status_code == 400
    assert state.cmi_data == cmi_ban_dau


def test_put_cmi_thieu_cmi_data_tra_422(
    client,
    mock_session,
):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={},
    )

    assert response.status_code == 422


def test_put_cmi_cmi_data_rong(
    client,
    mock_session,
):
    dang_nhap(client)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {},
        },
    )

    assert response.status_code == 200


def test_attempt_van_dang_hoc_khi_con_sco_chua_hoan_thanh(
    client,
    mock_session,
):
    dang_nhap(client)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    state = mock_session.scalar.return_value

    state.cmi_data = {
        "cmi.core.lesson_status": "completed",
    }

    sco_state_chua_xong = SimpleNamespace(
        cmi_data={
            "cmi.core.lesson_status": "incomplete",
        },
    )

    mock_session.scalars.return_value.all.return_value = [
        state,
        sco_state_chua_xong,
    ]

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 200
    assert attempt.status == "in_progress"
    assert attempt.completed_at is None

@pytest.mark.parametrize(
    ("scorm_version", "score_fields"),
    [
        (
            "1.2",
            {
                "cmi.core.score.raw": "8",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
        ),
        (
            "2004",
            {
                "cmi.score.raw": "8",
                "cmi.score.min": "0",
                "cmi.score.max": "10",
            },
        ),
    ],
)
def test_put_cmi_luu_diem_so(
    client,
    mock_session,
    scorm_version,
    score_fields,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    package_version = mock_session.get(
        api_runtime_session.PackageVersion,
        10,
    )
    package_version.scorm_version = scorm_version

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={"cmi_data": score_fields},
    )

    assert response.status_code == 200

    for field, value in score_fields.items():
        assert response.json()["cmi_data"][field] == value
        assert state.cmi_data[field] == value

@pytest.mark.parametrize(
    "scaled_score",
    ["-1", "-0.5", "0", "0.5", "1"],
)
def test_put_cmi_scorm_2004_luu_score_scaled(
    client,
    mock_session,
    scaled_score,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    package_version = mock_session.get(
        api_runtime_session.PackageVersion,
        10,
    )
    package_version.scorm_version = "2004"

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.score.scaled": scaled_score,
            },
        },
    )

    assert response.status_code == 200
    assert (
        response.json()["cmi_data"]["cmi.score.scaled"]
        == scaled_score
    )
    assert state.cmi_data["cmi.score.scaled"] == scaled_score

@pytest.mark.parametrize(
    "scaled_score",
    ["-1.01", "1.01", "abc", "NaN", "Infinity"],
)
def test_put_cmi_scorm_2004_score_scaled_khong_hop_le(
    client,
    mock_session,
    scaled_score,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    package_version = mock_session.get(
        api_runtime_session.PackageVersion,
        10,
    )
    package_version.scorm_version = "2004"

    cmi_ban_dau = dict(state.cmi_data)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.score.scaled": scaled_score,
            },
        },
    )

    assert response.status_code == 400
    assert state.cmi_data == cmi_ban_dau

def test_put_cmi_diem_vuot_max_khong_luu(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    cmi_ban_dau = dict(state.cmi_data)

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.score.raw": "11",
                "cmi.core.score.min": "0",
                "cmi.core.score.max": "10",
            },
        },
    )

    assert response.status_code == 400
    assert state.cmi_data == cmi_ban_dau


def test_initialize_khong_tim_thay_state_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.scalar.return_value = None

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Khong tim thay trang thai CMI cua SCO"
    )


def test_initialize_attempt_da_dong_sco_chua_terminate_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    state = mock_session.scalar.return_value
    state.runtime_initialized = True
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Attempt khong con trong trang thai hoc"
    )
    assert state.runtime_terminated is False


def test_put_cmi_runtime_chua_initialize_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    state = mock_session.scalar.return_value
    state.runtime_initialized = False
    state.runtime_terminated = False

    response = client.put(
        "/api/v1/attempts/1/scos/100/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Runtime chua duoc Initialize"
    )
    assert state.cmi_data["cmi.core.lesson_status"] == "incomplete"


def test_terminate_khong_tim_thay_state_tra_404(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.scalar.return_value = None

    response = client.post(
        "/api/v1/attempts/1/scos/100/terminate"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Khong tim thay trang thai CMI cua SCO"
    )


def test_initialize_attempt_da_dong_runtime_chua_terminate_tra_409(
    client,
    mock_session,
):
    dang_nhap(client)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    state = mock_session.scalar.return_value
    state.runtime_terminated = False

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Attempt khong con trong trang thai hoc"
    )
    assert state.runtime_terminated is False
    assert state.runtime_initialized is True


def test_initialize_nhanh_attempt_da_dong_runtime_chua_terminate_tra_409(
    client,
    mock_session,
    monkeypatch,
):
    dang_nhap(client)

    attempt = mock_session.get(api_runtime_session.Attempt, 1)
    attempt.status = "completed"

    state = mock_session.scalar.return_value
    state.runtime_terminated = False

    ham_goc = api_runtime_session.kiem_tra_quyen_runtime

    def kiem_tra_quyen_cho_phep_attempt_da_dong(
        s,
        attempt_id,
        sco_id,
        person_code,
    ):
        return ham_goc(
            s,
            attempt_id,
            sco_id,
            person_code,
            cho_phep_attempt_da_dong=True,
        )

    monkeypatch.setattr(
        api_runtime_session,
        "kiem_tra_quyen_runtime",
        kiem_tra_quyen_cho_phep_attempt_da_dong,
    )

    response = client.post(
        "/api/v1/attempts/1/scos/100/initialize"
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Attempt khong con trong trang thai hoc"
    )
    assert state.runtime_terminated is False



def test_launch_wrapper_thanh_cong(client, mock_session):
    dang_nhap(client)

    response = client.get(
        "/api/v1/attempts/1/scos/100/launch"
    )

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert '"attemptId": 1' in response.text
    assert '"scoId": 100' in response.text
    assert '"scormVersion": "1.2"' in response.text
    assert (
        '"launchUrl": "/content/attempts/1/scos/100/index.html"'
        in response.text
    )
    assert "window.API = adapter;" in response.text


def test_launch_wrapper_tu_choi_attempt_cua_nguoi_khac(
    client,
    mock_session,
):
    dang_nhap(client, person_code="SV002")

    response = client.get(
        "/api/v1/attempts/1/scos/100/launch"
    )

    assert response.status_code == 403


def test_launch_wrapper_tu_choi_sco_khong_thuoc_attempt(
    client,
    mock_session,
):
    dang_nhap(client)

    # Dữ liệu SCO được lấy từ fake_get trong fixture.
    # Thay đổi trực tiếp đối tượng SCO giả lập.
    mock_session.get.side_effect = None

    def fake_get(model, key):
        if model is api_runtime_session.Attempt:
            return SimpleNamespace(
                id=1,
                person_code="SV001",
                section_code="SEC001",
                package_version_id=10,
                status="in_progress",
            )
        if model is api_runtime_session.Enrollment:
            return SimpleNamespace(
                status="registered",
                role="student",
            )
        if model is api_runtime_session.Person:
            return SimpleNamespace(person_type="student")
        if model is api_runtime_session.Sco:
            return SimpleNamespace(
                id=100,
                package_version_id=999,
                href="index.html",
            )
        if model is api_runtime_session.PackageVersion:
            return SimpleNamespace(
                id=10,
                status="ready",
                scorm_version="1.2",
            )
        return None

    mock_session.get.side_effect = fake_get

    response = client.get(
        "/api/v1/attempts/1/scos/100/launch"
    )

    assert response.status_code == 404


def test_launch_wrapper_tu_choi_khi_chua_co_state(
    client,
    mock_session,
):
    dang_nhap(client)
    mock_session.scalar.return_value = None

    response = client.get(
        "/api/v1/attempts/1/scos/100/launch"
    )

    assert response.status_code == 404
