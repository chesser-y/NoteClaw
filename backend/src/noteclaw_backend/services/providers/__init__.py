"""Model provider adapters and provider factories."""

from __future__ import annotations

from functools import lru_cache

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


@lru_cache
def get_llm_provider() -> ResilientLLMProvider:
    settings = get_settings()
    primary: OpenAICompatibleLLMProvider | None = None
    if settings.openai_compat_api_key and settings.llm_model:
        primary = OpenAICompatibleLLMProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.llm_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientLLMProvider(primary, FallbackLLMProvider())


@lru_cache
def get_embedding_provider() -> ResilientEmbeddingProvider:
    settings = get_settings()
    primary: OpenAICompatibleEmbeddingProvider | None = None
    if settings.openai_compat_api_key and settings.embedding_model:
        primary = OpenAICompatibleEmbeddingProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.embedding_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientEmbeddingProvider(primary, HashingEmbeddingProvider())


@lru_cache
def get_vision_provider() -> ResilientVisionProvider:
    settings = get_settings()
    primary: OpenAICompatibleVisionProvider | None = None
    if settings.openai_compat_api_key and settings.vision_model:
        primary = OpenAICompatibleVisionProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.vision_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientVisionProvider(primary, FallbackVisionProvider())


__all__ = [
    "EmbeddingProvider",
    "HashingEmbeddingProvider",
    "OpenAICompatibleEmbeddingProvider",
    "ResilientEmbeddingProvider",
    "ImageProvider",
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
    "get_llm_provider",
    "get_vision_provider",
]
