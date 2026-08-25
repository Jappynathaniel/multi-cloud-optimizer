from functools import lru_cache
from pathlib import Path
import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "RedBridge FinOps"
    database_url: str = "sqlite:///./redbridge.db"
    # Required in production. A development key is generated only for local demos.
    encryption_key: str | None = None
    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    model_config = SettingsConfigDict(env_file=".env", env_prefix="REDBRIDGE_")

    @property
    def static_dir(self) -> Path:
        return Path(__file__).parent / "static"


@lru_cache
def get_settings() -> Settings:
    return Settings()

