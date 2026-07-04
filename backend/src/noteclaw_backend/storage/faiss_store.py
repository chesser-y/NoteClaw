from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VectorHit:
    chunk_id: str
    score: float


class FaissVectorStore:
    """FAISS adapter placeholder.

    Final implementation should normalize vectors, use IndexFlatIP, and persist
    chunk_id mappings in SQLite.
    """

    def __init__(self, index_path: Path) -> None:
        self.index_path = index_path

    def add(self, vectors: list[list[float]], chunk_ids: list[str]) -> None:
        raise NotImplementedError("FAISS add is not implemented yet.")

    def search(self, vector: list[float], limit: int) -> list[VectorHit]:
        raise NotImplementedError("FAISS search is not implemented yet.")

    def mark_deleted(self, chunk_ids: list[str]) -> None:
        raise NotImplementedError("FAISS deletion mapping is not implemented yet.")

    def save(self) -> None:
        raise NotImplementedError("FAISS persistence is not implemented yet.")

    def load(self) -> None:
        raise NotImplementedError("FAISS loading is not implemented yet.")
