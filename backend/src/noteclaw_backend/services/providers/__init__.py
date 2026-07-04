"""Model provider adapters and provider factories."""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from noteclaw_backend.services.providers.embedding import (
    EmbeddingProvider,
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    ResilientEmbeddingProvider,
)
from noteclaw_backend.services.providers.image import ImageProvider
from noteclaw_backend.services.providers.llm import (
    FallbackLLMProvider,
    LLMProvider,
    OpenAICompatibleLLMProvider,
    ResilientLLMProvider,
)
from noteclaw_backend.services.providers.openai_api import (
    MissingCredentialsError,
    NoteClawOpenAICompat,
    OpenAICompatConfig,
    OpenAICompatError,
    ProviderEndpoint,
)
from noteclaw_backend.services.providers.vision import (
    FallbackVisionProvider,
    OpenAICompatibleVisionProvider,
    ResilientVisionProvider,
    VisionProvider,
)
from noteclaw_backend.settings import get_settings


class _OpenAICompatLLMProvider:
    def __init__(self, client: NoteClawOpenAICompat) -> None:
        self.client = client

    async def complete_text(self, messages: list[dict]) -> str:
        return await self.client.complete_text(messages)  # type: ignore[arg-type]

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        return await self.client.complete_json(messages, schema=schema)  # type: ignore[arg-type]


class _OpenAICompatEmbeddingProvider:
    def __init__(self, client: NoteClawOpenAICompat) -> None:
        self.client = client

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self.client.embed_texts(texts)


class _OpenAICompatVisionProvider:
    def __init__(self, client: NoteClawOpenAICompat) -> None:
        self.client = client

    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        result = await self.client.understand_image(image_path, ocr_text)
        if "description" not in result:
            description = result.get("summary") or result.get("raw") or result.get("text") or ""
            result = {**result, "description": str(description)}
        return result


class _OpenAICompatImageProvider:
    def __init__(self, client: NoteClawOpenAICompat) -> None:
        self.client = client

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        return await self.client.generate_image(prompt, size=size)


class FallbackImageProvider:
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        _ = prompt, size
        return ""


class ResilientImageProvider:
    def __init__(self, primary: ImageProvider | None, fallback: ImageProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        if self.primary is not None:
            try:
                return await self.primary.generate_image(prompt, size=size)
            except Exception:
                pass
        return await self.fallback.generate_image(prompt, size=size)


@lru_cache
def _openai_compat_client() -> NoteClawOpenAICompat:
    settings = get_settings()
    return NoteClawOpenAICompat.from_env_like(
        openai_compat_base_url=settings.openai_compat_base_url,
        openai_compat_api_key=settings.openai_compat_api_key,
        llm_model=settings.llm_model,
        embedding_model=settings.embedding_model,
        vision_model=settings.vision_model,
        image_model=settings.image_model,
        chat_api_key=settings.openai_compat_chat_api_key,
        chat_base_url=settings.openai_compat_chat_base_url,
        chat_model=settings.openai_compat_chat_model,
        embedding_api_key=settings.openai_compat_embedding_api_key,
        embedding_base_url=settings.openai_compat_embedding_base_url,
        embedding_model_override=settings.openai_compat_embedding_model,
        vision_api_key=settings.openai_compat_vision_api_key,
        vision_base_url=settings.openai_compat_vision_base_url,
        vision_model_override=settings.openai_compat_vision_model,
        image_api_key=settings.openai_compat_image_api_key,
        image_base_url=settings.openai_compat_image_base_url,
        image_model_override=settings.openai_compat_image_model,
        ocr_api_key=settings.openai_compat_ocr_api_key,
        ocr_base_url=settings.openai_compat_ocr_base_url,
        ocr_model=settings.openai_compat_ocr_model,
        ocr_model_override=settings.openai_compat_ocr_model,
    )


def _first_non_empty(*values: str | None) -> str | None:
    for value in values:
        if value and value.strip():
            return value.strip()
    return None


def _capability_has_key(*keys: str | None) -> bool:
    return _first_non_empty(*keys) is not None


@lru_cache
def get_llm_provider() -> ResilientLLMProvider:
    settings = get_settings()
    primary: LLMProvider | None = None
    if _capability_has_key(settings.openai_compat_chat_api_key, settings.openai_compat_api_key):
        primary = _OpenAICompatLLMProvider(_openai_compat_client())
    elif settings.openai_compat_api_key and settings.llm_model:
        primary = OpenAICompatibleLLMProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.llm_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientLLMProvider(primary, FallbackLLMProvider())


@lru_cache
def get_embedding_provider() -> ResilientEmbeddingProvider:
    settings = get_settings()
    primary: EmbeddingProvider | None = None
    if _capability_has_key(settings.openai_compat_embedding_api_key, settings.openai_compat_api_key):
        primary = _OpenAICompatEmbeddingProvider(_openai_compat_client())
    elif settings.openai_compat_api_key and settings.embedding_model:
        primary = OpenAICompatibleEmbeddingProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.embedding_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientEmbeddingProvider(primary, HashingEmbeddingProvider())


@lru_cache
def get_vision_provider() -> ResilientVisionProvider:
    settings = get_settings()
    primary: VisionProvider | None = None
    if _capability_has_key(settings.openai_compat_vision_api_key, settings.openai_compat_api_key):
        primary = _OpenAICompatVisionProvider(_openai_compat_client())
    elif settings.openai_compat_api_key and settings.vision_model:
        primary = OpenAICompatibleVisionProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.vision_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientVisionProvider(primary, FallbackVisionProvider())


@lru_cache
def get_image_provider() -> ResilientImageProvider:
    settings = get_settings()
    primary: ImageProvider | None = None
    if _capability_has_key(settings.openai_compat_image_api_key, settings.openai_compat_api_key):
        primary = _OpenAICompatImageProvider(_openai_compat_client())
    return ResilientImageProvider(primary, FallbackImageProvider())


__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "ResilientEmbeddingProvider",
    "ImageProvider",
    "FallbackImageProvider",
    "ResilientImageProvider",
    "LLMProvider",
    "OpenAICompatibleLLMProvider",
    "ResilientLLMProvider",
    "FallbackLLMProvider",
    "OpenAICompatConfig",
    "OpenAICompatError",
    "MissingCredentialsError",
    "NoteClawOpenAICompat",
    "ProviderEndpoint",
    "VisionProvider",
    "FallbackVisionProvider",
    "OpenAICompatibleVisionProvider",
    "ResilientVisionProvider",
    "get_embedding_provider",
    "get_image_provider",
    "get_llm_provider",
    "get_vision_provider",
]
