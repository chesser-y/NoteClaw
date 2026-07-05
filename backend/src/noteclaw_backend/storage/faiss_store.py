from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from noteclaw_backend.settings import get_settings

try:  # pragma: no cover - exercised when faiss is installed in the runtime image
    import faiss  # type: ignore
except Exception:  # pragma: no cover - numpy fallback keeps the MVP runnable
    faiss = None


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    score: float


class FaissVectorStore:
    """Persistent vector index using normalized inner product search."""

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path
        self.ids_path = index_path.with_suffix(".ids.json")
        self.numpy_path = index_path.with_suffix(".npy")
        self.index = None
        self.vectors: np.ndarray | None = None
        self.chunk_ids: list[str] = []
        self.deleted: set[str] = set()
        self.load()

    def add(self, vectors: list[list[float]], chunk_ids: list[str]) -> list[int]:
        if not vectors:
            return []
        matrix = self._normalize(np.asarray(vectors, dtype="float32"))
        if matrix.ndim != 2:
            raise ValueError("vectors must be a two-dimensional list")

        start = len(self.chunk_ids)
        row_ids = list(range(start, start + len(chunk_ids)))
        if faiss is not None:
            if self.index is None:
                self.index = faiss.IndexFlatIP(matrix.shape[1])
            if self.index.d != matrix.shape[1]:
                raise ValueError(
                    f"embedding dimension changed from {self.index.d} to {matrix.shape[1]}. "
                    "The existing FAISS index was built with a different embedding provider/model. "
                    "Keep one embedding model per storage directory, or rebuild the vector index."
                )
            self.index.add(matrix)
        else:
            self.vectors = matrix if self.vectors is None else np.vstack([self.vectors, matrix])
        self.chunk_ids.extend(chunk_ids)
        self.save()
        return row_ids

    def search(self, vector: list[float], limit: int) -> list[VectorHit]:
        if limit <= 0 or not self.chunk_ids:
            return []
        query = self._normalize(np.asarray([vector], dtype="float32"))
        candidates = min(len(self.chunk_ids), max(limit * 4, limit))
        hits: list[VectorHit] = []
        if faiss is not None and self.index is not None and self.index.ntotal > 0:
            if self.index.d != query.shape[1]:
                raise ValueError(
                    f"query embedding dimension {query.shape[1]} does not match FAISS index dimension {self.index.d}. "
                    "Use the same embedding model used to build the index, or rebuild the vector index."
                )
            scores, row_ids = self.index.search(query, candidates)
            for score, row_id in zip(scores[0], row_ids[0]):
                if row_id < 0 or row_id >= len(self.chunk_ids):
                    continue
                chunk_id = self.chunk_ids[int(row_id)]
                if chunk_id in self.deleted:
                    continue
                hits.append(VectorHit(chunk_id=chunk_id, score=float(score)))
                if len(hits) >= limit:
                    break
            return hits

        if self.vectors is None or len(self.vectors) == 0:
            return []
        scores = self.vectors @ query[0]
        order = np.argsort(scores)[::-1][:candidates]
        for row_id in order:
            chunk_id = self.chunk_ids[int(row_id)]
            if chunk_id in self.deleted:
                continue
            hits.append(VectorHit(chunk_id=chunk_id, score=float(scores[row_id])))
            if len(hits) >= limit:
                break
        return hits

    def mark_deleted(self, chunk_ids: list[str]) -> None:
        self.deleted.update(chunk_ids)
        self.save()

    def save(self) -> None:
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        if faiss is not None and self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        elif self.vectors is not None:
            np.save(self.numpy_path, self.vectors)
        self.ids_path.write_text(
            json.dumps(
                {"chunk_ids": self.chunk_ids, "deleted": sorted(self.deleted)},
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def load(self) -> None:
        if self.ids_path.exists():
            data = json.loads(self.ids_path.read_text(encoding="utf-8"))
            self.chunk_ids = list(data.get("chunk_ids", []))
            self.deleted = set(data.get("deleted", []))
        if faiss is not None and self.index_path.exists():
            self.index = faiss.read_index(str(self.index_path))
        elif self.numpy_path.exists():
            self.vectors = np.load(self.numpy_path)

    def _normalize(self, matrix: np.ndarray) -> np.ndarray:
        if matrix.ndim == 1:
            matrix = matrix.reshape(1, -1)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return matrix / norms


@lru_cache
def get_vector_store() -> FaissVectorStore:
    return FaissVectorStore(get_settings().faiss_index_path)
