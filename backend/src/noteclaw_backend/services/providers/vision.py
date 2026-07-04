from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
from typing import Protocol

from openai import AsyncOpenAI


class VisionProvider(Protocol):
    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        ...


class OpenAICompatibleVisionProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        path = Path(image_path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        prompt = (
            "Describe this image for a personal knowledge base. Extract visible text, "
            "objects, diagrams, relationships, and retrieval keywords."
        )
        if ocr_text:
            prompt += f"\nOCR text already extracted:\n{ocr_text}"
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
                    ],
                }
            ],
            temperature=0.1,
        )
        return {"description": response.choices[0].message.content or ""}


class FallbackVisionProvider:
    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        return {
            "description": (ocr_text or "No OCR text was extracted from this image."),
            "image_path": image_path,
        }


class ResilientVisionProvider:
    def __init__(self, primary: VisionProvider | None, fallback: VisionProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def understand_image(self, image_path: str, ocr_text: str | None = None) -> dict:
        if self.primary is not None:
            try:
                return await self.primary.understand_image(image_path, ocr_text)
            except Exception:
                pass
        return await self.fallback.understand_image(image_path, ocr_text)
