
from contextlib import contextmanager
from datetime import date, datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from starlette.middleware.sessions import SessionMiddleware

from scorm_service import api_runtime_session
from scorm_service.models import (
    Attempt,
    AttemptScoState,
    Base,
    Enrollment,
    PackageVersion,
    Person,
    Sco,
    Section,
    Term,
)


@pytest.fixture
def database():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    with SessionLocal() as session:
        session.add(
            Term(
                term_code="HK_TEST",
                name="Hoc ky test",
                start_date=date(2026, 1, 1),
                end_date=date(2026, 12, 31),
                status="open",
            )
        )
        session.add(
            Person(
                person_code="SV_TEST",
                family_name="Nguyen",
                given_name="Test",
                email="test@example.com",
                person_type="student",
            )
        )
        session.flush()

        session.add(
            Section(
                section_code="HP_TEST",
                term_code="HK_TEST",
                course_code="SCORM_TEST",
                course_name="Kiem thu SCORM",
                updated_at=datetime(2026, 1, 1),
            )
        )
        session.flush()

        session.add(
            Enrollment(
                section_code="HP_TEST",
                person_code="SV_TEST",
                role="student",
                status="registered",
                updated_at=datetime(2026, 1, 1),
            )
        )
        session.flush()

        package = PackageVersion(
            package="PKG_TEST",
            version=1,
            scorm_version="1.2",
            sha256="a" * 64,
            storage_prefix="integration-test",
            status="ready",
        )
        session.add(package)
        session.flush()

        sco = Sco(
            package_version_id=package.id,
            identifier="SCO_TEST",
            title="SCO kiem thu",
            href="index.html",
        )
        session.add(sco)
        session.flush()

        attempt = Attempt(
            section_code="HP_TEST",
            person_code="SV_TEST",
            package_version_id=package.id,
            attempt_number=1,
            status="in_progress",
        )
        session.add(attempt)
        session.flush()

        state = AttemptScoState(
            attempt_id=attempt.id,
            sco_id=sco.id,
            cmi_data={
                "cmi.core.lesson_status": "incomplete",
                "cmi.core.student_id": "SV_TEST",
            },
            runtime_initialized=True,
            runtime_terminated=False,
        )
        session.add(state)
        session.commit()

        attempt_id = attempt.id
        sco_id = sco.id

    try:
        yield SessionLocal, attempt_id, sco_id
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(database):
    SessionLocal, _, _ = database

    @contextmanager
    def phien_lam_viec_test():
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app = FastAPI()

    app.add_middleware(
        SessionMiddleware,
        secret_key="integration-test-secret",
    )

    @app.post("/test-login")
    def test_login(request: Request, person_code: str = "SV_TEST"):
        request.session["authenticated"] = True
        request.session["person_code"] = person_code
        return {"status": "ok"}

    app.include_router(api_runtime_session.router)

    with (
        patch.object(
            api_runtime_session,
            "phien_lam_viec",
            phien_lam_viec_test,
        ),
        TestClient(app) as test_client,
    ):
        login_response = test_client.post("/test-login")
        assert login_response.status_code == 200
        yield test_client


def test_put_cmi_duoc_luu_sau_khi_dong_session(client, database):
    SessionLocal, attempt_id, sco_id = database

    response = client.put(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/cmi",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            }
        },
    )

    print("RESPONSE:", response.status_code, response.json())
    assert response.status_code == 200
    assert (
        response.json()["cmi_data"]["cmi.core.lesson_status"]
        == "completed"
    )

    # Mo session moi de doc lai du lieu da commit.
    with SessionLocal() as session:
        state = session.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        assert state is not None
        assert state.cmi_data["cmi.core.lesson_status"] == "completed"
        assert state.cmi_data["cmi.core.student_id"] == "SV_TEST"

    # PUT CMI chi luu du lieu, khong dong Attempt.
    with SessionLocal() as session:
        attempt = session.get(Attempt, attempt_id)

        assert attempt is not None
        assert attempt.status == "in_progress"
        assert attempt.completed_at is None

    # Attempt van dang hoc nen nguoi hoc van doc duoc CMI.
    get_response = client.get(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/cmi",
    )

    assert get_response.status_code == 200
    assert (
        get_response.json()["cmi_data"]["cmi.core.lesson_status"]
        == "completed"
    )

