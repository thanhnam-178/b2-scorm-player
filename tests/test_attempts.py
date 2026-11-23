import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

import scorm_service.models  # noqa: F401  nap het model de create_all thay du bang
from scorm_service.attempts import lay_hoac_tao_attempt
from scorm_service.models.attempt import Attempt
from scorm_service.models.base import Base


@pytest.fixture
def s():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_lan_dau_tao_moi(s):
    a = lay_hoac_tao_attempt(s, "SV000001", 1)
    assert a.id is not None
    assert a.person_code == "SV000001"


def test_mo_lan_hai_dung_lai(s):
    a1 = lay_hoac_tao_attempt(s, "SV000001", 1)
    a2 = lay_hoac_tao_attempt(s, "SV000001", 1)
    assert a1.id == a2.id
    assert s.scalar(select(func.count()).select_from(Attempt)) == 1


def test_nguoi_khac_co_attempt_rieng(s):
    a1 = lay_hoac_tao_attempt(s, "SV000001", 1)
    a2 = lay_hoac_tao_attempt(s, "SV000002", 1)
    assert a1.id != a2.id