"""Find near-duplicate notes via cosine similarity over note embeddings.

For each note we use the first chunk's vector as the representative
embedding. Pairs whose cosine >= threshold are persisted as review items.
On-demand only — call run() from the review route.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import numpy as np

from noteclaw_backend.schemas.common import new_id, utc_now
from noteclaw_backend.storage.faiss_store import get_vector_store
from noteclaw_backend.storage.repositories import get_repository
from noteclaw_backend.storage.sqlite import SQLiteStore
from noteclaw_backend.settings import get_settings

logger = logging.getLogger(__name__)


@dataclass
class DuplicatePair:
    note_a: str
    note_b: str
    title_a: str
    title_b: str
    score: float


class DuplicateDetectionService:
    def __init__(self) -> None:
        self._store: SQLiteStore | None = None

    def _get_store(self) -> SQLiteStore:
        if self._store is None:
            self._store = SQLiteStore(get_settings().sqlite_path)
            self._store.init_schema()
        return self._store

    async def find_duplicates(
        self,
        *,
        threshold: float = 0.85,
        max_pairs: int = 50,
    ) -> list[DuplicatePair]:
        repo = get_repository()
        notes, _ = await repo.list_notes(limit=500, offset=0)
        if len(notes) < 2:
            return []

        # Build note_id → first chunk_id map
        note_ids = [n.id for n in notes]
        note_titles = {n.id: n.title for n in notes}
        first_chunks: dict[str, str] = {}
        for note_id in note_ids:
            chunks = await repo.list_by_note(note_id)
            if chunks:
                first_chunks[note_id] = chunks[0]["chunk_id"]

        if not first_chunks:
            return []

        vs = get_vector_store()
        chunk_id_to_row: dict[str, int] = {}
        for i, cid in enumerate(vs.chunk_ids):
            if cid in {first_chunks.values() if False else set(first_chunks.values())}:
                chunk_id_to_row[cid] = i

        if vs.vectors is None:
            # FAISS-backed: rebuild vector per chunk via search-by-self trick is overkill;
            # we skip duplicate detection if numpy fallback isn't active.
            logger.info("duplicate detection skipped (faiss mode without numpy fallback)")
            return []

        vectors: dict[str, np.ndarray] = {}
        for note_id, chunk_id in first_chunks.items():
            row = chunk_id_to_row.get(chunk_id)
            if row is None or row >= vs.vectors.shape[0]:
                continue
            vectors[note_id] = vs.vectors[row]

        if len(vectors) < 2:
            return []

        ids = list(vectors.keys())
        matrix = np.vstack([vectors[i] for i in ids])
        matrix = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
        sim = matrix @ matrix.T

        pairs: list[DuplicatePair] = []
        seen: set[tuple[str, str]] = set()
        for a in range(len(ids)):
            for b in range(a + 1, len(ids)):
                if sim[a, b] < threshold:
                    continue
                id_a, id_b = ids[a], ids[b]
                key = (id_a, id_b) if id_a < id_b else (id_b, id_a)
                if key in seen:
                    continue
                seen.add(key)
                pairs.append(
                    DuplicatePair(
                        note_a=id_a,
                        note_b=id_b,
                        title_a=note_titles.get(id_a, id_a),
                        title_b=note_titles.get(id_b, id_b),
                        score=float(sim[a, b]),
                    )
                )
                if len(pairs) >= max_pairs:
                    return pairs
        return pairs

    async def persist_pairs(self, pairs: list[DuplicatePair]) -> int:
        if not pairs:
            return 0
        now = utc_now()
        store = self._get_store()
        inserted = 0
        with store.connect() as conn:
            for p in pairs:
                payload = {
                    "type": "duplicate",
                    "note_a": p.note_a,
                    "note_b": p.note_b,
                    "title_a": p.title_a,
                    "title_b": p.title_b,
                    "score": round(p.score, 3),
                }
                item_id = new_id("review")
                conn.execute(
                    """
                    insert into review_items(id, type, payload_json, status, created_at, resolved_at)
                    values (?, ?, ?, 'pending', ?, null)
                    """,
                    (item_id, "duplicate", _dump(payload), _iso(now)),
                )
                inserted += 1
        return inserted

    async def list_open_items(self) -> list[dict[str, Any]]:
        store = self._get_store()
        with store.connect() as conn:
            rows = conn.execute(
                "select * from review_items where status = 'pending' order by created_at desc limit 100"
            ).fetchall()
        return [
            {
                "id": row["id"],
                "type": row["type"],
                "payload": _load(row["payload_json"], {}),
                "status": row["status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    async def resolve_item(self, item_id: str, status: str) -> bool:
        store = self._get_store()
        with store.connect() as conn:
            cur = conn.execute(
                "update review_items set status = ?, resolved_at = ? where id = ?",
                (status, _iso(utc_now()), item_id),
            )
            return cur.rowcount > 0


def _dump(value: Any) -> str:
    import json
    return json.dumps(value, ensure_ascii=False)


def _load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        import json
        return json.loads(value)
    except json.JSONDecodeError:
        return default


def _iso(dt: datetime) -> str:
    return dt.isoformat()


duplicate_detection_service = DuplicateDetectionService()
