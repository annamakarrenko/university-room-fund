import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

TEST_DATABASE_PATH = (
    Path(tempfile.gettempdir())
    / f"university_room_fund_test_{os.getpid()}.sqlite3"
)

os.environ["DATABASE_URL"] = (
    f"sqlite:///{TEST_DATABASE_PATH.as_posix()}"
)
os.environ["SESSION_SECRET"] = (
    "test-session-secret-not-for-production"
)


@pytest.fixture(scope="session")
def application():
    from app.main import app

    return app


@pytest.fixture(autouse=True)
def clean_database(application):
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield


@pytest.fixture
def client(application):
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture(scope="session", autouse=True)
def remove_test_database():
    yield

    from app.database import engine

    engine.dispose()
    TEST_DATABASE_PATH.unlink(missing_ok=True)