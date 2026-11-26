import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import scorm_service.models  # noqa: F401
from scorm_service.api_runtime import get_db, router
from scorm_service.models.base import Base


@pytest.fixture
def env():
    """Mỗi test một DB SQLite trống trong bộ nhớ + một app chỉ có router runtime."""
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