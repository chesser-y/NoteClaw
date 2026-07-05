from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from sqlite3 import Row
from typing import Any, Iterable

from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.settings import get_settings
from noteclaw_backend.storage.sqlite import SQLiteStore


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


@dataclass
class ChatSessionRow:
    id: str
    title: str
    scope: dict[str, Any]
    created_at: datetime
    updated_at: datetime
    message_count: int
    is_favorite: bool = False


@dataclass
class ChatMessageRow:
    id: str
    session_id: str
    role: str
    content: str
    citations: list[dict[str, Any]]
    trace: dict[str, Any]
    created_at: datetime


class SQLiteChatRepository:
    def __init__(self, store: SQLiteStore) -> None:
        self.store = store
        self.store.init_schema()

    async def create_session(
        self,
        *,
        title: str,
        scope: dict[str, Any],
    ) -> ChatSessionRow:
        session_id = new_id("chat")
        now = utc_now()
        with self.store.connect() as conn:
            conn.execute(
                """
                insert into chat_sessions(id, title, scope_json, created_at, updated_at)
                values (?, ?, ?, ?, ?)
                """,
                (session_id, title, _dump(scope), _iso(now), _iso(now)),
            )
        return ChatSessionRow(
            id=session_id,
            title=title,
            scope=scope,
            created_at=now,
            updated_at=now,
            message_count=0,
        )

    async def get_session(self, session_id: str) -> ChatSessionRow | None:
        with self.store.connect() as conn:
            row = conn.execute(
                """
                select s.*, (
                    select count(*) from chat_messages m where m.session_id = s.id
                ) as message_count
                from chat_sessions s
                where s.id = ?
                """,
                (session_id,),
            ).fetchone()
        if row is None:
            return None
        return self._session_row(row)

    async def list_sessions(
        self, limit: int = 50, *, favorites_only: bool = False
    ) -> list[ChatSessionRow]:
        where = "where s.is_favorite = 1" if favorites_only else ""
        sql = f"""
            select s.*, (
                select count(*) from chat_messages m where m.session_id = s.id
            ) as message_count
            from chat_sessions s
            {where}
            order by s.updated_at desc
            limit ?
        """
        with self.store.connect() as conn:
            rows = conn.execute(sql, (limit,)).fetchall()
        return [self._session_row(row) for row in rows]

    async def rename_session(self, session_id: str, title: str) -> None:
        with self.store.connect() as conn:
            conn.execute(
                "update chat_sessions set title = ?, updated_at = ? where id = ?",
                (title, _iso(utc_now()), session_id),
            )

    async def set_session_favorite(self, session_id: str, value: bool) -> bool:
        with self.store.connect() as conn:
            cur = conn.execute(
                "update chat_sessions set is_favorite = ?, updated_at = ? where id = ?",
                (1 if value else 0, _iso(utc_now()), session_id),
            )
            return cur.rowcount > 0

    async def touch_session(self, session_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute(
                "update chat_sessions set updated_at = ? where id = ?",
                (_iso(utc_now()), session_id),
            )

    async def delete_session(self, session_id: str) -> None:
        with self.store.connect() as conn:
            conn.execute(
                "delete from chat_messages where session_id = ?",
                (session_id,),
            )
            conn.execute("delete from chat_sessions where id = ?", (session_id,))

    async def append_message(
        self,
        *,
        session_id: str,
        role: str,
        content: str,
        citations: list[dict[str, Any]],
        trace: dict[str, Any],
    ) -> ChatMessageRow:
        message_id = new_id("msg")
        now = utc_now()
        with self.store.connect() as conn:
            conn.execute(
                """
                insert into chat_messages(
                    id, session_id, role, content, citations_json, trace_json, created_at
                ) values (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    session_id,
                    role,
                    content,
                    _dump(citations),
                    _dump(trace),
                    _iso(now),
                ),
            )
            conn.execute(
                "update chat_sessions set updated_at = ? where id = ?",
                (_iso(now), session_id),
            )
        return ChatMessageRow(
            id=message_id,
            session_id=session_id,
            role=role,
            content=content,
            citations=citations,
            trace=trace,
            created_at=now,
        )

    async def list_messages(
        self,
        session_id: str,
        *,
        limit: int = 100,
    ) -> list[ChatMessageRow]:
        with self.store.connect() as conn:
            rows = conn.execute(
                """
                select * from chat_messages
                where session_id = ?
                order by created_at asc, id asc
                limit ?
                """,
                (session_id, limit),
            ).fetchall()
        return [self._message_row(row) for row in rows]

    def _session_row(self, row: Row) -> ChatSessionRow:
        keys = set(row.keys())
        return ChatSessionRow(
            id=row["id"],
            title=row["title"],
            scope=_load(row["scope_json"], {}),
            created_at=_dt(row["created_at"]),
            updated_at=_dt(row["updated_at"]),
            message_count=int(row["message_count"] or 0),
            is_favorite=bool(row["is_favorite"]) if "is_favorite" in keys else False,
        )

    def _message_row(self, row: Row) -> ChatMessageRow:
        return ChatMessageRow(
            id=row["id"],
            session_id=row["session_id"],
            role=row["role"],
            content=row["content"],
            citations=_load(row["citations_json"], []),
            trace=_load(row["trace_json"], {}),
            created_at=_dt(row["created_at"]),
        )


@lru_cache
def get_chat_repository() -> SQLiteChatRepository:
    settings = get_settings()
    return SQLiteChatRepository(SQLiteStore(settings.sqlite_path))
