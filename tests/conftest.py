"""
Test fixtures: shared app engine (SQLite in tests) and DB session override.
"""
import os

# Must run before any `app` / `app.database` import so the engine binds to SQLite.
os.environ.setdefault("DATABASE_URL", "sqlite://")

import pytest
from sqlalchemy.orm import sessionmaker

from app.database import Base, engine, get_db
from app.main import app


@pytest.fixture
def db_session():
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
