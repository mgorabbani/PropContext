from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="APP_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "buena-context"
    version: str = "0.1.0"
    env: Literal["dev", "staging", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    data_dir: Path = Field(default=REPO_ROOT / "data")
    output_dir: Path = Field(default=REPO_ROOT / "output")
    wiki_dir: Path = Field(default=REPO_ROOT / "wiki")
    normalize_dir: Path = Field(default=REPO_ROOT / "normalize")

    anthropic_api_key: str | None = Field(default=None)
    webhook_hmac_secret: str | None = Field(default=None)

    haiku_model: str = "claude-haiku-4-5-20251001"
    sonnet_model: str = "claude-sonnet-4-6"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
