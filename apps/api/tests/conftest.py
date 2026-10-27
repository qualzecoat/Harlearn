"""Test fixtures: isolated SQLite DB + a test-only password hash.

The hash here is generated at import time for the password
"test-password" and is NEVER a production credential. Production uses
HARLEARN_APP_PASSWORD_HASH from the deployment .env file.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["DATABASE_URL"] = "sqlite:///./test_harlearn.db"
os.environ["WEB_ORIGIN"] = "http://127.0.0.1:3000"

from argon2 import PasswordHasher  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

import pytest  # noqa: E402

from app import config, security  # noqa: E402
from app.db import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402

config.APP_PASSWORD_HASH = PasswordHasher().hash("test-password")

TEST_DB = "sqlite:///./test_harlearn.db"
engine = create_engine(TEST_DB, connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def _override_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_db


@pytest.fixture()
def client():
    security.reset_rate_limits()
    with TestClient(app) as c:
        yield c
    security.reset_rate_limits()


@pytest.fixture()
def authed_client(client):
    r = client.post("/api/auth/login", json={"password": "test-password"})
    assert r.status_code == 200, r.text
    return client
