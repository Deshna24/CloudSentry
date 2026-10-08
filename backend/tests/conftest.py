import os
import tempfile

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["JWT_SECRET"] = "test-secret-test-secret-test-secret-0123456789"
os.environ["SEED_ADMIN_PASSWORD"] = "AdminPass#123"
os.environ["SEED_ANALYST_PASSWORD"] = "AnalystPass#123"
os.environ["SEED_RECORDS"] = "300"
os.environ["ENVIRONMENT"] = "test"
os.environ["REGISTER_INSTANCES"] = ""
os.environ["INSTANCE_ID"] = "API-01"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


def _login(client, user, pw, ip="10.1.1.1"):
    r = client.post("/auth/login", json={"username": user, "password": pw}, headers={"X-Forwarded-For": ip})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="session")
def admin(client):
    return _login(client, "admin", "AdminPass#123", "10.1.1.1")


@pytest.fixture(scope="session")
def analyst(client):
    return _login(client, "analyst", "AnalystPass#123", "10.1.1.2")
