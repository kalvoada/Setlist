"""Application configuration.

All values can be overridden with environment variables (or a local ``.env``
file), which is what makes the service deployable without code changes.
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────
    app_name: str = "Setlist API"
    environment: str = "development"
    debug: bool = False

    # ── Database ──────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./social.db"

    # ── Auth ──────────────────────────────────────────────────────────────
    # MUST be overridden in production (see .env.example).
    secret_key: str = "dev-only-insecure-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins: List[str] = Field(default_factory=lambda: ["*"])

    # ── Music link resolution ─────────────────────────────────────────────
    # When enabled the API enriches posted streaming links with title/artwork
    # via the providers' public oEmbed endpoints. Disabled in tests.
    enable_link_metadata: bool = True
    link_metadata_timeout_seconds: float = 4.0

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value):
        """Accept a comma separated string so it maps cleanly to an env var."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}

    def model_post_init(self, __context) -> None:
        """Refuse to boot a production deployment with a weak signing key."""
        if self.is_production and (
            self.secret_key == Settings.model_fields["secret_key"].default
            or len(self.secret_key) < 32
        ):
            raise ValueError(
                "SECRET_KEY must be set to a random value of at least 32 "
                "characters in production (see .env.example)."
            )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
