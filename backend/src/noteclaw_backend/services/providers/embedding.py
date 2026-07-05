from __future__ import annotations

from collections import OrderedDict
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
    def __init__(self, primary: EmbeddingProvider | None, fallback: EmbeddingProvider, cache_size: int = 2048) -> None:
        self.primary = primary
        self.fallback = fallback
        self.cache_size = cache_size
        self._cache: OrderedDict[str, list[float]] = OrderedDict()

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float] | None] = [None] * len(texts)
        missing_texts: list[str] = []
        missing_indexes: list[int] = []
        for index, text in enumerate(texts):
            cached = self._cache.get(text)
            if cached is not None:
                self._cache.move_to_end(text)
                results[index] = list(cached)
                continue
            missing_indexes.append(index)
            missing_texts.append(text)

        if missing_texts:
            vectors = await self._embed_uncached(missing_texts)
            for index, text, vector in zip(missing_indexes, missing_texts, vectors):
                clean_vector = list(vector)
                results[index] = clean_vector
                self._cache[text] = clean_vector
                self._cache.move_to_end(text)
            while len(self._cache) > self.cache_size:
                self._cache.popitem(last=False)

        return [vector if vector is not None else [] for vector in results]

    async def _embed_uncached(self, texts: list[str]) -> list[list[float]]:
        if self.primary is not None:
            try:
                return await self.primary.embed_texts(texts)
            except Exception as exc:
                raise RuntimeError(
                    "Embedding API failed; refusing to fall back to local hashing embeddings because "
                    "that would mix vector spaces/dimensions in the same FAISS index. Check the "
                    "embedding API key/base URL/model, or rebuild the vector index with one embedding model."
                ) from exc
        return await self.fallback.embed_texts(texts)
