from __future__ import annotations

import json
import re
from datetime import date, datetime
from functools import lru_cache
from sqlite3 import Row
from typing import Any, Protocol

from noteclaw_backend.domain.enums import ContentType, NoteStatus
from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.schemas.knowledge import ChunkRead, NoteDetail, NoteListItem
from noteclaw_backend.settings import get_settings
from noteclaw_backend.storage.sqlite import SQLiteStore


class NoteRepository(Protocol):
    async def create_note(self, note: NoteDetail) -> None:
        ...

    async def get_note(self, note_id: str) -> NoteDetail | None:
        ...

    async def list_notes(self, limit: int, offset: int) -> tuple[list[NoteListItem], int]:
        ...

    async def delete_note(self, note_id: str) -> None:
        ...

    async def facets(self) -> dict[str, list[Any]]:
        ...


class ChunkRepository(Protocol):
    async def list_by_note(self, note_id: str) -> list[dict]:
        ...

    async def get_by_ids(self, chunk_ids: list[str]) -> list[dict]:
        ...


def _dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


KEYWORD_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "based",
    "be",
    "before",
    "by",
    "can",
    "does",
    "for",
    "from",
    "has",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "which",
    "with",
}

CJK_STOPWORDS = {
    "一个",
    "一下",
    "什么",
    "什么是",
    "哪些",
    "哪个",
    "如何",
    "怎么",
    "怎么办",
    "是否",
    "可以",
    "需要",
    "这个",
    "那个",
    "请问",
}


def _terms(text: str) -> list[str]:
    terms: list[str] = []
    for term in re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]+", text):
        lowered = term.lower()
        if _is_cjk(lowered):
            terms.extend(_cjk_terms(lowered))
        else:
            terms.append(lowered)
    filtered = [
        term
        for term in dict.fromkeys(terms)
        if term not in KEYWORD_STOPWORDS and term not in CJK_STOPWORDS and len(term) > 1
    ]
    return filtered or terms


def _is_cjk(text: str) -> bool:
    return bool(text) and all("\u4e00" <= char <= "\u9fff" for char in text)


def _cjk_terms(text: str) -> list[str]:
    if len(text) <= 4:
        return [text]
    terms = [text]
    for size in (4, 3, 2):
        for index in range(0, len(text) - size + 1):
            gram = text[index : index + size]
            if gram not in CJK_STOPWORDS:
                terms.append(gram)
    return terms


