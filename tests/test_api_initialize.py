import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import scorm_service.models  # noqa: F401
from scorm_service.api_runtime import get_db, router
from scorm_service.attempts import lay_hoac_tao_attempt
from scorm_service.models.base import Base
from scorm_service.models.person import Person
from scorm_service.models.sco_state import ScoState
from scorm_service.runtime_rules import EXIT, KHOA_NOI_BO, LESSON_STATUS, LOCATION
from scorm_service.sessions import cap_ma_khoi_chay, doi_ma_lay_token

URL = "/api/v1/runtime/initialize"


@pytest.fixture
def env():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)

    def _db():
        with Session(engine) as s:
            yield s
            s.commit()

    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = _db
    return TestClient(app), engine


def _tao_attempt(engine, person_code="SV000001"):
    with Session(engine) as s:
        s.add(Person(person_code=person_code, family_name="Nguyen", given_name="An",
                     email=f"{person_code}@x.vn", person_type="student"))
        a = lay_hoac_tao_attempt(s, person_code, 1)
        s.commit()
        return a.id


def _auth(engine, attempt_id, sco_id=3):
    with Session(engine) as s:
        token, _ = doi_ma_lay_token(s, cap_ma_khoi_chay(s, attempt_id, sco_id))
        s.commit()
    return {"Authorization": f"Bearer {token}"}


def _sua_state(engine, **thay):
    with Session(engine) as s:
        st = s.scalar(select(ScoState))
        if "cmi" in thay:
            st.cmi = {**st.cmi, **thay.pop("cmi")}
        for k, v in thay.items():
            setattr(st, k, v)
        s.commit()


def test_lan_dau_ab_initio(env):
    client, engine = env
    h = _auth(engine, _tao_attempt(engine))
    r = client.post(URL, headers=h)
    assert r.status_code == 200
    cmi = r.json()["cmi"]
    assert cmi["cmi.core.entry"] == "ab-initio"
    assert cmi[LESSON_STATUS] == "not attempted"
    assert cmi["cmi.core.student_id"] == "SV000001"


def test_thieu_token(env):
    client, _ = env
    assert client.post(URL).status_code == 401


def test_token_gia(env):
    client, _ = env
    assert client.post(URL, headers={"Authorization": "Bearer abc"}).status_code == 401


def test_vao_lai_sau_suspend_la_resume(env):
    client, engine = env
    h = _auth(engine, _tao_attempt(engine))
    client.post(URL, headers=h)
    _sua_state(engine, cmi={LOCATION: "trang-5", EXIT: "suspend"})
    cmi = client.post(URL, headers=h).json()["cmi"]
    assert cmi["cmi.core.entry"] == "resume"
    assert cmi[LOCATION] == "trang-5"


def test_da_xong_thi_khoa_ket_qua(env):
    client, engine = env
    h = _auth(engine, _tao_attempt(engine))
    client.post(URL, headers=h)
    _sua_state(engine, cmi={LESSON_STATUS: "completed"})
    cmi = client.post(URL, headers=h).json()["cmi"]
    assert cmi[LESSON_STATUS] == "completed"
    with Session(engine) as s:
        assert s.scalar(select(ScoState)).cmi[KHOA_NOI_BO] is True


def test_phien_moi_dat_lai_last_seq(env):
    client, engine = env
    h = _auth(engine, _tao_attempt(engine))
    client.post(URL, headers=h)
    _sua_state(engine, last_seq=5)
    client.post(URL, headers=h)
    with Session(engine) as s:
        assert s.scalar(select(ScoState)).last_seq == 0


def test_nguoi_hoc_theo_token(env):
    client, engine = env
    a1 = _tao_attempt(engine, "SV000001")
    a2 = _tao_attempt(engine, "SV000002")
    cmi2 = client.post(URL, headers=_auth(engine, a2)).json()["cmi"]
    cmi1 = client.post(URL, headers=_auth(engine, a1)).json()["cmi"]
    assert cmi2["cmi.core.student_id"] == "SV000002"
    assert cmi1["cmi.core.student_id"] == "SV000001"