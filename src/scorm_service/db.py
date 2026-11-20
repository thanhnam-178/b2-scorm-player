"""Ket noi DB: src/scorm_service/db.py"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None


def _khoi_tao():
    global _engine, _Session
    if _engine is None:
        _engine = create_engine(
            os.environ["DATABASE_URL"],
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True, 
        )
        _Session = sessionmaker(bind=_engine, expire_on_commit=False)


@contextmanager
def phien_lam_viec():
    _khoi_tao()
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()