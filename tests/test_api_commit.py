from decimal import Decimal

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
from scorm_service.runtime_rules import (
    LESSON_STATUS, LOCATION, SCORE_MAX, SCORE_MIN, SCORE_RAW,
)
from scorm_service.sessions import cap_ma_khoi_chay, doi_ma_lay_token

INIT = "/api/v1/runtime/initialize"
URL = "/api/v1/runtime/commit"


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


def _state_cua(engine, attempt_id):
    with Session(engine) as s:
        st = s.scalar(select(ScoState).where(ScoState.attempt_id == attempt_id))
        if st is not None:
            s.expunge(st)
        return st


def _sua_state(engine, attempt_id, **thay):
    with Session(engine) as s:
        st = s.scalar(select(ScoState).where(ScoState.attempt_id == attempt_id))
        if "cmi" in thay:
            st.cmi = {**st.cmi, **thay.pop("cmi")}
        for k, v in thay.items():
            setattr(st, k, v)
        s.commit()


def _bat_dau(client, engine, person_code="SV000001"):
    """Tao attempt, Initialize, tra ve (attempt_id, header)."""
    a = _tao_attempt(engine, person_code)
    h = _auth(engine, a)
    assert client.post(INIT, headers=h).status_code == 200
    return a, h


def test_commit_truoc_initialize_bi_tu_choi(env):
    client, engine = env
    h = _auth(engine, _tao_attempt(engine))
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {SCORE_RAW: "8"}})
    assert r.status_code == 409


def test_luu_diem_va_trang_thai(env):
    client, engine = env
    a, h = _bat_dau(client, engine)
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {
        LESSON_STATUS: "completed", SCORE_RAW: "8", SCORE_MIN: "0", SCORE_MAX: "10",
    }})
    assert r.status_code == 200
    assert r.json()["errors"] == {}
    st = _state_cua(engine, a)
    assert st.lesson_status == "completed"
    assert st.score_raw == Decimal("8")
    assert st.score_max == Decimal("10")
    assert st.last_seq == 1


def test_tc08_dinh_danh_gia_bi_bo_qua(env):
    client, engine = env
    a1, h = _bat_dau(client, engine, "SV000001")
    a2 = _tao_attempt(engine, "SV000002")
    r = client.post(
        URL,
        headers={**h, "X-Person-Code": "SV000002"},
        json={"seq": 1, "changes": {SCORE_RAW: "8"},
              "person_code": "SV000002", "attempt_id": a2},
    )
    assert r.status_code == 200
    assert _state_cua(engine, a1).score_raw == Decimal("8")  # ghi cho nguoi cua token
    assert _state_cua(engine, a2) is None                    # nguoi gia khong bi dung toi


def test_tc10_phan_tu_chi_doc(env):
    client, engine = env
    a, h = _bat_dau(client, engine)
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {
        "cmi.core.student_id": "SV999999",
    }})
    assert r.json()["errors"] == {"cmi.core.student_id": "403"}
    assert "cmi.core.student_id" not in _state_cua(engine, a).cmi


def test_tc11_gia_tri_sai(env):
    client, engine = env
    a, h = _bat_dau(client, engine)
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {
        SCORE_RAW: "150", LESSON_STATUS: "da-xong",
    }})
    assert r.json()["errors"] == {SCORE_RAW: "405", LESSON_STATUS: "405"}
    st = _state_cua(engine, a)
    assert st.score_raw is None
    assert st.lesson_status == "not attempted"


def test_tc14_gui_lai_lo_cu_khong_ghi_lai(env):
    client, engine = env
    a, h = _bat_dau(client, engine)
    client.post(URL, headers=h, json={"seq": 1, "changes": {SCORE_RAW: "8"}})
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {SCORE_RAW: "2"}})
    assert r.json()["duplicate"] is True
    assert _state_cua(engine, a).score_raw == Decimal("8")


def test_da_xong_thi_khoa_diem_nhung_van_luu_location(env):
    client, engine = env
    a, h = _bat_dau(client, engine)
    _sua_state(engine, a, cmi={LESSON_STATUS: "completed"})
    client.post(INIT, headers=h)  # phien moi: chot khoa ket qua
    r = client.post(URL, headers=h, json={"seq": 1, "changes": {
        SCORE_RAW: "3", LOCATION: "trang-9",
    }})
    assert r.json()["locked"] == [SCORE_RAW]
    st = _state_cua(engine, a)
    assert st.score_raw is None
    assert st.cmi[LOCATION] == "trang-9"


def test_seq_khong_hop_le(env):
    client, engine = env
    _, h = _bat_dau(client, engine)
    r = client.post(URL, headers=h, json={"seq": 0, "changes": {}})
    assert r.status_code == 422