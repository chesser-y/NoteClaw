from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...
