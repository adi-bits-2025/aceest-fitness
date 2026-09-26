import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app  # noqa: E402


@pytest.fixture
def app(tmp_path):
    """App wired to a fresh SQLite file per test."""
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.db")})


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def sample_client(client):
    """Create one client ('Ravi') through the HTML form and return its name."""
    client.post("/clients", data={
        "name": "Ravi", "age": "30", "height": "175", "weight": "80",
        "program": "Fat Loss", "membership_end": "2099-12-31",
    })
    return "Ravi"
