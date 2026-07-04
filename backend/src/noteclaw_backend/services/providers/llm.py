from __future__ import annotations

import json
import re
from typing import Protocol

from openai import AsyncOpenAI


class LLMProvider(Protocol):
    async def complete_text(self, messages: list[dict]) -> str:
        ...

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        ...


class OpenAICompatibleLLMProvider:
    def __init__(self, *, api_key: str, model: str, base_url: str | None = None) -> None:
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def complete_text(self, messages: list[dict]) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return response.choices[0].message.content or ""

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        _ = schema
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content or "{}"
        except Exception:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
            )
            text = response.choices[0].message.content or "{}"
        return _parse_json_object(text)


class FallbackLLMProvider:
    async def complete_text(self, messages: list[dict]) -> str:
        user_text = "\n".join(str(msg.get("content", "")) for msg in messages if msg.get("role") == "user")
        context = _extract_between(user_text, "Context:", "Question:") or user_text
        question = _extract_after(user_text, "Question:") or "the question"
        evidence_lines = [line.strip() for line in context.splitlines() if line.strip()]
        useful = [line for line in evidence_lines if not line.lower().startswith("source")][:4]
        if useful:
            return (
                f"Based on the stored knowledge, the answer to '{question.strip()}' is mainly supported by: "
                + " ".join(useful)
            )[:1600]
        return "I could not find enough relevant knowledge in the current library to answer confidently."

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        _ = schema
        text = "\n".join(str(msg.get("content", "")) for msg in messages)
        content = _extract_after(text, "Content:") or text
        return {
            "title": _first_line(content) or "Untitled note",
            "summary": _summary(content),
            "tags": _keywords(content),
            "category": _category(content),
        }


class ResilientLLMProvider:
    def __init__(self, primary: LLMProvider | None, fallback: LLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    async def complete_text(self, messages: list[dict]) -> str:
        if self.primary is not None:
            try:
                return await self.primary.complete_text(messages)
            except Exception:
                pass
        return await self.fallback.complete_text(messages)

    async def complete_json(self, messages: list[dict], schema: dict | None = None) -> dict:
        if self.primary is not None:
            try:
                return await self.primary.complete_json(messages, schema)
            except Exception:
                pass
        return await self.fallback.complete_json(messages, schema)


def _parse_json_object(text: str) -> dict:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}


def _extract_between(text: str, start: str, end: str) -> str:
    if start not in text:
        return ""
    rest = text.split(start, 1)[1]
    return rest.split(end, 1)[0] if end in rest else rest


def _extract_after(text: str, marker: str) -> str:
    return text.split(marker, 1)[1] if marker in text else ""


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip(" #\t")
        if stripped:
            return stripped[:80]
    return ""


def _summary(text: str, limit: int = 360) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip()
    if len(cleaned) <= limit:
        return cleaned
    cut = max(cleaned.rfind(".", 0, limit), cleaned.rfind("。", 0, limit), cleaned.rfind("\n", 0, limit))
    if cut < limit * 0.45:
        cut = limit
    return cleaned[:cut].strip() + "..."


def _keywords(text: str, limit: int = 6) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", text)]
    stop = {"the", "and", "for", "with", "this", "that", "from", "are", "was", "were", "you", "your"}
    counts: dict[str, int] = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _category(text: str) -> str:
    lowered = text.lower()
    buckets = {
        "code": ["def ", "class ", "function", "api", "bug", "error"],
        "machine_learning": ["embedding", "transformer", "model", "training", "rag"],
        "data": ["table", "csv", "column", "row", "dataset"],
        "research": ["paper", "abstract", "method", "experiment", "论文"],
    }
    for category, needles in buckets.items():
        if any(needle in lowered for needle in needles):
            return category
    return "general"
