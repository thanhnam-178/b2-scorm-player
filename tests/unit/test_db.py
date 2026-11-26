
from unittest.mock import Mock

import pytest

from scorm_service import db


class FakeSession:
    def __init__(self):
        self.commit = Mock()
        self.rollback = Mock()
        self.close = Mock()


@pytest.fixture
def fake_db(monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_Session", None)
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost/test")

    fake_engine = object()
    fake_session = FakeSession()

    create_engine_mock = Mock(return_value=fake_engine)
    sessionmaker_mock = Mock(return_value=lambda: fake_session)

    monkeypatch.setattr(db, "create_engine", create_engine_mock)
    monkeypatch.setattr(db, "sessionmaker", sessionmaker_mock)

    return {
        "engine": fake_engine,
        "session": fake_session,
        "create_engine": create_engine_mock,
        "sessionmaker": sessionmaker_mock,
    }


def test_phien_lam_viec_commit_va_dong_session(fake_db):
    with db.phien_lam_viec() as session:
        assert session is fake_db["session"]

    fake_db["create_engine"].assert_called_once_with(
        "postgresql://test:test@localhost/test",
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    fake_db["sessionmaker"].assert_called_once_with(
        bind=fake_db["engine"],
        expire_on_commit=False,
    )
    fake_db["session"].commit.assert_called_once()
    fake_db["session"].rollback.assert_not_called()
    fake_db["session"].close.assert_called_once()


def test_phien_lam_viec_rollback_khi_co_loi(fake_db):
    with pytest.raises(RuntimeError, match="Loi thu nghiem"), db.phien_lam_viec():
        raise RuntimeError("Loi thu nghiem")

    fake_db["session"].commit.assert_not_called()
    fake_db["session"].rollback.assert_called_once()
    fake_db["session"].close.assert_called_once()


def test_phien_lam_viec_tai_su_dung_engine(fake_db):
    with db.phien_lam_viec():
        pass

    with db.phien_lam_viec():
        pass

    fake_db["create_engine"].assert_called_once()
    fake_db["sessionmaker"].assert_called_once()
    assert fake_db["session"].commit.call_count == 2
    assert fake_db["session"].close.call_count == 2
