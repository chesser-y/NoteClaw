from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NoteClaw"
    app_env: str = "development"
    api_prefix: str = "/api"

    openai_compat_base_url: str | None = None
    openai_compat_api_key: str | None = None
    llm_model: str | None = None
    embedding_model: str | None = None
    vision_model: str | None = None
    image_model: str | None = None

    storage_dir: Path = Path("storage")
    faiss_index_path: Path = Path("storage/faiss/index.faiss")
    sqlite_path: Path = Path("storage/noteclaw.db")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
