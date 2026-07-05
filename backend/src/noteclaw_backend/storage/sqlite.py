from __future__ import annotations

from pathlib import Path
from sqlite3 import Connection, Row, connect


SCHEMA_SQL = """
create table if not exists notes(
  id text primary key,
  title text not null,
  content_type text not null,
  content text not null,
  summary text,
  tags_json text not null,
  category text,
  source text,
  source_url text,
  status text not null,
  metadata_json text not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists chunks(
  id text primary key,
  note_id text not null references notes(id) on delete cascade,
  chunk_index integer not null,
  text text not null,
  metadata_json text not null,
  created_at text not null
);

create table if not exists vector_mappings(
  chunk_id text primary key references chunks(id) on delete cascade,
  faiss_row_id integer not null,
  embedding_model text not null,
  deleted integer not null default 0
);

create table if not exists feedback(
  id text primary key,
  note_id text not null references notes(id) on delete cascade,
  target text not null,
  rating integer not null,
  comment text,
  created_at text not null
);

create table if not exists chat_sessions(
  id text primary key,
  title text not null,
  scope_json text not null,
  created_at text not null,
  updated_at text not null
);

create table if not exists chat_messages(
  id text primary key,
  session_id text not null references chat_sessions(id) on delete cascade,
  role text not null,
  content text not null,
  citations_json text not null,
  trace_json text not null,
  created_at text not null
);

create table if not exists review_items(
  id text primary key,
  type text not null,
  payload_json text not null,
  status text not null default 'pending',
  created_at text not null,
  resolved_at text
);

create index if not exists idx_chunks_note_id on chunks(note_id);
create index if not exists idx_notes_content_type on notes(content_type);
create index if not exists idx_notes_status on notes(status);
create index if not exists idx_vector_mappings_row on vector_mappings(faiss_row_id);
create index if not exists idx_chat_messages_session on chat_messages(session_id, created_at);
create index if not exists idx_chat_sessions_updated on chat_sessions(updated_at desc);
create index if not exists idx_review_items_status on review_items(status, created_at desc);
"""


class SQLiteStore:
    """Small SQLite connection factory plus schema bootstrap."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def connect(self) -> Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = connect(self.path)
        conn.row_factory = Row
        conn.execute("pragma foreign_keys = on")
        conn.execute("pragma journal_mode = wal")
        return conn

    def init_schema(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA_SQL)