def test_terminate_luu_cmi_va_dong_attempt(client, database):
    SessionLocal, attempt_id, sco_id = database

    response = client.post(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/terminate",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["terminated"] is True
    assert response.json()["attempt_status"] == "completed"

    # Kiem tra du lieu CMI va Runtime da duoc luu.
    with SessionLocal() as session:
        state = session.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        assert state is not None
        assert state.runtime_terminated is True
        assert state.cmi_data["cmi.core.lesson_status"] == "completed"

    # Kiem tra Attempt da duoc dong.
    with SessionLocal() as session:
        attempt = session.get(Attempt, attempt_id)

        assert attempt is not None
        assert attempt.status == "completed"
        assert attempt.completed_at is not None

def test_initialize_resume_giu_cmi_va_attempt_cu(client, database):
    SessionLocal, attempt_id, sco_id = database

    # Gia lap SCO da Terminate truoc do.
    with SessionLocal() as session:
        state = session.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        assert state is not None
        state.runtime_terminated = True
        state.cmi_data["cmi.core.lesson_status"] = "incomplete"
        session.commit()

    # Initialize lai Runtime tren Attempt cu.
    response = client.post(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/initialize",
    )

    assert response.status_code == 200
    assert response.json()["attempt_id"] == attempt_id
    assert response.json()["initialized"] is True
    assert response.json()["terminated"] is False
    assert (
        response.json()["cmi_data"]["cmi.core.lesson_status"]
        == "incomplete"
    )

    # Kiem tra trang thai da duoc luu trong database.
    with SessionLocal() as session:
        state = session.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        attempt = session.get(Attempt, attempt_id)

        assert state is not None
        assert state.runtime_initialized is True
        assert state.runtime_terminated is False
        assert state.cmi_data["cmi.core.lesson_status"] == "incomplete"

        assert attempt is not None
        assert attempt.status == "in_progress"

def test_terminate_lap_lai_khong_lam_mat_cmi(client, database):
    SessionLocal, attempt_id, sco_id = database

    # Terminate lan dau.
    response_1 = client.post(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/terminate",
        json={
            "cmi_data": {
                "cmi.core.lesson_status": "completed",
            }
        },
    )

    assert response_1.status_code == 200

    # Terminate lan hai, khong gui CMI moi.
    response_2 = client.post(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/terminate",
    )

    assert response_2.status_code == 200
    assert response_2.json()["terminated"] is True
    assert response_2.json()["attempt_status"] == "completed"

    with SessionLocal() as session:
        state = session.scalar(
            select(AttemptScoState).where(
                AttemptScoState.attempt_id == attempt_id,
                AttemptScoState.sco_id == sco_id,
            )
        )

        assert state is not None
        assert state.runtime_terminated is True
        assert state.cmi_data["cmi.core.lesson_status"] == "completed"

def test_runtime_tu_choi_khi_chua_dang_nhap(database):
    SessionLocal, attempt_id, sco_id = database

    @contextmanager
    def phien_lam_viec_test():
        with SessionLocal() as session:
            yield session
            session.commit()

    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key="integration-test-secret",
    )
    app.include_router(api_runtime_session.router)

    with (
        patch.object(
            api_runtime_session,
            "phien_lam_viec",
            phien_lam_viec_test,
        ),
        TestClient(app) as test_client,
    ):
        response = test_client.get(
            f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/cmi"
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Chua dang nhap"

def test_runtime_tu_choi_attempt_cua_nguoi_khac(client, database):
    _, attempt_id, sco_id = database

    # Dang nhap bang tai khoan nguoi hoc khac.
    response = client.post(
        "/test-login",
        params={"person_code": "SV_KHAC"},
    )
    assert response.status_code == 200

    # Truy cap Attempt cua SV_TEST.
    response = client.get(
        f"/api/v1/attempts/{attempt_id}/scos/{sco_id}/cmi",
    )

    assert response.status_code == 403
    assert (
        response.json()["detail"]
        == "Ban khong co quyen truy cap Attempt nay"
    )