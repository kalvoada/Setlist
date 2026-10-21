"""Settings read from the environment and from .env."""

import pytest

from src.config import Settings


@pytest.mark.parametrize(
    ("value", "origins"),
    [
        ("*", ["*"]),
        ("https://a.example, https://b.example", ["https://a.example", "https://b.example"]),
    ],
)
def test_cors_origins_from_a_dotenv_file(tmp_path, value, origins):
    env_file = tmp_path / ".env"
    env_file.write_text(f"CORS_ORIGINS={value}\nSPOTIFY_CLIENT_ID=abc\n")

    settings = Settings(_env_file=env_file)

    assert settings.cors_origins == origins
    assert settings.spotify_client_id == "abc"


def test_cors_origins_from_the_environment(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example,https://b.example")

    assert Settings(_env_file=None).cors_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_default_to_everything(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    assert Settings(_env_file=None).cors_origins == ["*"]