def _snippet(text: str, query: str, size: int = 220) -> str:
    lowered = text.lower()
    candidates = [query.lower(), *_terms(query)]
    pos = -1
    for candidate in candidates:
        if not candidate:
            continue
        pos = lowered.find(candidate)
        if pos >= 0:
            break
    if pos < 0:
        return text[:size].strip()
    start = max(0, pos - size // 3)
    end = min(len(text), start + size)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(text) else ""
    return f"{prefix}{text[start:end].strip()}{suffix}"


class SQLiteKnowledgeRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self.store.init_schema()

    async def create_note(self, note: NoteDetail) -> None:
        with self.store.connect() as conn:
            conn.execute("delete from chunks where note_id = ?", (note.id,))
            conn.execute(
                """
                insert or replace into notes(
                    id, title, content_type, content, summary, tags_json, category,
                    source, source_url, status, metadata_json, created_at, updated_at
                ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    note.id,
                    note.title,
                    note.content_type.value,
                    note.content,
                    note.summary,
                    _dump(note.tags),
                    note.category,
                    note.source,
                    note.source_url,
                    note.status.value,
                    _dump(note.metadata),
                    _iso(note.created_at),
                    _iso(note.updated_at),
                ),
            )
            for chunk in note.chunks:
                conn.execute(
                    """
                    insert into chunks(id, note_id, chunk_index, text, metadata_json, created_at)
                    values (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        chunk.id,
                        chunk.note_id,
                        chunk.chunk_index,
                        chunk.text,
                        _dump({}),
                        _iso(note.created_at),
                    ),
                )

    async def get_note(self, note_id: str) -> NoteDetail | None:
        with self.store.connect() as conn:
            row = conn.execute("select * from notes where id = ?", (note_id,)).fetchone()
            if row is None:
                return None
            chunks = conn.execute(
                "select * from chunks where note_id = ? order by chunk_index",
                (note_id,),
            ).fetchall()
        return self._note_detail(row, chunks)

    async def list_notes(
        self,
        limit: int,
        offset: int,
        *,
        q: str | None = None,
        content_type: ContentType | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        source: str | None = None,
        source_contains: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        metadata_filters: dict[str, str] | None = None,
        is_favorite: bool | None = None,
    ) -> tuple[list[NoteListItem], int]:
        clauses = []
        params: list[Any] = []
        if q:
            like = f"%{q}%"
            clauses.append(
                "(title like ? or content like ? or coalesce(summary, '') like ? or "
                "coalesce(tags_json, '') like ? or coalesce(source, '') like ? or coalesce(source_url, '') like ?)"
            )
            params.extend([like, like, like, like, like, like])
        if content_type:
            clauses.append("content_type = ?")
            params.append(content_type.value)
        if category:
            clauses.append("category = ?")
            params.append(category)
        if source:
            clauses.append("(source = ? or source_url = ?)")
            params.extend([source, source])
        if source_contains:
            like = f"%{source_contains}%"
            clauses.append("(coalesce(source, '') like ? or coalesce(source_url, '') like ?)")
            params.extend([like, like])
        if date_from:
            clauses.append("date(created_at) >= ?")
            params.append(date_from.isoformat())
        if date_to:
            clauses.append("date(created_at) <= ?")
            params.append(date_to.isoformat())
        if metadata_filters:
            for key, value in metadata_filters.items():
                clauses.append("json_extract(metadata_json, ?) = ?")
                params.extend([f"$.{key}", value])
        if is_favorite is not None:
            clauses.append("is_favorite = ?")
            params.append(1 if is_favorite else 0)
        where = " where " + " and ".join(clauses) if clauses else ""
        with self.store.connect() as conn:
            rows = conn.execute(
                f"select * from notes{where} order by updated_at desc",
                params,
            ).fetchall()
        wanted_tags = {tag.lower() for tag in (tags or []) if tag}
        if wanted_tags:
            rows = [row for row in rows if wanted_tags.issubset({t.lower() for t in _load(row['tags_json'], [])})]
        total = len(rows)
        page = rows[offset : offset + limit]
        return [self._note_list_item(row) for row in page], total

    async def update_note(
        self,
        note_id: str,
        *,
        title: str | None = None,
        summary: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
    ) -> NoteDetail | None:
        current = await self.get_note(note_id)
        if current is None:
            return None
        updated = current.model_copy(
            update={
                "title": title if title is not None else current.title,
                "summary": summary if summary is not None else current.summary,
                "tags": tags if tags is not None else current.tags,
                "category": category if category is not None else current.category,
                "updated_at": utc_now(),
            }
        )
        await self.create_note(updated)

    async def set_note_favorite(self, note_id: str, value: bool) -> bool:
        with self.store.connect() as conn:
            cur = conn.execute(
                "update notes set is_favorite = ?, updated_at = ? where id = ?",
                (1 if value else 0, _iso(utc_now()), note_id),
            )
            return cur.rowcount > 0
        return updated

    async def delete_note(self, note_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute("delete from notes where id = ?", (note_id,))

    async def facets(self) -> dict[str, list[Any]]:
        with self.store.connect() as conn:
            tag_rows = conn.execute(
                "select tags_json from notes where coalesce(tags_json, '') != ''"
            ).fetchall()
            sources = conn.execute(
                "select distinct source from notes where source is not null and source != '' order by source"
            ).fetchall()
            categories = conn.execute(
                "select distinct category from notes where category is not null and category != '' order by category"
            ).fetchall()
            content_types = conn.execute(
                "select distinct content_type from notes order by content_type"
            ).fetchall()
        tag_counts: dict[str, int] = {}
        for row in tag_rows:
            for tag in _load(row["tags_json"], []):
                if not isinstance(tag, str):
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1
        tags_sorted = sorted(tag_counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return {
            "tags": tags_sorted,
            "sources": [row["source"] for row in sources],
            "categories": [row["category"] for row in categories],
            "content_types": [row["content_type"] for row in content_types],
        }

    async def add_feedback(
        self,
        note_id: str,
        target: str,
        rating: int,
        comment: str | None,
    ) -> None:
        with self.store.connect() as conn:
            conn.execute(
                """
                insert into feedback(id, note_id, target, rating, comment, created_at)
                values (?, ?, ?, ?, ?, ?)
                """,
                (new_id("feedback"), note_id, target, rating, comment, _iso(utc_now())),
            )

    async def list_by_note(self, note_id: str) -> list[dict]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                select c.*, n.title, n.content_type, n.summary, n.tags_json, n.category,
                       n.source, n.source_url, n.created_at as note_created_at, n.updated_at as note_updated_at
                from chunks c join notes n on n.id = c.note_id
                where c.note_id = ?
                order by c.chunk_index
                """,
                (note_id,),
            ).fetchall()
        return [self._chunk_search_row(row) for row in rows]

    async def get_by_ids(self, chunk_ids: list[str]) -> list[dict]:
        if not chunk_ids:
            return []
        placeholders = ",".join("?" for _ in chunk_ids)
        with self.store.connect() as conn:
            rows = conn.execute(
                f"""
                select c.*, n.title, n.content_type, n.summary, n.tags_json, n.category,
                       n.source, n.source_url, n.created_at as note_created_at, n.updated_at as note_updated_at
                from chunks c join notes n on n.id = c.note_id
                where c.id in ({placeholders})
                """,
                chunk_ids,
            ).fetchall()
        by_id = {row["id"]: self._chunk_search_row(row) for row in rows}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    async def keyword_search(self, query: str, filters: Any, limit: int) -> list[dict]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                select c.*, n.title, n.content_type, n.summary, n.tags_json, n.category,
                       n.source, n.source_url, n.created_at as note_created_at, n.updated_at as note_updated_at
                from chunks c join notes n on n.id = c.note_id
                where n.status = ?
                """,
                (NoteStatus.READY.value,),
            ).fetchall()
        terms = _terms(query)
        query_lower = query.lower()
        scored: list[dict] = []
        for row in rows:
            if not self._row_matches_filters(row, filters):
                continue
            tags_text = " ".join(_load(row["tags_json"], []))
            title_text = row["title"].lower()
            body_text = row["text"].lower()
            summary_text = (row["summary"] or "").lower()
            metadata_text = "\n".join([tags_text, row["source"] or "", row["source_url"] or ""]).lower()
            haystack = "\n".join([title_text, body_text, summary_text, metadata_text])
            phrase_hits = haystack.count(query_lower) if query_lower else 0
            term_score = 0.0
            for term in dict.fromkeys(terms):
                if term in title_text:
                    term_score += 4.0
                if term in metadata_text:
                    term_score += 3.0
                if term in summary_text:
                    term_score += 2.0
                term_score += min(body_text.count(term), 3) * 1.0
            if phrase_hits == 0 and term_score == 0:
                continue
            item = self._chunk_search_row(row)
            item["score"] = float(phrase_hits * 8 + term_score)
            item["snippet"] = _snippet(row["text"], query)
            scored.append(item)
        scored.sort(key=lambda item: item["score"], reverse=True)
        return scored[:limit]

    async def upsert_vector_mappings(
        self,
        chunk_ids: list[str],
        row_ids: list[int],
        embedding_model: str,
    ) -> None:
        with self.store.connect() as conn:
            for chunk_id, row_id in zip(chunk_ids, row_ids):
                conn.execute(
                    """
                    insert or replace into vector_mappings(
                        chunk_id, faiss_row_id, embedding_model, deleted
                    ) values (?, ?, ?, 0)
                    """,
                    (chunk_id, row_id, embedding_model),
                )

    async def mark_vectors_deleted(self, chunk_ids: list[str]) -> None:
        if not chunk_ids:
            return
        placeholders = ",".join("?" for _ in chunk_ids)
        with self.store.connect() as conn:
            conn.execute(
                f"update vector_mappings set deleted = 1 where chunk_id in ({placeholders})",
                chunk_ids,
            )

    async def active_chunk_ids_by_faiss_rows(self, row_ids: list[int]) -> dict[int, str]:
        if not row_ids:
            return {}
        placeholders = ",".join("?" for _ in row_ids)
        with self.store.connect() as conn:
            rows = conn.execute(
                f"""
                select faiss_row_id, chunk_id from vector_mappings
                where deleted = 0 and faiss_row_id in ({placeholders})
                """,
                row_ids,
            ).fetchall()
        return {int(row["faiss_row_id"]): row["chunk_id"] for row in rows}

    def _note_detail(self, row: Row, chunks: list[Row]) -> NoteDetail:
        return NoteDetail(
            id=row["id"],
            title=row["title"],
            content_type=ContentType(row["content_type"]),
            content=row["content"],
            summary=row["summary"],
            tags=_load(row["tags_json"], []),
            category=row["category"],
            source=row["source"],
            source_url=row["source_url"],
            status=NoteStatus(row["status"]),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
            metadata=_load(row["metadata_json"], {}),
            is_favorite=bool(row["is_favorite"]) if "is_favorite" in row.keys() else False,
            chunks=[
                ChunkRead(
                    id=chunk["id"],
                    note_id=chunk["note_id"],
                    text=chunk["text"],
                    chunk_index=int(chunk["chunk_index"]),
                )
                for chunk in chunks
            ],
        )

    def _note_list_item(self, row: Row) -> NoteListItem:
        return NoteListItem(
            id=row["id"],
            title=row["title"],
            content_type=ContentType(row["content_type"]),
            summary=row["summary"],
            tags=_load(row["tags_json"], []),
            category=row["category"],
            source=row["source"],
            source_url=row["source_url"],
            status=NoteStatus(row["status"]),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
            is_favorite=bool(row["is_favorite"]) if "is_favorite" in row.keys() else False,
        )

    def _chunk_search_row(self, row: Row) -> dict:
        created_at = self._row_value(row, "note_created_at") or self._row_value(row, "created_at")
        updated_at = self._row_value(row, "note_updated_at") or self._row_value(row, "updated_at")
        return {
            "chunk_id": row["id"],
            "note_id": row["note_id"],
            "chunk_index": int(row["chunk_index"]),
            "text": row["text"],
            "title": row["title"],
            "content_type": ContentType(row["content_type"]),
            "summary": self._row_value(row, "summary"),
            "tags": _load(row["tags_json"], []),
            "source": row["source"],
            "source_url": self._row_value(row, "source_url"),
            "category": row["category"],
            "created_at": _dt(created_at) if created_at else None,
            "updated_at": _dt(updated_at) if updated_at else None,
            "score": None,
            "snippet": row["text"][:220],
        }

    def _row_value(self, row: Row, key: str) -> Any:
        try:
            return row[key]
        except (IndexError, KeyError):
            return None

    def _row_matches_filters(self, row: Row, filters: Any) -> bool:
        content_types = getattr(filters, "content_types", []) or []
        tags = getattr(filters, "tags", []) or []
        category = getattr(filters, "category", None)
        date_from: date | None = getattr(filters, "date_from", None)
        date_to: date | None = getattr(filters, "date_to", None)
        if content_types and row["content_type"] not in {item.value for item in content_types}:
            return False
        row_tags = {tag.lower() for tag in _load(row["tags_json"], [])}
        if tags and not {tag.lower() for tag in tags}.issubset(row_tags):
            return False
        if category and row["category"] != category:
            return False
        source = getattr(filters, "source", None)
        source_contains = getattr(filters, "source_contains", None)
        if source and row["source"] != source and self._row_value(row, "source_url") != source:
            return False
        if source_contains:
            needle = source_contains.lower()
            haystack = f"{row['source'] or ''}\n{self._row_value(row, 'source_url') or ''}".lower()
            if needle not in haystack:
                return False
        created_raw = self._row_value(row, "note_created_at") or self._row_value(row, "created_at")
        created = _dt(created_raw).date()
        if date_from and created < date_from:
            return False
        if date_to and created > date_to:
            return False
        return True


@lru_cache
def get_repository() -> SQLiteKnowledgeRepository:
    settings = get_settings()
    return SQLiteKnowledgeRepository(SQLiteStore(settings.sqlite_path))
