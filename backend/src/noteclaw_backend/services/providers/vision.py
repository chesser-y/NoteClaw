from __future__ import annotations

from typing import Protocol


class VisionProvider(Protocol):
    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        ...
