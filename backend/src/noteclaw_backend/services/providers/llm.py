from __future__ import annotations

from typing import Protocol


class LLMProvider(Protocol):
    async def complete_text(self, messages: list[dict]) -> str:
        ...

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        ...
