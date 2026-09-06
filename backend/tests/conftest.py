"""Pytest fixtures: a throwaway SQLite database and an authenticated client."""

from __future__ import annotations

import os
import tempfile
from typing import Callable

import pytest

# Configure the app before it is imported: a scratch database, deterministic
# auth and no outbound calls to streaming providers.
_TMP_DIR = tempfile.mkdtemp(prefix="setlist-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DIR}/test.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-32"
os.environ["ENABLE_LINK_METADATA"] = "false"
os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from src.database.database import Base, engine  # noqa: E402

SPOTIFY_TRACK = "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT"
APPLE_ALBUM = "https://music.apple.com/us/album/abbey-road-2019-mix/1474815798"


@pytest.fixture(autouse=True)
def _fresh_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def register(client: TestClient) -> Callable[..., dict]:
    """Create a user and return ``{user, token, headers}``."""

    def _register(username: str = "ada", password: str = "supersecret1", **extra):
        response = client.post(
            "/auth/register",
            json={
                "username": username,
                "email": extra.get("email", f"{username}@example.com"),
                "password": password,
                "display_name": extra.get("display_name"),
            },
        )
        assert response.status_code == 201, response.text
        payload = response.json()
        return {
            "user": payload["user"],
            "token": payload["access_token"],
            "password": password,
            "headers": {"Authorization": f"Bearer {payload['access_token']}"},
        }

    return _register


@pytest.fixture
def alice(register) -> dict:
    return register("alice", display_name="Alice")


@pytest.fixture
def bob(register) -> dict:
    return register("bob", display_name="Bob")


@pytest.fixture
def make_post(client: TestClient) -> Callable[..., dict]:
    def _make_post(headers: dict, url: str = SPOTIFY_TRACK, caption: str = "on repeat"):
        response = client.post(
            "/posts/",
            json={"music_url": url, "caption": caption, "title": "Bohemian Rhapsody",
                  "artist_name": "Queen"},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _make_post
