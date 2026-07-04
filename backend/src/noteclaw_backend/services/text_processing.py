from __future__ import annotations

import re
from dataclasses import dataclass

from noteclaw_backend.domain.enums import ContentType
from noteclaw_backend.services.providers.llm import LLMProvider


@dataclass(frozen=True)
class ContentMetadata:
    title: str
    summary: str
    tags: list[str]
    category: str


async def enrich_content(
    *,
    content: str,
    content_type: ContentType,
    title: str | None,
    llm: LLMProvider,
) -> ContentMetadata:
    fallback = fallback_metadata(content=content, content_type=content_type, title=title)
    messages = [
        {
            "role": "system",
            "content": "You extract concise metadata for a personal knowledge base. Return JSON only.",
        },
        {
            "role": "user",
            "content": (
                "Create metadata with keys: title, summary, tags, category. "
                "Use 3-8 short tags and one simple category.\n"
                f"Content type: {content_type.value}\n"
                f"Given title: {title or ''}\n"
                f"Content:\n{content[:8000]}"
            ),
        },
    ]
    data = await llm.complete_json(messages)
    clean_title = _clean_string(data.get("title")) or fallback.title
    if clean_title.lower().startswith("you extract"):
        clean_title = fallback.title
    summary = _clean_string(data.get("summary")) or fallback.summary
    tags = _clean_tags(data.get("tags")) or fallback.tags
    category = _clean_string(data.get("category")) or fallback.category
    return ContentMetadata(
        title=clean_title[:120],
        summary=summary[:800],
        tags=tags[:10],
        category=category[:80],
    )


def fallback_metadata(
    *,
    content: str,
    content_type: ContentType,
    title: str | None = None,
) -> ContentMetadata:
    clean_title = title or _title_from_content(content) or "Untitled note"
    return ContentMetadata(
        title=clean_title[:120],
        summary=_summary(content),
        tags=_keywords(content),
        category=_category(content, content_type),
    )


def chunk_text(text: str, *, chunk_size: int = 1200, overlap: int = 160) -> list[str]:
    text = text.strip()
    if not text:
        return []
    units = _split_units(text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    active_header = ""

    def flush() -> None:
        nonlocal current, current_len
        if not current:
            return
        chunk = "\n".join(part for part in current if part).strip()
        if chunk:
            chunks.append(chunk)
        tail = chunk[-overlap:] if overlap > 0 and len(chunk) > overlap else ""
        current = [tail] if tail else []
        current_len = len(tail)

    for unit in units:
        stripped = unit.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            active_header = stripped[:160]
        if len(stripped) > chunk_size:
            flush()
            for piece in _split_long(stripped, chunk_size=chunk_size, overlap=overlap):
                if active_header and not piece.startswith(active_header):
                    piece = f"{active_header}\n{piece}"
                chunks.append(piece.strip())
            current = []
            current_len = 0
            continue
        prefix = f"{active_header}\n" if active_header and not current and not stripped.startswith(active_header) else ""
        addition = prefix + stripped
        if current_len + len(addition) + 1 > chunk_size:
            flush()
        current.append(addition)
        current_len += len(addition) + 1
    if current:
        chunk = "\n".join(part for part in current if part).strip()
        if chunk and (not chunks or chunk != chunks[-1]):
            chunks.append(chunk)
    return [chunk for chunk in chunks if chunk.strip()]


def _split_units(text: str) -> list[str]:
    units: list[str] = []
    buffer: list[str] = []
    in_code = False
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            buffer.append(line)
            in_code = not in_code
            if not in_code:
                units.append("\n".join(buffer))
                buffer = []
            continue
        if in_code:
            buffer.append(line)
            continue
        is_table_row = stripped.startswith("|") and stripped.endswith("|")
        if is_table_row:
            if buffer and not in_table:
                units.append("\n".join(buffer))
                buffer = []
            in_table = True
            buffer.append(line)
            continue
        if in_table:
            units.append("\n".join(buffer))
            buffer = []
            in_table = False
        if not stripped:
            if buffer:
                units.append("\n".join(buffer))
                buffer = []
            continue
        buffer.append(line)
    if buffer:
        units.append("\n".join(buffer))
    return units


def _split_long(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        cut = max(text.rfind("\n", start, end), text.rfind("。", start, end), text.rfind(".", start, end))
        if cut <= start + chunk_size * 0.45:
            cut = end
        pieces.append(text[start:cut].strip())
        if cut >= len(text):
            break
        start = max(cut - overlap, start + 1)
    return pieces


def _title_from_content(content: str) -> str:
    for line in content.splitlines():
        stripped = line.strip().strip("#").strip()
        if stripped:
            return stripped
    return ""


def _summary(content: str, limit: int = 420) -> str:
    cleaned = re.sub(r"\s+", " ", content).strip()
    if len(cleaned) <= limit:
        return cleaned
    cut = max(cleaned.rfind(".", 0, limit), cleaned.rfind("。", 0, limit), cleaned.rfind(";", 0, limit))
    if cut < limit * 0.45:
        cut = limit
    return cleaned[:cut].strip() + "..."


def _keywords(content: str, limit: int = 8) -> list[str]:
    words = [w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9_\-]{2,}|[\u4e00-\u9fff]{2,}", content)]
    stop = {"the", "and", "for", "with", "this", "that", "from", "have", "will", "into", "using", "use"}
    counts: dict[str, int] = {}
    for word in words:
        if word in stop:
            continue
        counts[word] = counts.get(word, 0) + 1
    return [word for word, _ in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]] or ["note"]


def _category(content: str, content_type: ContentType) -> str:
    if content_type == ContentType.CODE:
        return "code"
    if content_type == ContentType.TABLE:
        return "data"
    if content_type == ContentType.IMAGE:
        return "image"
    lowered = content.lower()
    if any(word in lowered for word in ["rag", "embedding", "faiss", "retrieval", "vector"]):
        return "rag"
    if any(word in lowered for word in ["api", "fastapi", "backend", "database"]):
        return "engineering"
    if any(word in lowered for word in ["paper", "abstract", "experiment", "论文"]):
        return "research"
    return "general"


def _clean_string(value: object) -> str:
    return str(value).strip() if isinstance(value, str) else ""


def _clean_tags(value: object) -> list[str]:
    if isinstance(value, str):
        raw = re.split(r"[,，;；\n]", value)
    elif isinstance(value, list):
        raw = [str(item) for item in value]
    else:
        raw = []
    tags: list[str] = []
    seen: set[str] = set()
    for item in raw:
        tag = item.strip().strip("#")[:40]
        key = tag.lower()
        if tag and key not in seen:
            tags.append(tag)
            seen.add(key)
    return tags
