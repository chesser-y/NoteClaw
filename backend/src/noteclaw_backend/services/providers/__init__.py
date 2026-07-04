from __future__ import annotations

from functools import lru_cache

from noteclaw_backend.services.providers.embedding import (
    HashingEmbeddingProvider,
    OpenAICompatibleEmbeddingProvider,
    ResilientEmbeddingProvider,
)
from noteclaw_backend.services.providers.llm import (
    FallbackLLMProvider,
    OpenAICompatibleLLMProvider,
    ResilientLLMProvider,
)
from noteclaw_backend.services.providers.vision import (
    FallbackVisionProvider,
    OpenAICompatibleVisionProvider,
    ResilientVisionProvider,
)
from noteclaw_backend.settings import get_settings


@lru_cache
def get_llm_provider() -> ResilientLLMProvider:
    settings = get_settings()
    primary = None
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
    primary = None
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
    primary = None
    if settings.openai_compat_api_key and settings.vision_model:
        primary = OpenAICompatibleVisionProvider(
            api_key=settings.openai_compat_api_key,
            model=settings.vision_model,
            base_url=settings.openai_compat_base_url,
        )
    return ResilientVisionProvider(primary, FallbackVisionProvider())
