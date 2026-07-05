from __future__ import annotations

from typing import Any


def extract_vision_text(vision: dict[str, Any] | None) -> str:
    """Normalize vision provider outputs into searchable plain text."""
    if not vision:
        return ""

    parts: list[str] = []
    for key in ("description", "summary", "caption", "text", "content", "result", "raw"):
        value = vision.get(key)
        if isinstance(value, str) and value.strip():
            parts.append(value.strip())

    for key in ("key_points", "objects", "entities", "relationships", "visible_text"):
        value = vision.get(key)
        if isinstance(value, list):
            rendered = ", ".join(str(item).strip() for item in value if str(item).strip())
            if rendered:
                parts.append(f"{key.replace('_', ' ').title()}: {rendered}")
        elif isinstance(value, str) and value.strip():
            parts.append(f"{key.replace('_', ' ').title()}: {value.strip()}")

    tags = vision.get("tags")
    if isinstance(tags, list):
        rendered_tags = ", ".join(str(tag).strip() for tag in tags if str(tag).strip())
        if rendered_tags:
            parts.append(f"Tags: {rendered_tags}")

    seen: set[str] = set()
    deduped: list[str] = []
    for part in parts:
        normalized = " ".join(part.split()).lower()
        if normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(part)
    return "\n".join(deduped).strip()
