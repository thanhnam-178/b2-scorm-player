from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

import scorm_service.models  # noqa: F401
from scorm_service.models.base import Base, bay_gio
from scorm_service.models.runtime_session import RuntimeSession
from scorm_service.sessions import cap_ma_khoi_chay, doi_ma_lay_token, nguoi_hoc_tu_token


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_ma_dung_doi_duoc_token(s):
    ma = cap_ma_khoi_chay(s, attempt_id=7, sco_id=3)
    kq = doi_ma_lay_token(s, ma)
    assert kq is not None
    token, phien = kq
    assert phien.attempt_id == 7 and phien.sco_id == 3


def test_ma_chi_dung_mot_lan(s):
    ma = cap_ma_khoi_chay(s, 7, 3)
    assert doi_ma_lay_token(s, ma) is not None
    assert doi_ma_lay_token(s, ma) is None


def test_ma_sai(s):
    cap_ma_khoi_chay(s, 7, 3)
    assert doi_ma_lay_token(s, "ma-gia") is None


def test_ma_het_han(s):
    ma = cap_ma_khoi_chay(s, 7, 3)
    phien = s.scalar(select(RuntimeSession))
    phien.code_expires_at = bay_gio() - timedelta(seconds=1)
    s.flush()
    assert doi_ma_lay_token(s, ma) is None


def test_token_tra_ve_dung_attempt(s):
    token, _ = doi_ma_lay_token(s, cap_ma_khoi_chay(s, 7, 3))
    assert nguoi_hoc_tu_token(s, token).attempt_id == 7


def test_token_sai(s):
    assert nguoi_hoc_tu_token(s, "token-gia") is None


def test_token_het_han(s):
    token, phien = doi_ma_lay_token(s, cap_ma_khoi_chay(s, 7, 3))
    phien.token_expires_at = bay_gio() - timedelta(seconds=1)
    s.flush()
    assert nguoi_hoc_tu_token(s, token) is None