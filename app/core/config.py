from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        enable_decoding=False,
    )

    app_name: str = "Tracker Tools API"
    app_description: str = (
        "Tracker ratio scraper, Transmission admission controller, forecaster and purge API."
    )
    app_version: str = "1.0.0"

    config_dir: Path = Field(default=Path(".config"))
    database_url: str | None = None

    transmission_host: str = "localhost"
    transmission_port: int = 9091
    transmission_path: str = "/transmission/rpc"
    transmission_username: str | None = None
    transmission_password: str | None = None

    default_min_ratio: float = 1.0
    max_storage_bytes: int = 0
    min_free_storage_bytes: int = 0
    max_tracker_stats_age_minutes: int = 120
    refresh_interval_minutes: int = 60
    download_dir: Path | None = None

    c411_user: str | None = None
    c411_pass: str | None = None
    torr9_user: str | None = None
    tor9_user: str | None = None
    torr9_password: str | None = None
    torr9_pass: str | None = None
    tor9_pass: str | None = None

    # Optional explicit list of enabled scrapers, comma-separated in env.
    # If empty, scraper activation is inferred from credentials/token presence.
    scrapers_enabled: list[str] = Field(default_factory=list)

    # Additional scraper credentials/tokens.
    crazyspirits_cookie: str | None = None
    gemini_token: str | None = None
    gfree_token: str | None = None
    lacale_user: str | None = None
    lacale_pass: str | None = None
    nexum_token: str | None = None
    nostradamus_private_key: str | None = None
    nostradamus_api_key: str | None = None
    nostradamus_private_ticket: str | None = None
    teamflix_token: str | None = None
    tos_token: str | None = None
    tl_user: str | None = None
    tl_pass: str | None = None
    tr4ker_token: str | None = None
    tr4ker_api_key: str | None = None

    @field_validator("scrapers_enabled", mode="before")
    @classmethod
    def _parse_scrapers_enabled(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def resolved_config_dir(self) -> Path:
        if self.config_dir.is_absolute():
            return self.config_dir
        return Path(__file__).resolve().parents[2] / self.config_dir

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        config_dir = self.resolved_config_dir
        config_dir.mkdir(parents=True, exist_ok=True)
        return f"sqlite+aiosqlite:///{config_dir / 'tracker_tools.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
