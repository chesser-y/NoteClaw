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


def _terms(text: str) -> list[str]:
    return [term.lower() for term in re.findall(r"[A-Za-z0-9_\-]+|[\u4e00-\u9fff]+", text)]


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
        return updated

    async def delete_note(self, note_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute("delete from notes where id = ?", (note_id,))

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
            haystack = "\n".join(
                [
                    row["title"],
                    row["text"],
                    row["summary"] or "",
                    tags_text,
                    row["source"] or "",
                    row["source_url"] or "",
                ]
            ).lower()
            phrase_hits = haystack.count(query_lower) if query_lower else 0
            term_hits = sum(haystack.count(term) for term in terms)
            if phrase_hits == 0 and term_hits == 0:
                continue
            item = self._chunk_search_row(row)
            item["score"] = float(phrase_hits * 3 + term_hits)
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
