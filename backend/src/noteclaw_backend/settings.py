from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    app_name: str = "NoteClaw"
    app_env: str = "development"
    api_prefix: str = "/api"

    openai_compat_base_url: str | None = None
    openai_compat_api_key: str | None = None
    openai_compat_chat_api_key: str | None = None
    openai_compat_chat_base_url: str | None = None
    openai_compat_chat_model: str | None = None
    openai_compat_embedding_api_key: str | None = None
    openai_compat_embedding_base_url: str | None = None
    openai_compat_embedding_model: str | None = None
    openai_compat_vision_api_key: str | None = None
    openai_compat_vision_base_url: str | None = None
    openai_compat_vision_model: str | None = None
    openai_compat_ocr_api_key: str | None = None
    openai_compat_ocr_base_url: str | None = None
    openai_compat_ocr_model: str | None = None
    openai_compat_image_api_key: str | None = None
    openai_compat_image_base_url: str | None = None
    openai_compat_image_model: str | None = None
    llm_model: str | None = None
    embedding_model: str | None = None
    vision_model: str | None = None
    image_model: str | None = None

    web_search_enabled: bool = True
    web_search_provider: str = "duckduckgo"
    web_search_api_key: str | None = None
    web_search_base_url: str | None = None
    web_search_timeout: int = 15
    web_fetch_max_chars: int = 6000
    web_use_jina_reader: bool = True
    web_user_agent: str | None = None

    storage_dir: Path = Path("storage")
    faiss_index_path: Path = Path("storage/faiss/index.faiss")
    sqlite_path: Path = Path("storage/noteclaw.db")
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])

    model_config = SettingsConfigDict(
        env_file=BACKEND_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
