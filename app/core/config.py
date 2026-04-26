from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
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
    gemini_api_key: str | None = Field(default=None)
    tavily_api_key: str | None = Field(default=None)
    webhook_hmac_secret: str | None = Field(default=None)

    enrich_urls: bool = Field(default=True)
    enrich_max_urls: int = Field(default=5, ge=0, le=20)

    llm_provider: Literal["anthropic", "gemini", "fake"] = "gemini"

    mcp_enabled: bool = Field(default=True)
    mcp_base_url: str = Field(default="http://localhost:8000")
    mcp_required_scopes: list[str] = Field(default_factory=lambda: ["openid", "email"])
    workos_authkit_domain: str | None = Field(default=None)

    fast_model: str = ""
    smart_model: str = ""

    agent_model: str = Field(default="claude-sonnet-4-6")
    agent_max_iters: int = Field(default=20)

    @model_validator(mode="after")
    def _resolve_model_defaults(self) -> Settings:
        defaults = {
            "anthropic": ("claude-haiku-4-5-20251001", "claude-sonnet-4-6"),
            "gemini": ("gemini-2.5-flash-lite", "gemini-2.5-pro"),
            "fake": ("fake-fast", "fake-smart"),
        }[self.llm_provider]
        if not self.fast_model:
            self.fast_model = defaults[0]
        if not self.smart_model:
            self.smart_model = defaults[1]
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
