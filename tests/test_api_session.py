import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import scorm_service.models  # noqa: F401
from scorm_service.api_runtime import get_db, router
from scorm_service.models.base import Base
from scorm_service.sessions import cap_ma_khoi_chay, nguoi_hoc_tu_token


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


def _cap_ma(engine, attempt_id=7, sco_id=3):
    with Session(engine) as s:
        ma = cap_ma_khoi_chay(s, attempt_id, sco_id)
        s.commit()
    return ma


def test_doi_ma_thanh_cong(env):
    client, engine = env
    r = client.post("/api/v1/runtime/session", json={"code": _cap_ma(engine)})
    assert r.status_code == 200
    assert r.json()["sco_id"] == 3
    with Session(engine) as s:
        assert nguoi_hoc_tu_token(s, r.json()["token"]).attempt_id == 7


def test_ma_dung_lan_hai_bi_tu_choi(env):
    client, engine = env
    ma = _cap_ma(engine)
    assert client.post("/api/v1/runtime/session", json={"code": ma}).status_code == 200
    assert client.post("/api/v1/runtime/session", json={"code": ma}).status_code == 401


def test_ma_sai(env):
    client, _ = env
    r = client.post("/api/v1/runtime/session", json={"code": "ma-gia"})
    assert r.status_code == 401