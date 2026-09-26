import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import DEFAULT_PASSWORD, DEFAULT_USERNAME, create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """App wired to a fresh SQLite file per test."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def anon_client(app):
    """A test client that is NOT logged in."""
    return app.test_client()


@pytest.fixture
def client(app):
    """A test client logged in with the default staff account."""
    c = app.test_client()
    c.post("/login", data={"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD})
    return c


@pytest.fixture
def sample_client(client):
    """Create 'Ravi' (name + program), then fill in the profile page."""
    client.post("/clients", data={"name": "Ravi", "program": "Fat Loss"})
    client.post("/clients/Ravi/profile", data={
        "program": "Fat Loss", "age": "30", "height": "175", "weight": "80",
        "membership_end": "2099-12-31",
    })
    return "Ravi"
