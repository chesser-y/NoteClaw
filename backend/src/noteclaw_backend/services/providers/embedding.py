from __future__ import annotations

import hashlib
import re
from typing import Protocol

import numpy as np
from openai import AsyncOpenAI


class EmbeddingProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...


class OpenAICompatibleEmbeddingProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = await self.client.embeddings.create(model=self.model, input=texts)
        data = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in data]


class HashingEmbeddingProvider:
    def __init__(self, dimensions: int = 384) -> None:
        self.dimensions = dimensions

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> list[float]:
        vector = np.zeros(self.dimensions, dtype="float32")
        tokens = re.findall(r"[A-Za-z0-9_\-]+|[一-鿿]+", text.lower()) or [text[:64] or "empty"]
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[idx] += sign
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector.tolist()


class ResilientEmbeddingProvider:
    def __init__(self, primary: EmbeddingProvider | None, fallback: EmbeddingProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if self.primary is not None:
            try:
                return await self.primary.embed_texts(texts)
            except Exception:
                pass
        return await self.fallback.embed_texts(texts)
