from __future__ import annotations

from typing import Protocol


class ImageProvider(Protocol):
    async def generate_image(self, prompt: str, size: str = "1024x1024") -> str:
        ...
